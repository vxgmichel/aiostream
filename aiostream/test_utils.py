"""Utilities for testing stream operators."""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import contextmanager
from unittest.mock import Mock
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    List,
    Protocol,
    TypeVar,
    AsyncIterable,
    AsyncIterator,
    ContextManager,
    Iterator,
    cast,
    Any,
)

import pytest

from .core import StreamEmpty, streamcontext, pipable_operator

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest
    from aiostream.core import Stream

__all__ = ["add_resource", "assert_run", "event_loop_policy", "assert_cleanup"]


T = TypeVar("T")


@pipable_operator
async def add_resource(
    source: AsyncIterable[T], cleanup_time: float
) -> AsyncIterator[T]:
    """Simulate an open resource in a stream operator."""
    loop = asyncio.get_running_loop()
    assert isinstance(loop, TimeTrackingTestLoop)
    try:
        loop.open_resources += 1
        loop.resources += 1
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield item
    finally:
        try:
            await asyncio.sleep(cleanup_time)
        finally:
            loop.open_resources -= 1


def compare_exceptions(
    exc1: Exception,
    exc2: Exception,
) -> bool:
    """Compare two exceptions together."""
    return exc1 == exc2 or exc1.__class__ == exc2.__class__ and exc1.args == exc2.args


async def assert_aiter(
    source: Stream[object],
    values: List[object],
    exception: Exception | None = None,
) -> None:
    """Check the results of a stream using a streamcontext."""
    results: list[object] = []
    exception_type = (type(exception),) if exception else ()
    try:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                results.append(item)
    except exception_type as exc:
        assert exception is not None
        assert compare_exceptions(exc, exception)
    else:
        assert exception is None
    assert results == values


async def assert_await(
    source: Stream[object],
    values: List[object],
    exception: Exception | None = None,
) -> None:
    """Check the results of a stream using by awaiting it."""
    exception_type = (type(exception),) if exception else ()
    try:
        result = await source
    except StreamEmpty:
        assert values == []
        assert exception is None
    except exception_type as exc:
        assert exception is not None
        assert compare_exceptions(exc, exception)
    else:
        assert result == values[-1]
        assert exception is None


class AssertRunProtocol(Protocol):
    def __call__(
        self, source: Stream[object], values: List[object], exception: Exception | None
    ) -> Awaitable[None]: ...


@pytest.fixture(params=[assert_aiter, assert_await], ids=["aiter", "await"])  # type: ignore[misc]
def assert_run(request: SubRequest) -> AssertRunProtocol:
    """Parametrized fixture returning a stream runner."""
    return cast(AssertRunProtocol, request.param)


@pytest.fixture  # type: ignore[misc]
def event_loop_policy() -> TimeTrackingTestLoopPolicy:
    """Fixture providing a test event loop.

    The event loop simulate and records the sleep operation,
    available as event_loop.steps

    It also tracks simulated resources and make sure they are
    all released before the loop is closed.
    """
    return TimeTrackingTestLoopPolicy()


@pytest.fixture  # type: ignore[misc]
def assert_cleanup(
    event_loop: TimeTrackingTestLoop,
) -> Callable[[], ContextManager[TimeTrackingTestLoop]]:
    """Fixture to assert cleanup of resources."""
    return event_loop.assert_cleanup


class BaseEventLoopWithInternals(asyncio.BaseEventLoop):
    _ready: deque[asyncio.Handle]
    _run_once: Callable[[], None]


class TimeTrackingTestLoop(BaseEventLoopWithInternals):
    stuck_threshold: int = 100

    def __init__(self) -> None:
        super().__init__()
        self._time: float = 0.0
        self._timers: list[float] = []
        self._selector = Mock()

        self.steps: list[float] = []
        self.open_resources: int = 0
        self.resources: int = 0
        self.busy_count: int = 0

    # Loop internals

    def _run_once(self) -> None:  # type: ignore
        super()._run_once()
        # Update internals
        self.busy_count += 1
        self._timers = sorted(when for when in self._timers if when > self.time())
        # Time advance
        if self.time_to_go:
            when = self._timers.pop(0)
            step = when - self.time()
            self.steps.append(step)
            self.advance_time(step)
            self.busy_count = 0

    def _process_events(self, event_list: object) -> None:
        return

    def _write_to_self(self) -> None:
        return

    # Time management

    def time(self) -> float:
        return self._time

    def advance_time(self, advance: float) -> None:
        if advance:
            self._time += advance

    def call_at(self, when: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> asyncio.TimerHandle:  # type: ignore
        self._timers.append(when)
        return super().call_at(when, callback, *args, **kwargs)

    @property
    def stuck(self) -> bool:
        return self.busy_count > self.stuck_threshold

    @property
    def time_to_go(self) -> bool:
        return bool(self._timers) and (self.stuck or not self._ready)

    # Resource management

    def clear(self) -> None:
        self.steps = []
        self.open_resources = 0
        self.resources = 0
        self.busy_count = 0

    @contextmanager
    def assert_cleanup(self) -> Iterator[TimeTrackingTestLoop]:
        self.clear()
        yield self
        assert self.open_resources == 0
        self.clear()


class TimeTrackingTestLoopPolicy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = TimeTrackingTestLoop
