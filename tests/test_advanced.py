import pytest

from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop

# Pytest fixtures
assert_run, event_loop


@pytest.mark.anyio
async def test_concatmap(assert_run, event_loop):
    # Concurrent run
    with event_loop.assert_cleanup():
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.concatmap(lambda x: stream.range(x, x+2, interval=5))
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert event_loop.steps == [1, 1, 3, 5, 5]

    # Sequential run
    with event_loop.assert_cleanup():
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.concatmap(
            lambda x: stream.range(x, x+2, interval=5),
            task_limit=1)
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert event_loop.steps == [5, 1, 5, 1, 5]

    # Limited run
    with event_loop.assert_cleanup():
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.concatmap(
            lambda x: stream.range(x, x+2, interval=5),
            task_limit=2)
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert event_loop.steps == [1, 4, 1, 4, 5]

    # Make sure item arrive as soon as possible
    with event_loop.assert_cleanup():
        xs = stream.just(2)
        ys = xs | pipe.concatmap(lambda x: stream.range(x, x+4, interval=1))
        zs = ys | pipe.timeout(2)  # Sould NOT raise
        await assert_run(zs, [2, 3, 4, 5])
        assert event_loop.steps == [1, 1, 1]


@pytest.mark.anyio
async def test_flatmap(assert_run, event_loop):
    # Concurrent run
    with event_loop.assert_cleanup():
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.flatmap(lambda x: stream.range(x, x+2, interval=5))
        await assert_run(ys, [0, 2, 4, 1, 3, 5])
        assert event_loop.steps == [1, 1, 3, 1, 1]

    # Sequential run
    with event_loop.assert_cleanup():
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.flatmap(
            lambda x: stream.range(x, x+2, interval=5),
            task_limit=1)
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert event_loop.steps == [5, 1, 5, 1, 5]

    # Limited run
    with event_loop.assert_cleanup():
        xs = stream.range(1, 4, interval=1)
        ys = xs | pipe.flatmap(
            lambda x: stream.range(x*10, x*10+2, interval=5+x),
            task_limit=2)
        await assert_run(ys, [10, 20, 11, 30, 21, 31])
        assert event_loop.steps == [1, 5, 1, 1, 7]


@pytest.mark.anyio
async def test_switchmap(assert_run, event_loop):

    with event_loop.assert_cleanup():
        xs = stream.empty()
        ys = xs | pipe.switchmap(lambda x: stream.range(x, x+5, interval=1))
        await assert_run(ys, [])
        assert event_loop.steps == []

    with event_loop.assert_cleanup():
        xs = stream.range(0, 30, 10, interval=7)
        ys = xs | pipe.switchmap(lambda x: stream.range(x, x+5, interval=2))
        await assert_run(ys, [0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 24])
        assert event_loop.steps == [2, 2, 2, 1, 1, 1, 2, 2, 1, 1, 1, 2, 2, 2]

    # Test cleanup procedure

    with event_loop.assert_cleanup():
        xs = stream.range(0, 5, interval=1)
        ys = xs | pipe.switchmap(lambda x: stream.range(x, x+2, interval=2))
        await assert_run(ys[:3], [0, 1, 2])
        assert event_loop.steps == [1, 1]
