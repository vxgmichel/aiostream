import pytest

from aiostream.test_utils import add_resource
from aiostream import stream, streamcontext, operator


@pytest.mark.asyncio
async def test_streamcontext(assert_cleanup):
    with assert_cleanup() as loop:
        xs = stream.range(3) | add_resource.pipe(1)
        async with streamcontext(xs) as streamer:
            it = iter(range(3))
            async for item in streamer:
                assert item == next(it)
        assert loop.steps == [1]

    with assert_cleanup() as loop:
        xs = stream.range(5) | add_resource.pipe(1)
        async with xs.stream() as streamer:
            it = iter(range(5))
            async for item in streamer:
                assert item == next(it)
        assert loop.steps == [1]


def test_operator_from_method():
    with pytest.raises(ValueError):

        class A:
            @operator
            async def method(self, arg):
                yield 1

    with pytest.raises(ValueError):

        class B:
            @operator
            async def method(cls, arg):
                yield 1

    with pytest.raises(ValueError):

        class C:
            @operator
            @classmethod
            async def method(cls, arg):
                yield 1


@pytest.mark.asyncio
async def test_error_on_sync_iteration():
    xs = stream.range(3)

    # Stream raises a TypeError
    with pytest.raises(TypeError):
        for x in xs:
            assert False

    # Streamer raises a TypeError
    async with xs.stream() as streamer:
        with pytest.raises(TypeError):
            for x in streamer:
                assert False


@pytest.mark.asyncio
async def test_error_on_entering_a_stream():
    xs = stream.range(3)

    # Stream raises a TypeError
    with pytest.raises(TypeError) as ctx:
        async with xs:
            assert False

    assert "Use the `stream` method" in str(ctx.value)


def test_compatibility():
    @operator
    async def test1():
        yield 1

    with pytest.raises(AttributeError):
        test1.pipe

    match = "The `pipable` argument is deprecated."
    with pytest.warns(DeprecationWarning, match=match):

        @operator()
        async def test2():
            yield 1

    with pytest.raises(AttributeError):
        test2.pipe

    with pytest.warns(DeprecationWarning, match=match):

        @operator(pipable=False)
        async def test3():
            yield 1

    with pytest.raises(AttributeError):
        test3.pipe

    with pytest.warns(DeprecationWarning, match=match):

        @operator(pipable=True)
        async def test4(source):
            yield 1

    test4.pipe
