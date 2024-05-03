import pytest

from aiostream import stream, pipe
from aiostream.core import Stream


@pytest.mark.asyncio
async def test_concatmap(assert_run, assert_cleanup):
    def target1(x: int, *_) -> Stream[int]:
        return stream.range(x, x + 2, interval=5)

    def target2(x: int, *_) -> Stream[int]:
        return stream.range(x, x + 4, interval=1)

    def target3(x: int, *_) -> Stream[int]:
        return stream.range(0, 3, interval=1) if x else stream.throw(ZeroDivisionError)

    # Concurrent run
    with assert_cleanup() as loop:
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.concatmap(target1)
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert loop.steps == [1, 1, 3, 5, 5]

    # Sequential run
    with assert_cleanup() as loop:
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.concatmap(target1, task_limit=1)
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert loop.steps == [5, 1, 5, 1, 5]

    # Limited run
    with assert_cleanup() as loop:
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.concatmap(target1, task_limit=2)
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert loop.steps == [1, 4, 1, 4, 5]

    # Make sure item arrive as soon as possible
    with assert_cleanup() as loop:
        xs = stream.just(2)
        ys = xs | pipe.concatmap(target2)
        zs = ys | pipe.timeout(2)  # Sould NOT raise
        await assert_run(zs, [2, 3, 4, 5])
        assert loop.steps == [1, 1, 1]

    # An exception might get discarded if the result can be produced before the
    # processing of the exception is required
    with assert_cleanup() as loop:
        xs = stream.iterate([True, False])
        ys = xs | pipe.concatmap(target3)
        zs = ys | pipe.take(3)
        await assert_run(zs, [0, 1, 2])
        assert loop.steps == [1, 1]


@pytest.mark.asyncio
async def test_flatmap(assert_run, assert_cleanup):
    def target1(x: int, *_) -> Stream[int]:
        return stream.range(x, x + 2, interval=5)

    # Concurrent run
    with assert_cleanup() as loop:
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.flatmap(target1)
        await assert_run(ys, [0, 2, 4, 1, 3, 5])
        assert loop.steps == [1, 1, 3, 1, 1]

    # Sequential run
    with assert_cleanup() as loop:
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.flatmap(target1, task_limit=1)
        await assert_run(ys, [0, 1, 2, 3, 4, 5])
        assert loop.steps == [5, 1, 5, 1, 5]

    # Limited run
    with assert_cleanup() as loop:
        xs = stream.range(0, 6, 2, interval=1)
        ys = xs | pipe.flatmap(target1, task_limit=2)
        await assert_run(ys, [0, 2, 1, 3, 4, 5])
        assert loop.steps == [1, 4, 1, 5]


@pytest.mark.asyncio
async def test_switchmap(assert_run, assert_cleanup):
    def target1(x: int, *_) -> Stream[int]:
        return stream.range(x, x + 5, interval=1)

    def target2(x: int, *_) -> Stream[int]:
        return stream.range(x, x + 2, interval=2)

    with assert_cleanup() as loop:
        xs = stream.range(0, 30, 10, interval=3)
        ys = xs | pipe.switchmap(target1)
        await assert_run(ys, [0, 1, 2, 10, 11, 12, 20, 21, 22, 23, 24])
        assert loop.steps == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

    # Test cleanup procedure
    with assert_cleanup() as loop:
        xs = stream.range(0, 5, interval=1)
        ys = xs | pipe.switchmap(target2)
        await assert_run(ys[:3], [0, 1, 2])
        assert loop.steps == [1, 1]
