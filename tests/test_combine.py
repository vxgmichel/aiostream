from typing import Awaitable
import pytest
import asyncio

from aiostream import stream, pipe, async_, await_
from aiostream.test_utils import add_resource


@pytest.mark.asyncio
async def test_chain(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(5) + stream.range(5, 10)
        await assert_run(xs, list(range(10)))

    with assert_cleanup():
        xs = stream.range(10, 15) | add_resource.pipe(1)
        xs += stream.range(15, 20) | add_resource.pipe(1)
        await assert_run(xs, list(range(10, 20)))

    # Empty chain (issue #95)
    xs = stream.chain()
    await assert_run(xs, [])


@pytest.mark.asyncio
async def test_zip(assert_run):
    xs = stream.range(5) | add_resource.pipe(1.0)
    ys = xs | pipe.zip(xs, xs)
    expected = [(x,) * 3 for x in range(5)]
    await assert_run(ys, expected)

    # Exceptions from iterables are propagated
    xs = stream.zip(stream.range(2), stream.throw(AttributeError))
    with pytest.raises(AttributeError):
        await xs

    # Empty zip (issue #95)
    xs = stream.zip()
    await assert_run(xs, [])

    # Strict mode (issue #118): Iterable length mismatch raises
    xs = stream.zip(stream.range(2), stream.range(1), strict=True)
    with pytest.raises(ValueError):
        await xs

    # Strict mode (issue #118): No raise for matching-length iterables
    xs = stream.zip(stream.range(2), stream.range(2), strict=True)
    await assert_run(xs, [(0, 0), (1, 1)])

    # Strict mode (issue #118): Exceptions from iterables are propagated
    xs = stream.zip(stream.range(2), stream.throw(AttributeError), strict=True)
    with pytest.raises(AttributeError):
        await xs

    # Strict mode (issue #118): Non-strict mode works as before
    xs = stream.zip(stream.range(2), stream.range(1))
    await assert_run(xs, [(0, 0)])

    # Strict mode (issue #118): In particular, we stop immediately if any
    # one iterable is exhausted, not waiting for the others
    slow_iterable_continued_after_sleep = asyncio.Event()

    async def fast_iterable():
        yield 0
        await asyncio.sleep(1)

    async def slow_iterable():
        yield 0
        await asyncio.sleep(2)
        slow_iterable_continued_after_sleep.set()

    xs = stream.zip(fast_iterable(), slow_iterable())
    await assert_run(xs, [(0, 0)])
    assert not slow_iterable_continued_after_sleep.is_set()


@pytest.mark.asyncio
async def test_map(assert_run, assert_cleanup):
    def square_target(arg: int, *_) -> int:
        return arg**2

    def sum_target(a: int, b: int, *_) -> int:
        return a + b

    async def sleep_only(arg: float, *_) -> None:
        return await asyncio.sleep(arg)

    async def sleep_and_result(arg: float, result: int, *_) -> int:
        return await asyncio.sleep(arg, result)

    def not_a_coro_function(arg: int, *_) -> Awaitable[int]:
        return asyncio.sleep(arg, arg)

    # Synchronous/simple
    with assert_cleanup():
        xs = stream.range(5) | pipe.map(square_target)
        expected = [x**2 for x in range(5)]
        await assert_run(xs, expected)

    # Synchronous/multiple
    with assert_cleanup():
        xs = stream.range(5)
        ys = xs | pipe.map(sum_target, xs)
        expected = [x * 2 for x in range(5)]
        await assert_run(ys, expected)

    # Asynchronous/simple/concurrent
    with assert_cleanup() as loop:
        xs = stream.range(1, 4) | pipe.map(sleep_only)
        expected = [None] * 3
        await assert_run(xs, expected)
        assert loop.steps == [1, 1, 1]

    # Asynchronous/simple/sequential
    with assert_cleanup() as loop:
        xs = stream.range(1, 4) | pipe.map(sleep_only, task_limit=1)
        expected = [None] * 3
        await assert_run(xs, expected)
        assert loop.steps == [1, 2, 3]

    # Asynchronous/multiple/concurrent
    with assert_cleanup() as loop:
        xs = stream.range(1, 4)
        ys = xs | pipe.map(sleep_and_result, xs)
        await assert_run(ys, [1, 2, 3])
        assert loop.steps == [1, 1, 1]

    # Asynchronous/multiple/sequential
    with assert_cleanup() as loop:
        xs = stream.range(1, 4)
        ys = xs | pipe.map(sleep_and_result, xs, task_limit=1)
        await assert_run(ys, [1, 2, 3])
        assert loop.steps == [1, 2, 3]

    # As completed
    with assert_cleanup() as loop:
        xs = stream.iterate([2, 4, 1, 3, 5])
        ys = xs | pipe.map(sleep_and_result, xs, ordered=False)
        await assert_run(ys, [1, 2, 3, 4, 5])
        assert loop.steps == [1, 1, 1, 1, 1]

    # Invalid argument
    with pytest.raises(ValueError):
        await (stream.range(1, 4) | pipe.map(sleep_only, task_limit=0))

    # Break
    with assert_cleanup() as loop:
        xs = stream.count(1)
        ys = xs | pipe.map(sleep_and_result, xs, task_limit=10)
        await assert_run(ys[:3], [1, 2, 3])
        assert loop.steps == [1, 1, 1]

    # Stuck
    with assert_cleanup():
        xs = stream.count(1)
        ys = xs | pipe.map(sleep_and_result, xs, task_limit=1) | pipe.timeout(5)
        await assert_run(ys, [1, 2, 3, 4], asyncio.TimeoutError())

    # Force await
    with assert_cleanup():
        xs = stream.iterate([1, 2, 3])
        ys = xs | pipe.map(async_(not_a_coro_function))
        await assert_run(ys, [1, 2, 3])
        assert loop.steps == [1, 1, 1]

    # Map await_
    with assert_cleanup() as loop:
        xs = stream.iterate(map(lambda x: asyncio.sleep(x, x), [1, 2, 3]))
        ys = xs | pipe.map(await_)  # type: ignore
        await assert_run(ys, [1, 2, 3])
        assert loop.steps == [1, 1, 1]


@pytest.mark.asyncio
async def test_merge(assert_run, assert_cleanup):
    with assert_cleanup() as loop:
        xs = stream.range(1, 5, 2, interval=2) | pipe.delay(1)
        ys = stream.range(0, 5, 2, interval=2) | pipe.merge(xs)
        await assert_run(ys, [0, 1, 2, 3, 4])
        assert loop.steps == [1, 1, 1, 1]

    with assert_cleanup():
        xs = stream.range(1, 5, 2, interval=2) | pipe.delay(1)
        ys = stream.range(0, 5, 2, interval=2) | pipe.merge(xs)
        await assert_run(ys[:3], [0, 1, 2])
        assert loop.steps == [1, 1]

    with assert_cleanup():
        xs = stream.just(1) + stream.never()
        ys = xs | pipe.merge(xs) | pipe.timeout(1)
        await assert_run(ys, [1, 1], asyncio.TimeoutError())
        assert loop.steps == [1]

    # Reproduce issue #65
    with assert_cleanup():
        xs = stream.iterate([1, 2])
        ys = stream.iterate([3, 4])
        zs = stream.merge(xs, ys) | pipe.take(3)
        await assert_run(zs, [1, 2, 3])

    with assert_cleanup():
        xs = stream.iterate([1, 2, 3])
        ys = stream.throw(ZeroDivisionError())
        zs = stream.merge(xs, ys) | pipe.delay(1) | pipe.take(3)
        await assert_run(zs, [1, 2, 3])

    # Silencing of a CancelledError

    async def agen1():
        if False:
            yield
        try:
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            return

    async def agen2():
        yield 1

    with assert_cleanup():
        xs = stream.merge(agen1(), agen2()) | pipe.delay(1) | pipe.take(1)
        await assert_run(xs, [1])

    # Empty merge (issue #95)
    xs = stream.merge()
    await assert_run(xs, [])


@pytest.mark.asyncio
async def test_ziplatest(assert_run, assert_cleanup):
    with assert_cleanup() as loop:
        xs = stream.range(0, 5, 2, interval=2)
        ys = stream.range(1, 5, 2, interval=2) | pipe.delay(1)
        zs = stream.ziplatest(xs, ys, default="▲")
        await assert_run(zs, [(0, "▲"), (0, 1), (2, 1), (2, 3), (4, 3)])
        assert loop.steps == [1, 1, 1, 1]

    with assert_cleanup() as loop:
        xs = stream.range(0, 5, 2, interval=2)
        ys = stream.range(1, 5, 2, interval=2) | pipe.delay(1)
        zs = stream.ziplatest(xs, ys, partial=False)
        await assert_run(zs, [(0, 1), (2, 1), (2, 3), (4, 3)])
        assert loop.steps == [1, 1, 1, 1]

    # Empty ziplatest (issue #95)
    xs = stream.ziplatest()
    await assert_run(xs, [])
