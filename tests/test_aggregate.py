
import pytest
import asyncio
import operator

from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop, add_resource

# Pytest fixtures
assert_run, event_loop


@pytest.mark.asyncio
async def test_aggregate(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.accumulate()
        await assert_run(xs, [0, 1, 3, 6, 10])

    with event_loop.assert_cleanup():
        xs = (stream.range(2, 4)
              | add_resource.pipe(1)
              | pipe.accumulate(func=operator.mul, initializer=2))
        await assert_run(xs, [2, 4, 12])

    with event_loop.assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.accumulate()
        await assert_run(xs, [])

    async def sleepmax(x, y):
        return await asyncio.sleep(1, result=max(x, y))

    with event_loop.assert_cleanup():
        xs = stream.range(3) | add_resource.pipe(1) | pipe.accumulate(sleepmax)
        await assert_run(xs, [0, 1, 2])
        assert event_loop.steps == [1]*3


@pytest.mark.asyncio
async def test_reduce(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(min)
        await assert_run(xs, [0])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(max)
        await assert_run(xs, [4])

    with event_loop.assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.reduce(max)
        await assert_run(xs, [], IndexError("Index out of range"))


@pytest.mark.asyncio
async def test_to_list(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.to_list()
        await assert_run(xs, [[0, 1, 2, 3, 4]])

    with event_loop.assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.to_list()
        await assert_run(xs, [[]])
