
import pytest
import asyncio
import asyncio.test_utils
from contextlib import contextmanager

from .core import StreamEmpty, operator, streamcontext

__all__ = ['add_resource', 'assert_run', 'event_loop']


@operator(pipable=True)
async def add_resource(source, cleanup_time):
    try:
        loop = asyncio.get_event_loop()
        loop.open_resources += 1
        loop.resources += 1
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield item
    finally:
        await asyncio.sleep(cleanup_time)
        loop.open_resources -= 1


def compare_exceptions(exc1, exc2):
    return (
        exc1 == exc2 or
        exc1.__class__ == exc2.__class__ and
        exc1.__dict__ == exc2.__dict__)


async def assert_aiter(source, values, exception=None):
    result = []
    try:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                result.append(item)
    except Exception as exc:
        assert result == values
        assert compare_exceptions(exc, exception)
    else:
        assert result == values
        assert exception is None


async def assert_await(source, values, exception=None):
    try:
        result = await source
    except StreamEmpty:
        assert values == []
        assert exception is None
    except Exception as exc:
        assert compare_exceptions(exc, exception)
    else:
        assert result == values[-1]
        assert exception is None


@pytest.fixture(
    params=[assert_aiter, assert_await],
    ids=['aiter', 'await'])
def assert_run(request):
    return request.param


@pytest.fixture
def event_loop():

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
