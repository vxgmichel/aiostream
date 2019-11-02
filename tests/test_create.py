
import pytest
import asyncio
from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop

# Pytest fixtures
assert_run, event_loop


@pytest.mark.asyncio
async def test_just(assert_run):
    value = 3
    xs = stream.just(value)
    await assert_run(xs, [3])

    async def four():
        return 4

    xs = stream.just(four())
    await assert_run(xs, [4])


@pytest.mark.asyncio
async def test_call(assert_run):

    def myfunc(a, b, c=0, d=4):
        return a, b, c, d

    xs = stream.call(myfunc, 1, 2, c=3)
    await assert_run(xs, [(1, 2, 3, 4)])

    async def myasyncfunc(a, b, c=0, d=4):
        return a, b, c, d

    xs = stream.call(myasyncfunc, 1, 2, c=3)
    await assert_run(xs, [(1, 2, 3, 4)])


@pytest.mark.asyncio
async def test_throw(assert_run):
    exception = RuntimeError('Oops')
    xs = stream.throw(exception)
    await assert_run(xs, [], exception)


@pytest.mark.asyncio
async def test_empty(assert_run):
    xs = stream.empty()
    await assert_run(xs, [])


@pytest.mark.asyncio
async def test_never(assert_run, event_loop):
    xs = stream.never() | pipe.timeout(30.)
    await assert_run(xs, [], asyncio.TimeoutError())
    assert event_loop.steps == [30.]


@pytest.mark.asyncio
async def test_repeat(assert_run):
    xs = stream.repeat(1, 3)
    await assert_run(xs, [1, 1, 1])

    xs = stream.repeat(2)[:4]
    await assert_run(xs, [2, 2, 2, 2])


@pytest.mark.asyncio
async def test_range(assert_run, event_loop):
    xs = stream.range(3, 10, 2, interval=1.0)
    await assert_run(xs, [3, 5, 7, 9])
    assert event_loop.steps == [1, 1, 1]


@pytest.mark.asyncio
async def test_count(assert_run):
    xs = stream.count(3, 2)[:4]
    await assert_run(xs, [3, 5, 7, 9])


@pytest.mark.asyncio
async def test_iterable(assert_run):
    lst = [9, 4, 8, 3, 1]

    xs = stream.create.from_iterable(lst)
    await assert_run(xs, lst)

    xs = stream.iterate(lst)
    await assert_run(xs, lst)


@pytest.mark.asyncio
async def test_async_iterable(assert_run, event_loop):

    async def agen():
        for x in range(2, 5):
            yield await asyncio.sleep(1.0, result=x**2)

    xs = stream.create.from_async_iterable(agen())
    await assert_run(xs, [4, 9, 16])
    assert event_loop.steps == [1.0, 1.0, 1.0]

    xs = stream.iterate(agen())
    await assert_run(xs, [4, 9, 16])
    assert event_loop.steps == [1.0, 1.0, 1.0]*2


@pytest.mark.asyncio
async def test_iterate_from_callback_and_sentinel(assert_run):
    lst = [None, 3, 2, 1]
    xs = stream.create.from_callable_and_sentinel(lst.pop, None)
    await assert_run(xs, [1, 2, 3])
    assert lst == []

    lst = [None, 3, 2, 1]
    xs = stream.iterate(lst.pop, None)
    await assert_run(xs, [1, 2, 3])
    assert lst == []


@pytest.mark.asyncio
async def test_iterate_from_async_callback_and_sentinel(assert_run):
    queue = asyncio.Queue()
    await queue.put(1)
    await queue.put(2)
    await queue.put(3)
    await queue.put(None)

    xs = stream.create.from_callable_and_sentinel(queue.get, None)
    await assert_run(xs, [1, 2, 3])

    await queue.put(1)
    await queue.put(2)
    await queue.put(3)
    await queue.put(None)

    xs = stream.iterate(queue.get, None)
    await assert_run(xs, [1, 2, 3])


@pytest.mark.asyncio
async def test_non_iterable(assert_run):
    with pytest.raises(TypeError):
        stream.iterate(None)

    with pytest.raises(TypeError):
        stream.create.from_async_iterable(None)


@pytest.mark.asyncio
async def test_preserve(assert_run, event_loop):

    async def agen():
        yield 1
        yield 2

    xs = stream.iterate(agen())[0]
    await assert_run(xs, [1])
    await assert_run(xs, [], IndexError('Index out of range'))

    ys = stream.preserve(agen())[0]
    await assert_run(ys, [1])
    await assert_run(ys, [2])
