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


@pytest.mark.asyncio
async def test_prefetch(assert_run, assert_cleanup):
    # Test basic prefetching
    with assert_cleanup():
        xs = stream.range(5, interval=1)
        ys = xs | pipe.prefetch(1)  # Default buffer_size=1
        await assert_run(ys, [0, 1, 2, 3, 4])

    # Test with custom buffer size
    with assert_cleanup():
        xs = stream.range(5, interval=1)
        ys = xs | pipe.prefetch(1)
        await assert_run(ys, [0, 1, 2, 3, 4])

    # Test with buffer_size=0
    with assert_cleanup():
        xs = stream.range(5, interval=1)
        ys = xs | pipe.prefetch(0)
        await assert_run(ys, [0, 1, 2, 3, 4])

    # Test cleanup on early exit
    with assert_cleanup():
        xs = stream.range(100, interval=1)
        ys = xs | pipe.prefetch(buffer_size=1) | pipe.take(3)
        await assert_run(ys, [0, 1, 2])

    # Test with empty stream
    with assert_cleanup():
        xs = stream.empty() | pipe.prefetch()
        await assert_run(xs, [])

    # Test with error propagation
    with assert_cleanup():
        xs = stream.throw(ValueError()) | pipe.prefetch()
        await assert_run(xs, [], ValueError())


@pytest.mark.asyncio
async def test_prefetch_timing(assert_run, assert_cleanup):
    async def slow_fetch(x: int) -> int:
        await asyncio.sleep(0.1)
        return x

    async def slow_processor(x: int) -> int:
        await asyncio.sleep(0.4)
        return x

    with assert_cleanup() as loop:
        # Without prefetch (sequential):
        xs = stream.range(3) | pipe.map(slow_fetch, task_limit=1)
        ys = xs | pipe.map(slow_processor, task_limit=1)  # Process time
        await assert_run(ys, [0, 1, 2])
        assert loop.steps == pytest.approx([0.1, 0.4, 0.1, 0.4, 0.1, 0.4])

    with assert_cleanup() as loop:
        # With prefetch:
        xs = stream.range(3) | pipe.map(slow_fetch, task_limit=1)
        ys = xs | pipe.prefetch(1) | pipe.map(slow_processor, task_limit=1)
        await assert_run(ys, [0, 1, 2])
        # instead of taking 0.1 + 0.4 seconds per element, we should now just take max(0.1, 0.4) = 0.4
        assert loop.steps == pytest.approx([0.1, 0.1, 0.1, 0.2, 0.4, 0.4])
