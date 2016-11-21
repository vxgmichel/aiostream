"""Core objects for stream operators."""

import inspect
import functools
from collections import AsyncIterable, Awaitable

from .aiter_utils import AsyncIteratorContext
from .aiter_utils import _await, aitercontext, assert_async_iterable

__all__ = ['Stream', 'Streamer', 'StreamEmpty', 'operator', 'streamcontext']


# Exception

class StreamEmpty(Exception):
    """Exception raised when awaiting an empty stream."""
    pass


# Helpers

async def wait_stream(aiterable):
    """Wait for an asynchronous iterable to finish and return the last item.

    The iterable is executed within a safe stream context.
    A StreamEmpty exception is raised if the sequence is empty.
    """
    async with streamcontext(aiterable) as streamer:
        async for item in streamer:
            item
        try:
            return item
        except NameError:
            raise StreamEmpty()


# Core objects

class Stream(AsyncIterable, Awaitable):
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

    def __init__(self, factory):
        """Initialize the stream with an asynchronous iterable factory.

        The factory is a callable and takes no argument.
        The factory return value is an asynchronous iterable.
        """
        aiter = factory()
        assert_async_iterable(aiter)
        self._generator = self._make_generator(aiter, factory)

    def _make_generator(self, first, factory):
        """Generate asynchronous iterables when required.

        The first iterable is created beforehand for extra checking.
        """
        yield first
        del first
        while True:
            yield factory()

    def __aiter__(self):
        """Asynchronous iteration protocol.

        Return a streamer context for safe iteration.
        """
        return streamcontext(next(self._generator))

    def __await__(self):
        """Await protocol.

        Safely iterate and return the last element.
        """
        return _await(wait_stream(self))

    def __or__(self, func):
        """Pipe protocol.

        Allow to pipe stream operators.
        """
        return func(self)

    def __add__(self, value):
        """Addition protocol.

        Concatenate with a given asynchronous sequence.
        """
        from .stream import chain
        return chain(self, value)

    def __getitem__(self, value):
        """Get item protocol.

        Accept index or slice to extract the corresponding item(s)
        """
        from .stream import getitem
        return getitem(self, value)

    def stream(self):
        """Return a streamer context for safe iteration.

        Example::

            xs = stream.count()
            async with xs.stream() as streamer:
                async for item in streamer:
                    <block>

        """
        return self.__aiter__()


class Streamer(AsyncIteratorContext, Stream):
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


def streamcontext(aiterable):
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
    return aitercontext(aiterable, cls=Streamer)


# Operator decorator

def operator(func=None, *, pipable=False):
    """Create a stream operator from an asynchronous generator
    (or any function returning an asynchronous iterable).

    Decorator usage::

        @operator
        async def random(offset=0., width=1.):
            while True:
                yield offset + width * random.random()

    Decorator usage for pipable operators::

        @operator(pipable=True)
        async def multiply(source, factor):
            async with streamcontext(source) as streamer:
                 async for item in streamer:
                     yield factor * item

    In the case of pipable operators, the first argument is expected
    to be the asynchronous iteratable used for piping.

    The return value is a dynamically created class.
    It has the same name, module and doc as the original function.

    A new stream is created by simply instanciating the operator::

        xs = random()
        ys = multiply(xs, 2)

    The original function is called at instanciation to check that
    signature match. In the case of pipable operators, the source is
    also checked for asynchronous iteration.

    The operator also have a pipe class method that can be used along
    with the piping synthax::

        xs = random()
        ys = xs | multiply.pipe(2)

    This is strictly equivalent to the previous example.

    Other methods are available:

      - `original`: the original function as a static method
      - `raw`: same as original but add extra checking

    The raw method is useful to create new operators from existing ones::

        @operator(pipable=True)
        def double(source):
            return multiply.raw(source, 2)
    """

    def decorator(func):
        """Inner decorator for stream operator."""

        # Gather data
        bases = (Stream,)
        name = func.__name__
        module = func.__module__
        extra_doc = func.__doc__
        doc = extra_doc or f'Regular {name} stream operator.'

        # Extract signature
        signature = inspect.signature(func)
        parameters = list(signature.parameters.values())
        self_parameter = inspect.Parameter(
            'self', inspect.Parameter.POSITIONAL_OR_KEYWORD)
        cls_parameter = inspect.Parameter(
            'cls', inspect.Parameter.POSITIONAL_OR_KEYWORD)

        # wrapped static method
        original = func
        original.__qualname__ = name + '.original'

        # Raw static method
        raw = func
        raw.__qualname__ = name + '.raw'

        # Init method
        def init(self, *args, **kwargs):
            if pipable and args:
                assert_async_iterable(args[0])
            factory = functools.partial(self.raw, *args, **kwargs)
            return Stream.__init__(self, factory)

        # Customize init signature
        new_parameters = [self_parameter] + parameters
        init.__signature__ = signature.replace(parameters=new_parameters)

        # Customize init method
        init.__qualname__ = name + '.__init__'
        init.__name__ = '__init__'
        init.__module__ = module
        init.__doc__ = f'Initialize the {name} stream.'

        if pipable:

            # Raw static method
            def raw(*args, **kwargs):
                if args:
                    assert_async_iterable(args[0])
                return func(*args, **kwargs)

            # Custonize raw method
            raw.__signature__ = signature
            raw.__qualname__ = name + '.raw'
            raw.__module__ = module
            raw.__doc__ = doc

            # Pipe class method
            def pipe(cls, *args, **kwargs):
                return lambda source: cls(source, *args, **kwargs)

            # Customize pipe signature
            if parameters and parameters[0].kind in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD):
                new_parameters = [cls_parameter] + parameters[1:]
            else:
                new_parameters = [cls_parameter] + parameters
            pipe.__signature__ = signature.replace(parameters=new_parameters)

            # Customize pipe method
            pipe.__qualname__ = name + '.pipe'
            pipe.__module__ = module
            pipe.__doc__ = f'Pipable "{name}" stream operator.'
            if extra_doc:
                pipe.__doc__ += "\n\n    " + extra_doc

        # Gather attributes
        attrs = {
            '__init__': init,
            '__module__': module,
            '__doc__': doc,
            'raw': staticmethod(raw),
            'original': staticmethod(original),
            'pipe': classmethod(pipe) if pipable else None}

        # Create operator class
        return type(name, bases, attrs)

    return decorator if func is None else decorator(func)
