import pytest
import asyncio
import operator

from aiostream import stream, pipe
from aiostream.test_utils import add_resource


@pytest.mark.asyncio
async def test_accumulate(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.accumulate()
        await assert_run(xs, [0, 1, 3, 6, 10])

    with assert_cleanup():
        xs = (
            stream.range(2, 4)
            | add_resource.pipe(1)
            | pipe.accumulate(func=operator.mul, initializer=2)
        )
        await assert_run(xs, [2, 4, 12])

    with assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.accumulate()
        await assert_run(xs, [])

    async def sleepmax(x, y):
        return await asyncio.sleep(1, result=max(x, y))

    with assert_cleanup() as loop:
        xs = stream.range(3) | add_resource.pipe(1) | pipe.accumulate(sleepmax)
        await assert_run(xs, [0, 1, 2])
        assert loop.steps == [1] * 3


@pytest.mark.asyncio
async def test_reduce(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(min)
        await assert_run(xs, [0])

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(max)
        await assert_run(xs, [4])

    with assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.reduce(max)
        await assert_run(xs, [], IndexError("Index out of range"))


@pytest.mark.asyncio
async def test_list(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(3) | add_resource.pipe(1) | pipe.list()
        # The same list object is yielded at each step
        await assert_run(xs, [[0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2]])

    with assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.list()
        await assert_run(xs, [[]])
