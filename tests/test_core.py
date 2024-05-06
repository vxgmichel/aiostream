import pytest

from aiostream.core import pipable_operator
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


@pytest.mark.parametrize("operator_param", [operator, pipable_operator])
def test_operator_from_method(operator_param):
    with pytest.raises(ValueError):

        class A:
            @operator_param
            async def method(self, arg):
                yield 1

    with pytest.raises(ValueError):

        class B:
            @operator_param
            async def method(cls, arg):
                yield 1

    with pytest.raises(ValueError):

        class C:
            @operator_param
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
        async with xs:  # type: ignore
            assert False

    assert "Use the `stream` method" in str(ctx.value)


def test_compatibility():
    @operator
    async def test1():
        yield 1

    with pytest.raises(AttributeError):
        test1.pipe  # type: ignore

    match = "The `pipable` argument is deprecated."
    with pytest.warns(DeprecationWarning, match=match):

        @operator()
        async def test2():
            yield 1

    with pytest.raises(AttributeError):
        test2.pipe  # type: ignore

    with pytest.warns(DeprecationWarning, match=match):

        @operator(pipable=False)
        async def test3():
            yield 1

    with pytest.raises(AttributeError):
        test3.pipe  # type: ignore

    with pytest.warns(DeprecationWarning, match=match):

        @operator(pipable=True)
        async def test4(source):
            yield 1

    test4.pipe  # type: ignore

    with pytest.warns(DeprecationWarning, match=match):

        async def test5(source):
            yield 1

        test5_operator = operator(test5, pipable=True)
        test5_operator.pipe  # type: ignore


def test_pipable_operator_with_variadic_args():

    with pytest.raises(ValueError):

        @pipable_operator
        async def test1(*args):
            yield 1
