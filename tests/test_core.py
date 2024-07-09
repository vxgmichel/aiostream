import inspect
import pytest

from aiostream.core import pipable_operator, sources_operator
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


@pytest.mark.parametrize(
    "operator_param", [operator, pipable_operator, sources_operator]
)
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


def test_sources_operator_with_postional_args():
    with pytest.raises(ValueError):

        @sources_operator
        async def test1(source):
            yield 1


def test_introspection_for_operator():
    # Extract original information
    original = stream.range.original  # type: ignore
    original_doc = original.__doc__
    assert original_doc is not None
    assert original_doc.splitlines()[0] == "Generate a given range of numbers."
    assert (
        str(inspect.signature(original))
        == "(*args: 'int', interval: 'float' = 0.0) -> 'AsyncIterator[int]'"
    )

    # Check the stream operator
    assert str(stream.range) == repr(stream.range) == "aiostream.stream.create.range"
    assert stream.range.__module__ == "aiostream.stream.create"
    assert stream.range.__doc__ == original_doc

    # Check the raw method
    assert stream.range.raw.__qualname__ == "range.raw"
    assert stream.range.raw.__module__ == "aiostream.stream.create"
    assert stream.range.raw.__doc__ == original_doc
    assert (
        str(inspect.signature(stream.range.raw))
        == "(*args: 'int', interval: 'float' = 0.0) -> 'AsyncIterator[int]'"
    )

    # Check the __call__ method
    assert stream.range.__call__.__qualname__ == "range.__call__"
    assert stream.range.__call__.__module__ == "aiostream.stream.create"
    assert stream.range.__call__.__doc__ == original_doc
    assert (
        str(inspect.signature(stream.range.__call__))
        == "(*args: 'int', interval: 'float' = 0.0) -> 'Stream[int]'"
    )


def test_introspection_for_pipable_operator():
    # Extract original information
    original = stream.take.original  # type: ignore
    original_doc = original.__doc__
    assert original_doc is not None
    assert (
        original_doc.splitlines()[0]
        == "Forward the first ``n`` elements from an asynchronous sequence."
    )
    assert (
        str(inspect.signature(original))
        == "(source: 'AsyncIterable[T]', n: 'int') -> 'AsyncIterator[T]'"
    )

    # Check the stream operator
    assert str(stream.take) == repr(stream.take) == "aiostream.stream.select.take"
    assert stream.take.__module__ == "aiostream.stream.select"
    assert stream.take.__doc__ == original_doc

    # Check the raw method
    assert stream.take.raw.__qualname__ == "take.raw"
    assert stream.take.raw.__module__ == "aiostream.stream.select"
    assert stream.take.raw.__doc__ == original_doc
    assert (
        str(inspect.signature(stream.take.raw))
        == "(source: 'AsyncIterable[T]', n: 'int') -> 'AsyncIterator[T]'"
    )

    # Check the __call__ method
    assert stream.take.__call__.__qualname__ == "take.__call__"
    assert stream.take.__call__.__module__ == "aiostream.stream.select"
    assert stream.take.__call__.__doc__ == original_doc
    assert (
        str(inspect.signature(stream.take.__call__))
        == "(source: 'AsyncIterable[T]', n: 'int') -> 'Stream[T]'"
    )

    # Check the pipe method
    assert stream.take.pipe.__qualname__ == "take.pipe"
    assert stream.take.pipe.__module__ == "aiostream.stream.select"
    assert (
        stream.take.pipe.__doc__
        == 'Piped version of the "take" stream operator.\n\n    ' + original_doc
    )
    assert (
        str(inspect.signature(stream.take.pipe))
        == "(n: 'int') -> 'Callable[[AsyncIterable[X]], Stream[T]]'"
    )


def test_introspection_for_sources_operator():
    # Extract original information
    original = stream.zip.original  # type: ignore
    original_doc = original.__doc__
    assert original_doc is not None
    assert (
        original_doc.splitlines()[0]
        == "Combine and forward the elements of several asynchronous sequences."
    )
    assert (
        str(inspect.signature(original))
        == "(*sources: 'AsyncIterable[T]', strict: 'bool' = False) -> 'AsyncIterator[tuple[T, ...]]'"
    )

    # Check the stream operator
    assert str(stream.zip) == repr(stream.zip) == "aiostream.stream.combine.zip"
    assert stream.zip.__module__ == "aiostream.stream.combine"
    assert stream.zip.__doc__ == original_doc

    # Check the raw method
    assert stream.zip.raw.__qualname__ == "zip.raw"
    assert stream.zip.raw.__module__ == "aiostream.stream.combine"
    assert stream.zip.raw.__doc__ == original_doc
    assert (
        str(inspect.signature(stream.zip.raw))
        == "(*sources: 'AsyncIterable[T]', strict: 'bool' = False) -> 'AsyncIterator[tuple[T, ...]]'"
    )

    # Check the __call__ method
    assert stream.zip.__call__.__qualname__ == "zip.__call__"
    assert stream.zip.__call__.__module__ == "aiostream.stream.combine"
    assert stream.zip.__call__.__doc__ == original_doc
    assert (
        str(inspect.signature(stream.zip.__call__))
        == "(*sources: 'AsyncIterable[T]', strict: 'bool' = False) -> 'Stream[tuple[T, ...]]'"
    )

    # Check the pipe method
    assert stream.zip.pipe.__qualname__ == "zip.pipe"
    assert stream.zip.pipe.__module__ == "aiostream.stream.combine"
    assert (
        stream.zip.pipe.__doc__
        == 'Piped version of the "zip" stream operator.\n\n    ' + original_doc
    )
    assert (
        str(inspect.signature(stream.zip.pipe))
        == "(*sources: 'AsyncIterable[T]', strict: 'bool' = False) -> 'Callable[[AsyncIterable[Any]], Stream[tuple[T, ...]]]'"
    )
