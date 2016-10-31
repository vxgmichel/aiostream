
import asyncio
import pytest

from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop, add_resource

# Pytest fixtures
assert_run, event_loop


@pytest.mark.asyncio
async def test_take(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.count() | add_resource.pipe(1) | pipe.take(3)
        await assert_run(xs, [0, 1, 2])

    with event_loop.assert_cleanup():
        xs = stream.count() | add_resource.pipe(1) | pipe.take(0)
        await assert_run(xs, [])


@pytest.mark.asyncio
async def test_take_last(assert_run, event_loop):
    xs = stream.range(10) | add_resource.pipe(1) | pipe.take_last(3)
    await assert_run(xs, [7, 8, 9])


@pytest.mark.asyncio
async def test_skip(assert_run, event_loop):
    xs = stream.range(10) | add_resource.pipe(1) | pipe.skip(8)
    await assert_run(xs, [8, 9])


@pytest.mark.asyncio
async def test_skip_last(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(10) | add_resource.pipe(1) | pipe.skip_last(8)
        await assert_run(xs, [0, 1])

    with event_loop.assert_cleanup():
        xs = stream.range(10) | add_resource.pipe(1) | pipe.skip_last(0)
        await assert_run(xs, list(range(10)))


@pytest.mark.asyncio
async def test_filter_index(assert_run, event_loop):
    xs = (stream.range(10)
          | add_resource.pipe(1)
          | pipe.filter_index(lambda x: x in [4, 7, 8]))
    await assert_run(xs, [4, 7, 8])


@pytest.mark.asyncio
async def test_slice(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = (stream.range(10, 20)
              | add_resource.pipe(1)
              | pipe.slice(2))
        await assert_run(xs, [10, 11])

    with event_loop.assert_cleanup():
        xs = (stream.range(10, 20)
              | add_resource.pipe(1)
              | pipe.slice(8, None))
        await assert_run(xs, [18, 19])

    with event_loop.assert_cleanup():
        xs = (stream.range(10, 20)
              | add_resource.pipe(1)
              | pipe.slice(-3, -1))
        await assert_run(xs, [17, 18])

    with event_loop.assert_cleanup():
        xs = (stream.range(10, 20)
              | add_resource.pipe(1)
              | pipe.slice(-5, -1, 2))
        await assert_run(xs, [15, 17])

    xs = stream.range(10, 20) | pipe.slice(5, 1, -1)
    exc = ValueError('Negative step not supported')
    await assert_run(xs, [], exc)

    xs = stream.range(10, 20) | pipe.slice(-8, 8)
    exc = ValueError('Positive stop and negative start is not supported')
    await assert_run(xs, [], exc)


@pytest.mark.asyncio
async def test_item_at(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.item_at(2)
        await assert_run(xs, [2])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.item_at(-2)
        await assert_run(xs, [3])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.item_at(10)
        exception = IndexError('Index out of range',)
        await assert_run(xs, [], exception)

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.item_at(-10)
        exception = IndexError('Index out of range',)
        await assert_run(xs, [], exception)


@pytest.mark.asyncio
async def test_get_item(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.get_item(2)
        await assert_run(xs, [2])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        await assert_run(xs[2], [2])

    with event_loop.assert_cleanup():
        s = slice(1, 3)
        xs = stream.range(5) | add_resource.pipe(1) | pipe.get_item(s)
        await assert_run(xs, [1, 2])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        await assert_run(xs[1:3], [1, 2])

    with event_loop.assert_cleanup():
        s = slice(1, 5, 2)
        xs = stream.range(5) | add_resource.pipe(1) | pipe.get_item(s)
        await assert_run(xs, [1, 3])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        await assert_run(xs[1:5:2], [1, 3])

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        exception = TypeError('Not a valid index (int or slice)')
        await assert_run(xs[None], [], exception)


@pytest.mark.asyncio
async def test_filter(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = (stream.range(1, 10)
              | add_resource.pipe(1)
              | pipe.filter(lambda x: x in [4, 7, 8]))
        await assert_run(xs, [4, 7, 8])

    async def afunc(x):
        await asyncio.sleep(1)
        return x in [3, 6, 9]

    with event_loop.assert_cleanup():
        xs = (stream.range(1, 10)
              | add_resource.pipe(1)
              | pipe.filter(afunc))
        await assert_run(xs, [3, 6, 9])
        assert event_loop.steps == [1]*10
