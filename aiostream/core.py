"""Provide core objects for streaming."""

import functools
from collections import AsyncIterable, Awaitable

from .aiter_utils import _await, aitercontext, AsyncIteratorContext

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
        self._factory = factory

    def __aiter__(self):
        return streamcontext(self._factory())

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

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return Stream(lambda: func(*args, **kwargs))

        @functools.wraps(func)
        def pipe(*args, **kwargs):
            return lambda source: wrapper(
                *args[:position], source, *args[position:], **kwargs)

        wrapper.operator = True
        wrapper.pipe = pipe if pipable else None
        wrapper.raw = func
        return wrapper

    return decorator if func is None else decorator(func)
