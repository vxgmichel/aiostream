"""Utilities for asynchronous iteration."""
from __future__ import annotations
from types import TracebackType

import warnings
import functools
from typing import (
    TYPE_CHECKING,
    AsyncContextManager,
    AsyncGenerator,
    AsyncIterable,
    Awaitable,
    Callable,
    Type,
    TypeVar,
    AsyncIterator,
    Any,
)

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec("P")

from contextlib import AsyncExitStack

__all__ = [
    "aiter",
    "anext",
    "await_",
    "async_",
    "is_async_iterable",
    "assert_async_iterable",
    "is_async_iterator",
    "assert_async_iterator",
    "AsyncIteratorContext",
    "aitercontext",
    "AsyncExitStack",
]


# Magic method shorcuts


def aiter(obj: AsyncIterable[T]) -> AsyncIterator[T]:
    """Access aiter magic method."""
    assert_async_iterable(obj)
    return obj.__aiter__()


def anext(obj: AsyncIterator[T]) -> Awaitable[T]:
    """Access anext magic method."""
    assert_async_iterator(obj)
    return obj.__anext__()


# Async / await helper functions


async def await_(obj: Awaitable[T]) -> T:
    """Identity coroutine function."""
    return await obj


def async_(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Wrap the given function into a coroutine function."""

    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await fn(*args, **kwargs)

    return wrapper


# Iterability helpers


def is_async_iterable(obj: object) -> bool:
    """Check if the given object is an asynchronous iterable."""
    return hasattr(obj, "__aiter__")


def assert_async_iterable(obj: object) -> None:
    """Raise a TypeError if the given object is not an
    asynchronous iterable.
    """
    if not is_async_iterable(obj):
        raise TypeError(f"{type(obj).__name__!r} object is not async iterable")


def is_async_iterator(obj: object) -> bool:
    """Check if the given object is an asynchronous iterator."""
    return hasattr(obj, "__anext__")


def assert_async_iterator(obj: object) -> None:
    """Raise a TypeError if the given object is not an
    asynchronous iterator.
    """
    if not is_async_iterator(obj):
        raise TypeError(f"{type(obj).__name__!r} object is not an async iterator")


# Async iterator context

T = TypeVar("T")
Self = TypeVar("Self", bound="AsyncIteratorContext[Any]")


class AsyncIteratorContext(AsyncIterator[T], AsyncContextManager[Any]):
    """Asynchronous iterator with context management.

    The context management makes sure the aclose asynchronous method
    of the corresponding iterator has run before it exits. It also issues
    warnings and RuntimeError if it is used incorrectly.

    Correct usage::

        ait = some_asynchronous_iterable()
        async with AsyncIteratorContext(ait) as safe_ait:
            async for item in safe_ait:
                <block>

    It is nonetheless not meant to use directly.
    Prefer aitercontext helper instead.
    """

    _STANDBY = "STANDBY"
    _RUNNING = "RUNNING"
    _FINISHED = "FINISHED"

    def __init__(self, aiterator: AsyncIterator[T]):
        """Initialize with an asynchrnous iterator."""
        assert_async_iterator(aiterator)
        if isinstance(aiterator, AsyncIteratorContext):
            raise TypeError(f"{aiterator!r} is already an AsyncIteratorContext")
        self._state = self._STANDBY
        self._aiterator = aiterator

    def __aiter__(self: Self) -> Self:
        return self

    def __anext__(self) -> Awaitable[T]:
        if self._state == self._FINISHED:
            raise RuntimeError(
                f"{type(self).__name__} is closed and cannot be iterated"
            )
        if self._state == self._STANDBY:
            warnings.warn(
                f"{type(self).__name__} is iterated outside of its context",
                stacklevel=2,
            )
        return anext(self._aiterator)

    async def __aenter__(self: Self) -> Self:
        if self._state == self._RUNNING:
            raise RuntimeError(f"{type(self).__name__} has already been entered")
        if self._state == self._FINISHED:
            raise RuntimeError(
                f"{type(self).__name__} is closed and cannot be iterated"
            )
        self._state = self._RUNNING
        return self

    async def __aexit__(
        self,
        typ: Type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            if self._state == self._FINISHED:
                return False
            try:
                # No exception to throw
                if typ is None:
                    return False

                # Prevent GeneratorExit from being silenced
                if typ is GeneratorExit:
                    return False

                # No method to throw
                if not hasattr(self._aiterator, "athrow"):
                    return False

                # No frame to throw
                if not getattr(self._aiterator, "ag_frame", True):
                    return False

                # Cannot throw at the moment
                if getattr(self._aiterator, "ag_running", False):
                    return False

                # Throw
                try:
                    assert isinstance(self._aiterator, AsyncGenerator)
                    await self._aiterator.athrow(typ, value, traceback)
                    raise RuntimeError("Async iterator didn't stop after athrow()")

                # Exception has been (most probably) silenced
                except StopAsyncIteration as exc:
                    return exc is not value

                # A (possibly new) exception has been raised
                except BaseException as exc:
                    if exc is value:
                        return False
                    raise
            finally:
                # Look for an aclose method
                aclose = getattr(self._aiterator, "aclose", None)

                # The ag_running attribute has been introduced with python 3.8
                running = getattr(self._aiterator, "ag_running", False)
                closed = not getattr(self._aiterator, "ag_frame", True)

                # A RuntimeError is raised if aiterator is running or closed
                if aclose and not running and not closed:
                    try:
                        await aclose()

                    # Work around bpo-35409
                    except GeneratorExit:
                        pass  # pragma: no cover
        finally:
            self._state = self._FINISHED

    async def aclose(self) -> None:
        await self.__aexit__(None, None, None)

    async def athrow(self, exc: Exception) -> T:
        if self._state == self._FINISHED:
            raise RuntimeError(f"{type(self).__name__} is closed and cannot be used")
        assert isinstance(self._aiterator, AsyncGenerator)
        item: T = await self._aiterator.athrow(exc)
        return item


def aitercontext(
    aiterable: AsyncIterable[T],
) -> AsyncIteratorContext[T]:
    """Return an asynchronous context manager from an asynchronous iterable.

    The context management makes sure the aclose asynchronous method
    has run before it exits. It also issues warnings and RuntimeError
    if it is used incorrectly.

    It is safe to use with any asynchronous iterable and prevent
    asynchronous iterator context to be wrapped twice.

    Correct usage::

        ait = some_asynchronous_iterable()
        async with aitercontext(ait) as safe_ait:
            async for item in safe_ait:
                <block>
    """
    aiterator = aiter(aiterable)
    if isinstance(aiterator, AsyncIteratorContext):
        return aiterator
    return AsyncIteratorContext(aiterator)
