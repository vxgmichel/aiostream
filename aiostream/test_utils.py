
import pytest
import asyncio
import asyncio.test_utils

from . import stream
from .utils import aitercontext
from .core import StreamEmpty, operator


@operator(pipable=True)
async def add_resource(source, cleanup_time):
    try:
        async with aitercontext(source) as streamer:
            async for item in streamer:
                yield item
    finally:
        await asyncio.sleep(cleanup_time)


def compare_exceptions(exc1, exc2):
    return (
        exc1 == exc2 or
        exc1.__class__ == exc2.__class__ and
        exc1.__dict__ == exc2.__dict__)


async def assert_aiter(source, values, exception=None):
    result = []
    try:
        async with aitercontext(source) as streamer:
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


@pytest.fixture()
def event_loop():

    def gen():
        when = yield
        while True:
            loop.steps.append(
                when - loop.time() if when > loop.time()
                else 0.)
            when = yield loop.steps[-1]

    loop = asyncio.test_utils.TestLoop(gen)
    loop._check_on_close = False
    loop.steps = []
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
