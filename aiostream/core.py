"""Provide core objects for streaming."""

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
    """Wait for a stream to finish and return the last item."""
    async with streamcontext(aiterable) as streamer:
        async for item in streamer:
            item
        try:
            return item
        except NameError:
            raise StreamEmpty()


# Core objects

class Stream(AsyncIterable, Awaitable):
    """Enhanced asynchronous iterable."""

    def __init__(self, factory):
        aiter = factory()
        assert_async_iterable(aiter)
        self._generator = self._make_generator(aiter, factory)

    def _make_generator(self, first, factory):
        yield first
        del first
        while True:
            yield factory()

    def __aiter__(self):
        return streamcontext(next(self._generator))

    def __await__(self):
        return _await(wait_stream(self))

    def __or__(self, func):
        return func(self)

    def __add__(self, value):
        from .stream import chain
        return chain(self, value)

    def __getitem__(self, value):
        from .stream import get_item
        return get_item(self, value)

    stream = __aiter__


class Streamer(AsyncIteratorContext, Stream):
    """Enhanced asynchronous iterator."""
    pass


streamcontext = functools.partial(aitercontext, cls=Streamer)


# Operator decorator

def operator(func=None, *, pipable=False):
    """Return a decorator to wrap function into a stream operator."""

    def decorator(func):
        # Gather data
        raw = func
        bases = (Stream,)
        name = func.__name__
        module = func.__module__
        extra_doc = func.__doc__
        doc = f'Regular "{name}" stream operator.'
        if extra_doc:
            doc += '\n\n    ' + extra_doc

        # Extract signature
        signature = inspect.signature(func)
        parameters = list(signature.parameters.values())
        self_parameter = inspect.Parameter(
            'self', inspect.Parameter.POSITIONAL_OR_KEYWORD)
        cls_parameter = inspect.Parameter(
            'cls', inspect.Parameter.POSITIONAL_OR_KEYWORD)

        # Raw method

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
        init.__doc__ = f'Initialize the "{name}" stream.'

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
            'pipe': classmethod(pipe) if pipable else None}

        # Create operator class
        return type(name, bases, attrs)

    return decorator if func is None else decorator(func)
