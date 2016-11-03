"""Provide core objects for streaming."""

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

def operator(func=None, *, pipable=False, position=0):
    """Return a decorator to wrap function into a stream operator."""

    def decorator(func):

        def __init__(self, *args, **kwargs):
            return Stream.__init__(self, lambda: func(*args, **kwargs))

        @classmethod
        def pipe(cls, *args, **kwargs):
            return lambda source: cls(
                *args[:position], source, *args[position:], **kwargs)
        pipe.__doc__ = func.__doc__

        attrs = {
            '__init__': __init__,
            '__module__': func.__module__,
            '__doc__': func.__doc__,
            'operator': True,
            'pipe': pipe if pipable else None,
            'raw': staticmethod(func)}
        return type(func.__name__, (Stream,), attrs)

    return decorator if func is None else decorator(func)
