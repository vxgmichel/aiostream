"""Non-pipable creation operators."""

import asyncio
import builtins
import itertools
import collections

from ..stream import time
from ..core import operator, streamcontext
from ..aiter_utils import is_async_iterable

__all__ = ['iterate', 'preserve',
           'just', 'throw', 'empty', 'never', 'repeat',
           'range', 'count']


# Convert regular iterables

@operator
async def from_iterable(it):
    """Generate values from a regular iterable."""
    for item in it:
        yield item


@operator
def from_async_iterable(ait):
    """Generate values from an asynchronous iterable.

    Note: the corresponding iterator will be explicitely closed
    when leaving the context manager."""
    return streamcontext(ait)


@operator
def iterate(it):
    """Generate values from a sychronous or asynchronous iterable."""
    if is_async_iterable(it):
        return from_async_iterable.raw(it)
    if isinstance(it, collections.Iterable):
        return from_iterable.raw(it)
    raise TypeError(
        f"{type(it).__name__!r} object is not (async) iterable")


@operator
async def preserve(ait):
    """Generate values from an asynchronous iterable without
    explicitly closing the corresponding iterator."""
    async for item in ait:
        yield item


# Simple operators

@operator
async def just(value):
    """Generate a single value."""
    yield value


@operator
async def throw(exc):
    """Throw an exception without generating any value."""
    if False:
        yield
    raise exc


@operator
async def empty():
    """Terminate without generating any value."""
    if False:
        yield


@operator
async def never():
    """Hang forever without generating any value."""
    if False:
        yield
    future = asyncio.Future()
    try:
        await future
    finally:
        future.cancel()


@operator
def repeat(value, times=None, *, interval=0):
    """Generate the same value a given number of times.

    If times is None, the value is repeated indefinitely.
    An optional interval can be given to space the values out.
    """
    args = () if times is None else (times,)
    it = itertools.repeat(value, *args)
    agen = from_iterable.raw(it)
    return time.spaceout.raw(agen, interval) if interval else agen


# Counting operators

@operator
def range(*args, interval=0):
    """Generate a given range of numbers.

    It supports the same arguments as the builtin function.
    An optional interval can be given to space the values out.
    """
    agen = from_iterable.raw(builtins.range(*args))
    return time.spaceout.raw(agen, interval) if interval else agen


@operator
def count(start=0, step=1, *, interval=0):
    """Generate consecutive numbers indefinitely.

    Optional starting point and increment can be defined,
    respectively defaulting to 0 and 1.

    An optional interval can be given to space the values out.
    """
    agen = from_iterable.raw(itertools.count(start, step))
    return time.spaceout.raw(agen, interval) if interval else agen
