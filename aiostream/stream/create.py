
import asyncio
import builtins
import itertools
from collections import Iterable, AsyncIterable

from ..core import operator
from ..stream import time

__all__ = ['from_iterable', 'from_async_iterable', 'iterate',
           'just', 'throw', 'empty', 'never', 'repeat',
           'range', 'count']


# Convert regular iterables

@operator
async def from_iterable(it):
    for item in it:
        yield item


@operator
def from_async_iterable(ait):
    return ait


@operator
def iterate(it):
    if isinstance(it, AsyncIterable):
        return from_async_iterable.raw(it)
    if isinstance(it, Iterable):
        return from_iterable.raw(it)
    raise TypeError("Not (async) iterable")


# Simple operators

@operator
async def just(value):
    yield value


@operator
async def throw(exc):
    if False:
        yield
    raise exc


@operator
async def empty():
    if False:
        yield


@operator
async def never():
    if False:
        yield
    future = asyncio.Future()
    await future


@operator
def repeat(value, times=None):
    args = () if times is None else (times,)
    it = itertools.repeat(value, *args)
    return from_iterable.raw(it)


# Counting operators

@operator
def range(*args, interval=0):
    stream = from_iterable.raw(builtins.range(*args))
    return time.space_out.raw(stream, interval) if interval else stream


@operator
def count(start=0, step=1, *, interval=0):
    stream = from_iterable.raw(itertools.count(start, step))
    return time.space_out.raw(stream, interval) if interval else stream
