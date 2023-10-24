"""Core objects for stream operators."""
from __future__ import annotations

import inspect
import functools
import sys
import warnings

from .aiter_utils import AsyncIteratorContext, aiter, assert_async_iterable
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Generator,
    Iterator,
    Protocol,
    Union,
    TypeVar,
    cast,
    AsyncIterable,
    Awaitable,
)

from typing_extensions import ParamSpec, Concatenate


__all__ = ["Stream", "Streamer", "StreamEmpty", "operator", "streamcontext"]


# Exception


class StreamEmpty(Exception):
    """Exception raised when awaiting an empty stream."""

    pass


# Helpers

T = TypeVar("T")
X = TypeVar("X")
A = TypeVar("A", contravariant=True)
P = ParamSpec("P")
Q = ParamSpec("Q")

# Hack for python 3.8 compatibility
if sys.version_info < (3, 9):
    P = TypeVar("P")


async def wait_stream(aiterable: BaseStream[T]) -> T:
    """Wait for an asynchronous iterable to finish and return the last item.

    The iterable is executed within a safe stream context.
    A StreamEmpty exception is raised if the sequence is empty.
    """

    class Unassigned:
        pass

    last_item: Unassigned | T = Unassigned()

    async with streamcontext(aiterable) as streamer:
        async for item in streamer:
            last_item = item

    if isinstance(last_item, Unassigned):
        raise StreamEmpty()
    return last_item


# Core objects


class BaseStream(AsyncIterable[T], Awaitable[T]):
    """
    Base class for streams.

    See `Stream` and `Streamer` for more information.
    """

    def __init__(self, factory: Callable[[], AsyncIterable[T]]) -> None:
        """Initialize the stream with an asynchronous iterable factory.

        The factory is a callable and takes no argument.
        The factory return value is an asynchronous iterable.
        """
        aiter = factory()
        assert_async_iterable(aiter)
        self._generator = self._make_generator(aiter, factory)

    def _make_generator(
        self, first: AsyncIterable[T], factory: Callable[[], AsyncIterable[T]]
    ) -> Iterator[AsyncIterable[T]]:
        """Generate asynchronous iterables when required.

        The first iterable is created beforehand for extra checking.
        """
        yield first
        del first
        while True:
            yield factory()

    def __await__(self) -> Generator[Any, None, T]:
        """Await protocol.

        Safely iterate and return the last element.
        """
        return wait_stream(self).__await__()

    def __or__(self, func: Callable[[BaseStream[T]], X]) -> X:
        """Pipe protocol.

        Allow to pipe stream operators.
        """
        return func(self)

    def __add__(self, value: AsyncIterable[X]) -> Stream[Union[X, T]]:
        """Addition protocol.

        Concatenate with a given asynchronous sequence.
        """
        from .stream import chain

        return chain(self, value)

    def __getitem__(self, value: Union[int, slice]) -> Stream[T]:
        """Get item protocol.

        Accept index or slice to extract the corresponding item(s)
        """
        from .stream import getitem

        return getitem(self, value)

    # Disable sync iteration
    # This is necessary because __getitem__ is defined
    # which is a valid fallback for for-loops in python
    __iter__: None = None


class Stream(BaseStream[T]):
    """Enhanced asynchronous iterable.

    It provides the following features:

      - **Operator pipe-lining** - using pipe symbol ``|``
      - **Repeatability** - every iteration creates a different iterator
      - **Safe iteration context** - using ``async with`` and the ``stream``
        method
      - **Simplified execution** - get the last element from a stream using
        ``await``
      - **Slicing and indexing** - using square brackets ``[]``
      - **Concatenation** - using addition symbol ``+``

    It is not meant to be instanciated directly.
    Use the stream operators instead.

    Example::

        xs = stream.count()    # xs is a stream object
        ys = xs | pipe.skip(5) # pipe xs and skip the first 5 elements
        zs = ys[5:10:2]        # slice ys using start, stop and step

        async with zs.stream() as streamer:  # stream zs in a safe context
            async for z in streamer:         # iterate the zs streamer
                print(z)                     # Prints 10, 12, 14

        result = await zs  # await zs and return its last element
        print(result)      # Prints 14
        result = await zs  # zs can be used several times
        print(result)      # Prints 14
    """

    def stream(self) -> Streamer[T]:
        """Return a streamer context for safe iteration.

        Example::

            xs = stream.count()
            async with xs.stream() as streamer:
                async for item in streamer:
                    <block>

        """
        return self.__aiter__()

    def __aiter__(self) -> Streamer[T]:
        """Asynchronous iteration protocol.

        Return a streamer context for safe iteration.
        """
        return streamcontext(next(self._generator))

    # Advertise the proper synthax for entering a stream context

    __aexit__: None = None

    async def __aenter__(self) -> None:
        raise TypeError(
            "A stream object cannot be used as a context manager. "
            "Use the `stream` method instead: "
            "`async with xs.stream() as streamer`"
        )


class Streamer(AsyncIteratorContext[T], BaseStream[T]):
    """Enhanced asynchronous iterator context.

    It is similar to AsyncIteratorContext but provides the stream
    magic methods for concatenation, indexing and awaiting.

    It's not meant to be instanciated directly, use streamcontext instead.

    Example::

        ait = some_asynchronous_iterable()
        async with streamcontext(ait) as streamer:
            async for item in streamer:
                await streamer[5]
    """

    pass


def streamcontext(aiterable: AsyncIterable[T]) -> Streamer[T]:
    """Return a stream context manager from an asynchronous iterable.

    The context management makes sure the aclose asynchronous method
    of the corresponding iterator has run before it exits. It also issues
    warnings and RuntimeError if it is used incorrectly.

    It is safe to use with any asynchronous iterable and prevent
    asynchronous iterator context to be wrapped twice.

    Correct usage::

        ait = some_asynchronous_iterable()
        async with streamcontext(ait) as streamer:
            async for item in streamer:
                <block>

    For streams objects, it is possible to use the stream method instead::

        xs = stream.count()
        async with xs.stream() as streamer:
            async for item in streamer:
                <block>
    """
    aiterator = aiter(aiterable)
    if isinstance(aiterator, Streamer):
        return aiterator
    return Streamer(aiterator)


# Operator type protocol


class OperatorType(Protocol[P, T]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Stream[T]:
        ...

    def raw(self, *args: P.args, **kwargs: P.kwargs) -> AsyncIterator[T]:
        ...


class PipableOperatorType(Protocol[A, P, T]):
    def __call__(
        self, source: AsyncIterable[A], /, *args: P.args, **kwargs: P.kwargs
    ) -> Stream[T]:
        ...

    def raw(
        self, source: AsyncIterable[A], /, *args: P.args, **kwargs: P.kwargs
    ) -> AsyncIterator[T]:
        ...

    def pipe(
        self, *args: P.args, **kwargs: P.kwargs
    ) -> Callable[[AsyncIterable[A]], Stream[T]]:
        ...


# Operator decorator


def operator(
    func: Callable[P, AsyncIterator[T]] | None = None,
    pipable: bool | None = None,
) -> OperatorType[P, T]:
    """Create a stream operator from an asynchronous generator
    (or any function returning an asynchronous iterable).

    Decorator usage::

        @operator
        async def random(offset=0., width=1.):
            while True:
                yield offset + width * random.random()

    The return value is a dynamically created class.
    It has the same name, module and doc as the original function.

    A new stream is created by simply instanciating the operator::

        xs = random()

    The original function is called at instanciation to check that
    signature match. Other methods are available:

      - `original`: the original function as a static method
      - `raw`: same as original but add extra checking

    The `pipable` argument is deprecated, use `pipable_operator` instead.
    """

    # Handle compatibility with legacy (aiostream <= 0.4)
    if pipable is not None or func is None:
        warnings.warn(
            "The `pipable` argument is deprecated. Use either `@operator` or `@pipable_operator` directly.",
            DeprecationWarning,
        )
    if func is None:
        return pipable_operator if pipable else operator  # type: ignore
    if pipable is True:
        return pipable_operator(func)  # type: ignore

    # First check for classmethod instance, to avoid more confusing errors later on
    if isinstance(func, classmethod):
        raise ValueError(
            "An operator cannot be created from a class method, "
            "since the decorated function becomes an operator class"
        )

    # Gather data
    bases = (Stream,)
    name = func.__name__
    module = func.__module__
    extra_doc = func.__doc__
    doc = extra_doc or f"Regular {name} stream operator."

    # Extract signature
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name in ("self", "cls"):
        raise ValueError(
            "An operator cannot be created from a method, "
            "since the decorated function becomes an operator class"
        )

    # Look for "more_sources"
    for i, p in enumerate(parameters):
        if p.name == "more_sources" and p.kind == inspect.Parameter.VAR_POSITIONAL:
            more_sources_index = i
            break
    else:
        more_sources_index = None

    # Injected parameters
    self_parameter = inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    inspect.Parameter("cls", inspect.Parameter.POSITIONAL_OR_KEYWORD)

    # Wrapped static method
    original = func
    original.__qualname__ = name + ".original"

    # Raw static method
    raw = func
    raw.__qualname__ = name + ".raw"

    # Init method
    def init(self: BaseStream[T], *args: P.args, **kwargs: P.kwargs) -> None:
        if more_sources_index is not None:
            for source in args[more_sources_index:]:
                assert_async_iterable(source)
        factory = functools.partial(raw, *args, **kwargs)
        return BaseStream.__init__(self, factory)

    # Customize init signature
    new_parameters = [self_parameter] + parameters
    init.__signature__ = signature.replace(parameters=new_parameters)  # type: ignore[attr-defined]

    # Customize init method
    init.__qualname__ = name + ".__init__"
    init.__name__ = "__init__"
    init.__module__ = module
    init.__doc__ = f"Initialize the {name} stream."

    # Gather attributes
    attrs = {
        "__init__": init,
        "__module__": module,
        "__doc__": doc,
        "raw": staticmethod(raw),
        "original": staticmethod(original),
    }

    # Create operator class
    return cast("OperatorType[P, T]", type(name, bases, attrs))


def pipable_operator(
    func: Callable[Concatenate[AsyncIterable[X], P], AsyncIterator[T]],
) -> PipableOperatorType[X, P, T]:
    """Create a pipable stream operator from an asynchronous generator
    (or any function returning an asynchronous iterable).

    Decorator usage::

        @pipable_operator
        async def multiply(source, factor):
            async with streamcontext(source) as streamer:
                 async for item in streamer:
                     yield factor * item

    The first argument is expected to be the asynchronous iteratable used
    for piping.

    The return value is a dynamically created class.
    It has the same name, module and doc as the original function.

    A new stream is created by simply instanciating the operator::

        xs = random()
        ys = multiply(xs, 2)

    The original function is called at instanciation to check that
    signature match. The source is also checked for asynchronous iteration.

    The operator also have a pipe class method that can be used along
    with the piping synthax::

        xs = random()
        ys = xs | multiply.pipe(2)

    This is strictly equivalent to the previous example.

    Other methods are available:

      - `original`: the original function as a static method
      - `raw`: same as original but add extra checking

    The raw method is useful to create new operators from existing ones::

        @pipable_operator
        def double(source):
            return multiply.raw(source, 2)
    """

    # First check for classmethod instance, to avoid more confusing errors later on
    if isinstance(func, classmethod):
        raise ValueError(
            "An operator cannot be created from a class method, "
            "since the decorated function becomes an operator class"
        )

    # Gather data
    bases = (Stream,)
    name = func.__name__
    module = func.__module__
    extra_doc = func.__doc__
    doc = extra_doc or f"Regular {name} stream operator."

    # Extract signature
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name in ("self", "cls"):
        raise ValueError(
            "An operator cannot be created from a method, "
            "since the decorated function becomes an operator class"
        )

    # Look for "more_sources"
    for i, p in enumerate(parameters):
        if p.name == "more_sources" and p.kind == inspect.Parameter.VAR_POSITIONAL:
            more_sources_index = i
            break
    else:
        more_sources_index = None

    # Injected parameters
    self_parameter = inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    cls_parameter = inspect.Parameter("cls", inspect.Parameter.POSITIONAL_OR_KEYWORD)

    # Wrapped static method
    original = func
    original.__qualname__ = name + ".original"

    # Raw static method
    def raw(
        arg: AsyncIterable[X], *args: P.args, **kwargs: P.kwargs
    ) -> AsyncIterator[T]:
        assert_async_iterable(arg)
        if more_sources_index is not None:
            for source in args[more_sources_index - 1 :]:
                assert_async_iterable(source)
        return func(arg, *args, **kwargs)

    # Custonize raw method
    raw.__signature__ = signature  # type: ignore[attr-defined]
    raw.__qualname__ = name + ".raw"
    raw.__module__ = module
    raw.__doc__ = doc

    # Init method
    def init(
        self: BaseStream[T], arg: AsyncIterable[X], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        assert_async_iterable(arg)
        if more_sources_index is not None:
            for source in args[more_sources_index - 1 :]:
                assert_async_iterable(source)
        factory = functools.partial(raw, arg, *args, **kwargs)
        return BaseStream.__init__(self, factory)

    # Customize init signature
    new_parameters = [self_parameter] + parameters
    init.__signature__ = signature.replace(parameters=new_parameters)  # type: ignore[attr-defined]

    # Customize init method
    init.__qualname__ = name + ".__init__"
    init.__name__ = "__init__"
    init.__module__ = module
    init.__doc__ = f"Initialize the {name} stream."

    # Pipe class method
    def pipe(
        cls: PipableOperatorType[X, P, T],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Callable[[AsyncIterable[X]], Stream[T]]:
        return lambda source: cls(source, *args, **kwargs)

    # Customize pipe signature
    if parameters and parameters[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        new_parameters = [cls_parameter] + parameters[1:]
    else:
        new_parameters = [cls_parameter] + parameters
    pipe.__signature__ = signature.replace(parameters=new_parameters)  # type: ignore[attr-defined]

    # Customize pipe method
    pipe.__qualname__ = name + ".pipe"
    pipe.__module__ = module
    pipe.__doc__ = f'Pipable "{name}" stream operator.'
    if extra_doc:
        pipe.__doc__ += "\n\n    " + extra_doc

    # Gather attributes
    attrs = {
        "__init__": init,
        "__module__": module,
        "__doc__": doc,
        "raw": staticmethod(raw),
        "original": staticmethod(original),
        "pipe": classmethod(pipe),  # type: ignore[arg-type]
    }

    # Create operator class
    return cast(
        "PipableOperatorType[X, P, T]",
        type(name, bases, attrs),
    )
