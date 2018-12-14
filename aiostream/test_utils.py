"""Utilities for testing stream operators."""

import asyncio
from unittest.mock import Mock

import pytest

from .core import StreamEmpty, operator, streamcontext

__all__ = ['add_resource', 'assert_run']


@pytest.fixture
def add_resource():
    resources = 0
    open_resources = 0

    @operator(pipable=True)
    async def add_resource(source, cleanup_time):
        """Simulate an open resource in a stream operator."""
        nonlocal resources, open_resources
        try:
            resources += 1
            open_resources += 1
            async with streamcontext(source) as streamer:
                async for item in streamer:
                    yield item
        finally:
            try:
                await asyncio.sleep(cleanup_time)
            finally:
                open_resources -= 1

    yield add_resource
    assert resources > 0
    assert open_resources == 0


async def assert_aiter(source, values, exception=None):
    """Check the results of a stream using a streamcontext."""
    if exception is not None:
        with pytest.raises(type(exception)) as record:
            await assert_aiter(source, values)
        assert str(record.value) == str(exception)
        return
    try:
        result = []
        async with streamcontext(source) as streamer:
            async for item in streamer:
                result.append(item)
    finally:
        assert result == values


async def assert_await(source, values, exception=None):
    """Check the results of a stream using by awaiting it."""
    if exception is not None:
        with pytest.raises(type(exception)) as record:
            await assert_await(source, values)
        assert str(record.value) == str(exception)
        return
    try:
        result = await source
    except StreamEmpty:
        assert values == []
    else:
        assert result == values[-1]


@pytest.fixture(
    params=[assert_aiter, assert_await],
    ids=['aiter', 'await'])
def assert_run(request):
    """Parametrized fixture returning a stream runner."""

    class TimeTrackingTestLoop(asyncio.BaseEventLoop):

        stuck_threshold = 100

        def __init__(self):
            super().__init__()
            self._time = 0
            self._timers = []
            self._selector = Mock()
            self._busy_count = 0
            self._steps = []

        # Loop internals

        def _run_once(self):
            super()._run_once()
            # Update internals
            self._busy_count += 1
            self._timers = sorted(
                when for when in self._timers if when > self.time())
            # Time advance
            if self.time_to_go:
                when = self._timers.pop(0)
                step = when - self.time()
                self._steps.append(step)
                self.advance_time(step)
                self._busy_count = 0

        def _process_events(self, event_list):
            return

        def _write_to_self(self):
            return

        # Time management

        def time(self):
            return self._time

        def advance_time(self, advance):
            if advance:
                self._time += advance

        def call_at(self, when, callback, *args, **kwargs):
            self._timers.append(when)
            return super().call_at(when, callback, *args, **kwargs)

        @property
        def stuck(self):
            return self._busy_count > self.stuck_threshold

        @property
        def time_to_go(self):
            return self._timers and (self.stuck or not self._ready)

    def assert_run(source, value, exception=None, steps=[]):
        loop = TimeTrackingTestLoop()
        try:
            asyncio.set_event_loop(loop)
            coro = request.param(source, value, exception)
            loop.run_until_complete(coro)
            assert loop._steps == steps
        finally:
            loop.close()

    yield assert_run
