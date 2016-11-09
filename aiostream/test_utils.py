"""Utilities for testing stream operators."""

import pytest
import asyncio
import asyncio.test_utils
from contextlib import contextmanager

from .core import StreamEmpty, operator, streamcontext

__all__ = ['add_resource', 'assert_run', 'event_loop']


@operator(pipable=True)
async def add_resource(source, cleanup_time):
    """Simulate an open resource in a stream operator."""
    try:
        loop = asyncio.get_event_loop()
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


def compare_exceptions(exc1, exc2):
    """Compare two exceptions together."""
    return (
        exc1 == exc2 or
        exc1.__class__ == exc2.__class__ and
        exc1.args == exc2.args)


async def assert_aiter(source, values, exception=None):
    """Check the results of a stream using a streamcontext."""
    result = []
    exception_type = type(exception) if exception else ()
    try:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                result.append(item)
    except exception_type as exc:
        assert result == values
        assert compare_exceptions(exc, exception)
    else:
        assert result == values
        assert exception is None


async def assert_await(source, values, exception=None):
    """Check the results of a stream using by awaiting it."""
    exception_type = type(exception) if exception else ()
    try:
        result = await source
    except StreamEmpty:
        assert values == []
        assert exception is None
    except exception_type as exc:
        assert compare_exceptions(exc, exception)
    else:
        assert result == values[-1]
        assert exception is None


@pytest.fixture(
    params=[assert_aiter, assert_await],
    ids=['aiter', 'await'])
def assert_run(request):
    """Parametrized fixture returning a stream runner."""
    return request.param


@pytest.fixture
def event_loop():
    """Fixture providing a test event loop.

    The event loop simulate and records the sleep operation,
    available as event_loop.steps

    It also tracks simulated resources and make sure they are
    all released before the loop is closed.
    """

    def gen():
        when = yield
        while True:
            loop.steps.append(
                when - loop.time() if when > loop.time()
                else 0.)
            when = yield loop.steps[-1]

    def clear():
        loop.steps = []
        loop.open_resources = 0
        loop.resources = 0

    @contextmanager
    def assert_cleanup():
        clear()
        yield loop
        assert loop.open_resources == 0
        clear()

    loop = asyncio.test_utils.TestLoop(gen)
    loop._check_on_close = False
    loop.assert_cleanup = assert_cleanup
    asyncio.set_event_loop(loop)
    with assert_cleanup():
        yield loop
    loop.close()
