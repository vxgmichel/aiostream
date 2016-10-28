
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
    with event_loop.assert_cleanup():
        xs = stream.range(5) | pipe.map(lambda x: x**2)
        expected = [x**2 for x in range(5)]
        await assert_run(xs, expected)

    with event_loop.assert_cleanup():
        xs = stream.range(5)
        ys = xs | pipe.map(lambda x, y: x+y, xs)
        expected = [x*2 for x in range(5)]
        await assert_run(ys, expected)

    with event_loop.assert_cleanup():
        xs = stream.range(1, 4) | pipe.map(asyncio.sleep)
        expected = [None] * 3
        await assert_run(xs, expected)
        assert event_loop.steps == [1, 2, 3]

    with event_loop.assert_cleanup():
        xs = stream.range(1, 4)
        ys = xs | pipe.map(asyncio.sleep, xs)
        await assert_run(ys, [1, 2, 3])
        assert event_loop.steps == [1, 2, 3]
        event_loop.steps.clear()


@pytest.mark.asyncio
async def test_merge(assert_run, event_loop):
    xs = stream.range(1, 5, 2, interval=2) | pipe.delay(1)
    ys = stream.range(0, 5, 2, interval=2) | pipe.merge(xs)
    await assert_run(ys, [0, 1, 2, 3, 4])
    assert event_loop.steps == [1, 2, 2, 2]
