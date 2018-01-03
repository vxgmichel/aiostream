import pytest

from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop

# Pytest fixtures
assert_run, event_loop


@pytest.mark.asyncio
async def test_concatmap(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.concatmap(lambda x: stream.range(x, x+2, interval=5))
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert event_loop.steps == [1, 1, 3, 1, 1]


@pytest.mark.asyncio
async def test_flatmap(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(0, 3, interval=1)
        ys = xs | pipe.flatmap(lambda x: stream.range(x, x+6, 3, interval=3))
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert event_loop.steps == [1, 1, 1, 1, 1]


@pytest.mark.asyncio
async def test_switchmap(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(0, 5, interval=1)
        ys = xs | pipe.switchmap(lambda x: stream.range(x, x+2, interval=2))
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert event_loop.steps == [1, 1, 1, 1, 1, 1]

    with event_loop.assert_cleanup():
        xs = stream.range(0, 5, interval=1)
        ys = xs | pipe.switchmap(lambda x: stream.range(x, x+2, interval=2))
        await assert_run(ys[:3], [0, 1, 2])
        assert event_loop.steps == [1, 1]
