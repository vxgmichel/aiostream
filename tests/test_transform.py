import pytest
import asyncio

from aiostream import stream, pipe
from aiostream.test_utils import add_resource


@pytest.mark.asyncio
async def test_starmap(assert_run, assert_cleanup):
    def target(a: int, b: int, *_) -> int:
        return a + b

    with assert_cleanup():
        xs = stream.range(5)
        ys = stream.range(5)
        zs = xs | pipe.zip(ys) | pipe.starmap(target)
        expected = [x * 2 for x in range(5)]
        await assert_run(zs, expected)

    async def async_target(arg: float, result: int, *_) -> int:
        return await asyncio.sleep(arg, result)

    with assert_cleanup() as loop:
        xs = stream.range(1, 4)
        ys = stream.range(1, 4)
        zs = xs | pipe.zip(ys) | pipe.starmap(async_target)
        await assert_run(zs, [1, 2, 3])
        assert loop.steps == [1, 1, 1]

    with assert_cleanup() as loop:
        xs = stream.range(1, 4)
        ys = stream.range(1, 4)
        zs = xs | pipe.zip(ys) | pipe.starmap(async_target, task_limit=1)
        await assert_run(zs, [1, 2, 3])
        assert loop.steps == [1, 2, 3]


@pytest.mark.asyncio
async def test_cycle(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.empty() | pipe.cycle() | pipe.timeout(1)
        await assert_run(xs, [], asyncio.TimeoutError())

    with assert_cleanup():
        xs = stream.empty() | add_resource.pipe(1) | pipe.cycle() | pipe.timeout(1)
        await assert_run(xs, [], asyncio.TimeoutError())

    with assert_cleanup() as loop:
        xs = stream.just(1) | add_resource.pipe(1) | pipe.cycle()
        await assert_run(xs[:5], [1] * 5)
        assert loop.steps == [1] * 5


@pytest.mark.asyncio
async def test_chunks(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(3, interval=1) | pipe.chunks(3)
        await assert_run(xs, [[0, 1, 2]])

    with assert_cleanup():
        xs = stream.range(4, interval=1) | pipe.chunks(3)
        await assert_run(xs, [[0, 1, 2], [3]])

    with assert_cleanup():
        xs = stream.range(5, interval=1) | pipe.chunks(3)
        await assert_run(xs, [[0, 1, 2], [3, 4]])

    with assert_cleanup():
        xs = stream.count(interval=1) | add_resource.pipe(1) | pipe.chunks(3)
        await assert_run(xs[:1], [[0, 1, 2]])
