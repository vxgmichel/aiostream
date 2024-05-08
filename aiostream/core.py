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

T = TypeVar("T", covariant=True)
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


class Operator(Protocol[P, T]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Stream[T]: ...

    @staticmethod
    def raw(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[T]: ...


class PipableOperator(Protocol[A, P, T]):
    def __call__(
        self, source: AsyncIterable[A], /, *args: P.args, **kwargs: P.kwargs
    ) -> Stream[T]: ...

    @staticmethod
    def raw(
        source: AsyncIterable[A], /, *args: P.args, **kwargs: P.kwargs
    ) -> AsyncIterator[T]: ...

    @staticmethod
    def pipe(
        *args: P.args, **kwargs: P.kwargs
    ) -> Callable[[AsyncIterable[A]], Stream[T]]: ...


class SourcesOperator(Protocol[P, T]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Stream[T]: ...

    @staticmethod
    def raw(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[T]: ...

    @staticmethod
    def pipe(
        *args: P.args, **kwargs: P.kwargs
    ) -> Callable[[AsyncIterable[Any]], Stream[T]]: ...


# Operator decorators


def operator(
    func: Callable[P, AsyncIterator[T]] | None = None,
    pipable: bool | None = None,
) -> Operator[P, T]:
    """Create a stream operator from an asynchronous generator
    (or any function returning an asynchronous iterable).

    Decorator usage::

        @operator
        async def random(offset=0., width=1.):
            while True:
                yield offset + width * random.random()

    The return value is a dynamically created callable.
    It has the same name, module and documentation as the original function.

    A new stream is created by simply calling the operator::

        xs = random()

    The original function is called right away to check that the
    signatures match. Other methods are available:

      - `original`: the original function as a static method
      - `raw`: same as original with extra checking

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
    name = func.__name__
    module = func.__module__
    extra_doc = func.__doc__
    doc = extra_doc or f"Regular {name} stream operator."

    # Extract signature
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    return_annotation = signature.return_annotation
    if parameters and parameters[0].name in ("self", "cls"):
        raise ValueError(
            "An operator cannot be created from a method, "
            "since the decorated function becomes an operator class"
        )

    # Wrapped static method
    original_func = func
    original_func.__qualname__ = name + ".original"

    # Raw static method
    raw_func = func
    raw_func.__qualname__ = name + ".raw"

    # Gather attributes
    class OperatorImplementation:

        original = staticmethod(original_func)

        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Stream[T]:
            factory = functools.partial(raw_func, *args, **kwargs)
            return Stream(factory)

        @staticmethod
        def raw(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[T]:
            return raw_func(*args, **kwargs)

        def __repr__(self) -> str:
            return f"{module}.{name}"

        def __str__(self) -> str:
            return f"{module}.{name}"

    # Customize raw method
    OperatorImplementation.raw.__signature__ = signature  # type: ignore[attr-defined]
    OperatorImplementation.raw.__qualname__ = name + ".raw"
    OperatorImplementation.raw.__module__ = module
    OperatorImplementation.raw.__doc__ = doc

    # Customize call method
    self_parameter = inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    new_parameters = [self_parameter] + parameters
    new_return_annotation = (
        return_annotation.replace("AsyncIterator", "Stream")
        if isinstance(return_annotation, str)
        else return_annotation
    )
    OperatorImplementation.__call__.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=new_parameters, return_annotation=new_return_annotation
    )
    OperatorImplementation.__call__.__qualname__ = name + ".__call__"
    OperatorImplementation.__call__.__name__ = "__call__"
    OperatorImplementation.__call__.__module__ = module
    OperatorImplementation.__call__.__doc__ = doc

    # Create operator singleton
    properly_named_class = type(
        name,
        (OperatorImplementation,),
        {
            "__qualname__": name,
            "__module__": module,
            "__doc__": doc,
        },
    )
    operator_instance = properly_named_class()
    return operator_instance


def pipable_operator(
    func: Callable[Concatenate[AsyncIterable[X], P], AsyncIterator[T]],
) -> PipableOperator[X, P, T]:
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

    The return value is a dynamically created callable.
    It has the same name, module and documentation as the original function.

    A new stream is created by simply calling the operator::

        xs = random()
        ys = multiply(xs, 2)

    The original function is called right away (but not awaited) to check that
    signatures match. The sources are also checked for asynchronous iteration.

    The operator also have a `pipe` method that can be used with the pipe
    synthax::

        xs = random()
        ys = xs | multiply.pipe(2)

    This is strictly equivalent to the previous example.

    Other methods are available:

      - `original`: the original function as a static method
      - `raw`: same as original with extra checking

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
    name = func.__name__
    module = func.__module__
    extra_doc = func.__doc__
    doc = extra_doc or f"Regular {name} stream operator."

    # Extract signature
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    return_annotation = signature.return_annotation
    if parameters and parameters[0].name in ("self", "cls"):
        raise ValueError(
            "An operator cannot be created from a method, "
            "since the decorated function becomes an operator class"
        )

    # Check for positional first parameter
    if not parameters or parameters[0].kind not in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        raise ValueError("The first parameter of the operator must be positional")

    # Look for "more_sources"
    for i, p in enumerate(parameters):
        if p.name == "more_sources" and p.kind == inspect.Parameter.VAR_POSITIONAL:
            more_sources_index = i
            break
    else:
        more_sources_index = None

    # Wrapped static method
    original_func = func
    original_func.__qualname__ = name + ".original"

    # Gather attributes
    class PipableOperatorImplementation:

        original = staticmethod(original_func)

        @staticmethod
        def raw(
            arg: AsyncIterable[X], /, *args: P.args, **kwargs: P.kwargs
        ) -> AsyncIterator[T]:
            assert_async_iterable(arg)
            if more_sources_index is not None:
                for source in args[more_sources_index - 1 :]:
                    assert_async_iterable(source)
            return func(arg, *args, **kwargs)

        def __call__(
            self, arg: AsyncIterable[X], /, *args: P.args, **kwargs: P.kwargs
        ) -> Stream[T]:
            assert_async_iterable(arg)
            if more_sources_index is not None:
                for source in args[more_sources_index - 1 :]:
                    assert_async_iterable(source)
            factory = functools.partial(self.raw, arg, *args, **kwargs)
            return Stream(factory)

        @staticmethod
        def pipe(
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> Callable[[AsyncIterable[X]], Stream[T]]:
            return lambda source: operator_instance(source, *args, **kwargs)

        def __repr__(self) -> str:
            return f"{module}.{name}"

        def __str__(self) -> str:
            return f"{module}.{name}"

    # Customize raw method
    PipableOperatorImplementation.raw.__signature__ = signature  # type: ignore[attr-defined]
    PipableOperatorImplementation.raw.__qualname__ = name + ".raw"
    PipableOperatorImplementation.raw.__module__ = module
    PipableOperatorImplementation.raw.__doc__ = doc

    # Customize call method
    self_parameter = inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    new_parameters = [self_parameter] + parameters
    new_return_annotation = (
        return_annotation.replace("AsyncIterator", "Stream")
        if isinstance(return_annotation, str)
        else return_annotation
    )
    PipableOperatorImplementation.__call__.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=new_parameters, return_annotation=new_return_annotation
    )
    PipableOperatorImplementation.__call__.__qualname__ = name + ".__call__"
    PipableOperatorImplementation.__call__.__name__ = "__call__"
    PipableOperatorImplementation.__call__.__module__ = module
    PipableOperatorImplementation.__call__.__doc__ = doc

    # Customize pipe method
    pipe_parameters = parameters[1:]
    pipe_return_annotation = f"Callable[[AsyncIterable[X]], {new_return_annotation}]"
    PipableOperatorImplementation.pipe.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=pipe_parameters, return_annotation=pipe_return_annotation
    )
    PipableOperatorImplementation.pipe.__qualname__ = name + ".pipe"
    PipableOperatorImplementation.pipe.__module__ = module
    PipableOperatorImplementation.pipe.__doc__ = (
        f'Piped version of the "{name}" stream operator.'
    )
    if extra_doc:
        PipableOperatorImplementation.pipe.__doc__ += "\n\n    " + extra_doc

    # Create operator singleton
    properly_named_class = type(
        name,
        (PipableOperatorImplementation,),
        {
            "__qualname__": name,
            "__module__": module,
            "__doc__": doc,
        },
    )
    operator_instance = properly_named_class()
    return operator_instance


def sources_operator(
    func: Callable[P, AsyncIterator[T]],
) -> SourcesOperator[P, T]:
    """Create a pipable stream operator from an asynchronous generator
    (or any function returning an asynchronous iterable) that takes
    a variadic ``*args`` of sources as argument.

    Decorator usage::

        @sources_operator
        async def chain(*sources, repeat=1):
            for source in (sources * repeat):
                async with streamcontext(source) as streamer:
                    async for item in streamer:
                        yield item

    Positional arguments are expected to be asynchronous iterables.

    When used in a pipable context, the asynchronous iterable injected by
    the pipe operator is used as the first argument.

    The return value is a dynamically created callable.
    It has the same name, module and documentation as the original function.

    A new stream is created by simply calling the operator::

        xs = chain()
        ys = chain(random())
        zs = chain(stream.just(0.0), stream.just(1.0), random())

    The original function is called right away (but not awaited) to check that
    signatures match. The sources are also checked for asynchronous iteration.

    The operator also have a `pipe` method that can be used with the pipe
    synthax::

        just_zero = stream.just(0.0)
        zs = just_zero | chain.pipe(stream.just(1.0), random())

    This is strictly equivalent to the previous ``zs`` example.

    Other methods are available:

      - `original`: the original function as a static method
      - `raw`: same as original with extra checking

    The raw method is useful to create new operators from existing ones::

        @sources_operator
        def chain_twice(*sources):
            return chain.raw(*sources, repeat=2)
    """
    # First check for classmethod instance, to avoid more confusing errors later on
    if isinstance(func, classmethod):
        raise ValueError(
            "An operator cannot be created from a class method, "
            "since the decorated function becomes an operator class"
        )

    # Gather data
    name = func.__name__
    module = func.__module__
    extra_doc = func.__doc__
    doc = extra_doc or f"Regular {name} stream operator."

    # Extract signature
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    return_annotation = signature.return_annotation
    if parameters and parameters[0].name in ("self", "cls"):
        raise ValueError(
            "An operator cannot be created from a method, "
            "since the decorated function becomes an operator class"
        )

    # Check for positional first parameter
    if not parameters or parameters[0].kind != inspect.Parameter.VAR_POSITIONAL:
        raise ValueError(
            "The first parameter of the sources operator must be var-positional"
        )

    # Wrapped static method
    original_func = func
    original_func.__qualname__ = name + ".original"

    # Gather attributes
    class SourcesOperatorImplementation:

        original = staticmethod(original_func)

        @staticmethod
        def raw(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[T]:
            for source in args:
                assert_async_iterable(source)
            return func(*args, **kwargs)

        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Stream[T]:
            for source in args:
                assert_async_iterable(source)
            factory = functools.partial(self.raw, *args, **kwargs)
            return Stream(factory)

        @staticmethod
        def pipe(
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> Callable[[AsyncIterable[Any]], Stream[T]]:
            return lambda source: operator_instance(source, *args, **kwargs)  # type: ignore

        def __repr__(self) -> str:
            return f"{module}.{name}"

        def __str__(self) -> str:
            return f"{module}.{name}"

    # Customize raw method
    SourcesOperatorImplementation.raw.__signature__ = signature  # type: ignore[attr-defined]
    SourcesOperatorImplementation.raw.__qualname__ = name + ".raw"
    SourcesOperatorImplementation.raw.__module__ = module
    SourcesOperatorImplementation.raw.__doc__ = doc

    # Customize call method
    self_parameter = inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    new_parameters = [self_parameter] + parameters
    new_return_annotation = (
        return_annotation.replace("AsyncIterator", "Stream")
        if isinstance(return_annotation, str)
        else return_annotation
    )
    SourcesOperatorImplementation.__call__.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=new_parameters, return_annotation=new_return_annotation
    )
    SourcesOperatorImplementation.__call__.__qualname__ = name + ".__call__"
    SourcesOperatorImplementation.__call__.__name__ = "__call__"
    SourcesOperatorImplementation.__call__.__module__ = module
    SourcesOperatorImplementation.__call__.__doc__ = doc

    # Customize pipe method
    pipe_parameters = parameters
    pipe_return_annotation = f"Callable[[AsyncIterable[Any]], {new_return_annotation}]"
    SourcesOperatorImplementation.pipe.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=pipe_parameters, return_annotation=pipe_return_annotation
    )
    SourcesOperatorImplementation.pipe.__qualname__ = name + ".pipe"
    SourcesOperatorImplementation.pipe.__module__ = module
    SourcesOperatorImplementation.pipe.__doc__ = (
        f'Piped version of the "{name}" stream operator.'
    )
    if extra_doc:
        SourcesOperatorImplementation.pipe.__doc__ += "\n\n    " + extra_doc

    # Create operator singleton
    properly_named_class = type(
        name,
        (SourcesOperatorImplementation,),
        {
            "__qualname__": name,
            "__module__": module,
            "__doc__": doc,
        },
    )
    operator_instance = properly_named_class()
    return operator_instance
