
import pytest
import asyncio

from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop, add_resource

# Pytest fixtures
assert_run, event_loop


@pytest.mark.asyncio
async def test_chain(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(5) + stream.range(5, 10)
        await assert_run(xs, list(range(10)))

    with event_loop.assert_cleanup():
        xs = stream.range(10, 15) | add_resource.pipe(1)
        xs += stream.range(15, 20) | add_resource.pipe(1)
        await assert_run(xs, list(range(10, 20)))


@pytest.mark.asyncio
async def test_zip(assert_run, event_loop):
    xs = stream.range(5) | add_resource.pipe(1.0)
    ys = xs | pipe.zip(xs, xs)
    expected = [(x,)*3 for x in range(5)]
    await assert_run(ys, expected)


@pytest.mark.asyncio
async def test_map(assert_run, event_loop):

    # Synchronous/simple
    with event_loop.assert_cleanup():
        xs = stream.range(5) | pipe.map(lambda x: x**2)
        expected = [x**2 for x in range(5)]
        await assert_run(xs, expected)

    # Synchronous/multiple
    with event_loop.assert_cleanup():
        xs = stream.range(5)
        ys = xs | pipe.map(lambda x, y: x+y, xs)
        expected = [x*2 for x in range(5)]
        await assert_run(ys, expected)

    # Asynchronous/simple/concurrent
    with event_loop.assert_cleanup():
        xs = stream.range(1, 4) | pipe.map(asyncio.sleep)
        expected = [None] * 3
        await assert_run(xs, expected)
        assert event_loop.steps == [1, 1, 1]

    # Asynchronous/simple/sequential
    with event_loop.assert_cleanup():
        xs = stream.range(1, 4) | pipe.map(asyncio.sleep, task_limit=1)
        expected = [None] * 3
        await assert_run(xs, expected)
        assert event_loop.steps == [1, 2, 3]

    # Asynchronous/multiple/concurrent
    with event_loop.assert_cleanup():
        xs = stream.range(1, 4)
        ys = xs | pipe.map(asyncio.sleep, xs)
        await assert_run(ys, [1, 2, 3])
        assert event_loop.steps == [1, 1, 1]
        event_loop.steps.clear()

    # Asynchronous/multiple/sequential
    with event_loop.assert_cleanup():
        xs = stream.range(1, 4)
        ys = xs | pipe.map(asyncio.sleep, xs, task_limit=1)
        await assert_run(ys, [1, 2, 3])
        assert event_loop.steps == [1, 2, 3]
        event_loop.steps.clear()

    # As completed
    with event_loop.assert_cleanup():
        xs = stream.iterate([2, 4, 1, 3, 5])
        ys = xs | pipe.map(asyncio.sleep, xs, ordered=False)
        await assert_run(ys, [1, 2, 3, 4, 5])
        assert event_loop.steps == [1, 1, 1, 1, 1]
        event_loop.steps.clear()

    # Invalid argument
    with pytest.raises(ValueError):
        await (stream.range(1, 4) | pipe.map(asyncio.sleep, task_limit=0))

    # Break
    with event_loop.assert_cleanup():
        xs = stream.count(1)
        ys = xs | pipe.map(asyncio.sleep, xs, task_limit=10)
        await assert_run(ys[:3], [1, 2, 3])
        assert event_loop.steps == [1, 1, 1]
        event_loop.steps.clear()

    # Stuck
    with event_loop.assert_cleanup():
        xs = stream.count(1)
        ys = xs | pipe.map(asyncio.sleep, xs, task_limit=1) | pipe.timeout(5)
        await assert_run(ys, [1, 2, 3, 4], asyncio.TimeoutError())

@pytest.mark.asyncio
async def test_merge(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(1, 5, 2, interval=2) | pipe.delay(1)
        ys = stream.range(0, 5, 2, interval=2) | pipe.merge(xs)
        await assert_run(ys, [0, 1, 2, 3, 4])
        assert event_loop.steps == [1, 1, 1, 1]

    with event_loop.assert_cleanup():
        xs = stream.range(1, 5, 2, interval=2) | pipe.delay(1)
        ys = stream.range(0, 5, 2, interval=2) | pipe.merge(xs)
        await assert_run(ys[:3], [0, 1, 2])
        assert event_loop.steps == [1, 1]
