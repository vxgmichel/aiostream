import asyncio
import pytest

from aiostream import stream, pipe
from aiostream.test_utils import add_resource


@pytest.mark.asyncio
async def test_take(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.count() | add_resource.pipe(1) | pipe.take(3)
        await assert_run(xs, [0, 1, 2])

    with assert_cleanup():
        xs = stream.count() | add_resource.pipe(1) | pipe.take(0)
        await assert_run(xs, [])


@pytest.mark.asyncio
async def test_takelast(assert_run):
    xs = stream.range(10) | add_resource.pipe(1) | pipe.takelast(3)
    await assert_run(xs, [7, 8, 9])


@pytest.mark.asyncio
async def test_skip(assert_run, assert_cleanup):
    xs = stream.range(10) | add_resource.pipe(1) | pipe.skip(8)
    await assert_run(xs, [8, 9])


@pytest.mark.asyncio
async def test_skiplast(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(10) | add_resource.pipe(1) | pipe.skiplast(8)
        await assert_run(xs, [0, 1])

    with assert_cleanup():
        xs = stream.range(10) | add_resource.pipe(1) | pipe.skiplast(0)
        await assert_run(xs, list(range(10)))


@pytest.mark.asyncio
async def test_filterindex(assert_run, assert_cleanup):
    filterindex = stream.select.filterindex
    xs = (
        stream.range(10)
        | add_resource.pipe(1)
        | filterindex.pipe(lambda x: x in [4, 7, 8])
    )
    await assert_run(xs, [4, 7, 8])


@pytest.mark.asyncio
async def test_slice(assert_run, assert_cleanup):
    slice = stream.select.slice

    with assert_cleanup():
        xs = stream.range(10, 20) | add_resource.pipe(1) | slice.pipe(2)
        await assert_run(xs, [10, 11])

    with assert_cleanup():
        xs = stream.range(10, 20) | add_resource.pipe(1) | slice.pipe(8, None)
        await assert_run(xs, [18, 19])

    with assert_cleanup():
        xs = stream.range(10, 20) | add_resource.pipe(1) | slice.pipe(-3, -1)
        await assert_run(xs, [17, 18])

    with assert_cleanup():
        xs = stream.range(10, 20) | add_resource.pipe(1) | slice.pipe(-5, -1, 2)
        await assert_run(xs, [15, 17])

    with pytest.raises(ValueError):
        xs = stream.range(10, 20) | slice.pipe(5, 1, -1)

    with pytest.raises(ValueError):
        xs = stream.range(10, 20) | slice.pipe(-8, 8)


@pytest.mark.asyncio
async def test_item(assert_run, assert_cleanup):
    item = stream.select.item

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | item.pipe(2)
        await assert_run(xs, [2])

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | item.pipe(-2)
        await assert_run(xs, [3])

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | item.pipe(10)
        exception = IndexError(
            "Index out of range",
        )
        await assert_run(xs, [], exception)

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | item.pipe(-10)
        exception = IndexError(
            "Index out of range",
        )
        await assert_run(xs, [], exception)


@pytest.mark.asyncio
async def test_getitem(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1) | pipe.getitem(2)
        await assert_run(xs, [2])

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        await assert_run(xs[2], [2])

    with assert_cleanup():
        s = slice(1, 3)
        xs = stream.range(5) | add_resource.pipe(1) | pipe.getitem(s)
        await assert_run(xs, [1, 2])

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        await assert_run(xs[1:3], [1, 2])

    with assert_cleanup():
        s = slice(1, 5, 2)
        xs = stream.range(5) | add_resource.pipe(1) | pipe.getitem(s)
        await assert_run(xs, [1, 3])

    with assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        await assert_run(xs[1:5:2], [1, 3])

    with pytest.raises(TypeError):
        xs = stream.range(5)[None]  # type: ignore


@pytest.mark.asyncio
async def test_filter(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = (
            stream.range(1, 10)
            | add_resource.pipe(1)
            | pipe.filter(lambda x: x in [4, 7, 8])
        )
        await assert_run(xs, [4, 7, 8])

    async def afunc(x):
        await asyncio.sleep(1)
        return x in [3, 6, 9]

    with assert_cleanup() as loop:
        xs = stream.range(1, 10) | add_resource.pipe(1) | pipe.filter(afunc)
        await assert_run(xs, [3, 6, 9])
        assert loop.steps == [1] * 10


@pytest.mark.asyncio
async def test_until(assert_run, assert_cleanup):
    with assert_cleanup():
        xs = stream.range(1, 10) | add_resource.pipe(1) | pipe.until(lambda x: x == 3)
        await assert_run(xs, [1, 2, 3])

    async def afunc(x):
        await asyncio.sleep(1)
        return x == 3

    with assert_cleanup() as loop:
        xs = stream.range(1, 10) | add_resource.pipe(1) | pipe.until(afunc)
        await assert_run(xs, [1, 2, 3])
        assert loop.steps == [1] * 4


@pytest.mark.asyncio
async def test_takewhile(assert_run, assert_cleanup):
    def less_than_4(x: int) -> bool:
        return x < 4

    with assert_cleanup():
        xs = stream.range(1, 10) | add_resource.pipe(1) | pipe.takewhile(less_than_4)
        await assert_run(xs, [1, 2, 3])

    async def afunc(x):
        await asyncio.sleep(1)
        return x < 4

    with assert_cleanup() as loop:
        xs = stream.range(1, 10) | add_resource.pipe(1) | pipe.takewhile(afunc)
        await assert_run(xs, [1, 2, 3])
        assert loop.steps == [1] * 5


@pytest.mark.asyncio
async def test_dropwhile(assert_run, assert_cleanup):
    def less_than_7(x: int) -> bool:
        return x < 7

    with assert_cleanup():
        xs = stream.range(1, 10) | add_resource.pipe(1) | pipe.dropwhile(less_than_7)
        await assert_run(xs, [7, 8, 9])

    async def afunc(x):
        await asyncio.sleep(1)
        return x < 7

    with assert_cleanup() as loop:
        xs = stream.range(1, 10) | add_resource.pipe(1) | pipe.dropwhile(afunc)
        await assert_run(xs, [7, 8, 9])
        assert loop.steps == [1] * 8
