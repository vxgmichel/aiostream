
import asyncio
import builtins
import itertools
from collections import Iterable, AsyncIterable

from ..core import operator
from ..utils import aiter
from ..stream import time


# Convert regular iterables

@operator
async def from_iterable(it):
    for item in it:
        yield item


@operator
def from_aiterable(ait):
    return ait


@operator
def iterate(it):
    if isinstance(it, AsyncIterable):
        return from_aiterable(it)
    if instance(it, Iterable):
        return from_iterable(it)
    raise TypeError("Not (async) iterable")


# Simple operators

@operator
async def just(value):
    yield value


@operator
async def throw(exc):
    raise exc


@operator
async def empty():
    if False:
        yield


@operator
async def never():
    future = asyncio.Future()
    await future


# Counting operators

@operator
def range(*args, delay=0):
    stream = from_iterable(builtins.range(*args))
    return time.space_out(stream, delay) if delay else stream


@operator
def count(start=0, step=1, *, delay=0):
    stream = from_iterable(itertools.count(start, step))
    return time.space_out(stream, delay) if delay else stream
