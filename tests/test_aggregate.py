
import pytest
import operator

from aiostream import stream, pipe, compat


@pytest.mark.anyio
async def test_aggregate(assert_run, event_loop, add_resource):
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
        await compat.sleep(1)
        return max(x, y)

    with event_loop.assert_cleanup():
        xs = stream.range(3) | add_resource.pipe(1) | pipe.accumulate(sleepmax)
        await assert_run(xs, [0, 1, 2])
        assert event_loop.steps == [1]*3


@pytest.mark.anyio
async def test_reduce(assert_run, event_loop, add_resource):
    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(min)
        await assert_run(xs, [0])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(max)
        await assert_run(xs, [4])

    with event_loop.assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.reduce(max)
        await assert_run(xs, [], IndexError("Index out of range"))


@pytest.mark.anyio
async def test_list(assert_run, event_loop, add_resource):
    with event_loop.assert_cleanup():
        xs = stream.range(3) | add_resource.pipe(1) | pipe.list()
        await assert_run(xs, [[], [0], [0, 1], [0, 1, 2]])

    with event_loop.assert_cleanup():
        xs = stream.range(0) | add_resource.pipe(1) | pipe.list()
        await assert_run(xs, [[]])
