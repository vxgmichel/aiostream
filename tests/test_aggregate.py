
import asyncio
import operator

from aiostream import stream, pipe


def test_accumulate_no_arguments(assert_run, add_resource):
    xs = stream.range(5) | add_resource.pipe(1) | pipe.accumulate()
    assert_run(xs, [0, 1, 3, 6, 10], steps=[1])


def test_accumulate_with_sync_function(assert_run, add_resource):
    xs = (stream.range(2, 4)
          | add_resource.pipe(1)
          | pipe.accumulate(func=operator.mul, initializer=2))
    assert_run(xs, [2, 4, 12], steps=[1])


def test_accumulate_empty_stream(assert_run, add_resource):
    xs = stream.range(0) | add_resource.pipe(1) | pipe.accumulate()
    assert_run(xs, [], steps=[1])


def test_accumulate_with_async_function(assert_run, add_resource):

    async def sleepmax(x, y):
        return await asyncio.sleep(1, result=max(x, y))

    xs = stream.range(3) | add_resource.pipe(1) | pipe.accumulate(sleepmax)
    assert_run(xs, [0, 1, 2], steps=[1, 1, 1])


def test_reduce_with_min(assert_run, add_resource):
    xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(min)
    assert_run(xs, [0], steps=[1])


def test_reduce_with_max(assert_run, add_resource):
    xs = stream.range(5) | add_resource.pipe(1) | pipe.reduce(max)
    assert_run(xs, [4], steps=[1])


def test_reduce_with_empty_stream(assert_run, add_resource):
    exception = TypeError("reduce() of empty sequence with no initial value")
    xs = stream.range(0) | add_resource.pipe(1) | pipe.reduce(max)
    assert_run(xs, [], exception, steps=[1])


def test_list_simple(assert_run, add_resource):
    xs = stream.range(5) | add_resource.pipe(1) | pipe.list()
    assert_run(xs, [[0, 1, 2, 3, 4]], steps=[1])


def test_list_with_empty_stream(assert_run, add_resource):
    xs = stream.range(0) | add_resource.pipe(1) | pipe.list()
    assert_run(xs, [[]], steps=[1])
