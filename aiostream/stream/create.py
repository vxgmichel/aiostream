"""Non-pipable creation operators."""
from __future__ import annotations

import sys
import asyncio
import inspect
import builtins
import itertools

from typing import (
    AsyncIterable,
    Awaitable,
    Iterable,
    Protocol,
    TypeVar,
    AsyncIterator,
    cast,
)
from typing_extensions import ParamSpec

from ..stream import time
from ..core import operator, streamcontext

__all__ = [
    "iterate",
    "preserve",
    "just",
    "call",
    "throw",
    "empty",
    "never",
    "repeat",
    "range",
    "count",
]

T = TypeVar("T")
P = ParamSpec("P")

# Hack for python 3.8 compatibility
if sys.version_info < (3, 9):
    P = TypeVar("P")

# Convert regular iterables


@operator
async def from_iterable(it: Iterable[T]) -> AsyncIterator[T]:
    """Generate values from a regular iterable."""
    for item in it:
        await asyncio.sleep(0)
        yield item


@operator
def from_async_iterable(ait: AsyncIterable[T]) -> AsyncIterator[T]:
    """Generate values from an asynchronous iterable.

    Note: the corresponding iterator will be explicitely closed
    when leaving the context manager."""
    return streamcontext(ait)


@operator
def iterate(it: AsyncIterable[T] | Iterable[T]) -> AsyncIterator[T]:
    """Generate values from a sychronous or asynchronous iterable."""
    if isinstance(it, AsyncIterable):
        return from_async_iterable.raw(it)
    if isinstance(it, Iterable):
        return from_iterable.raw(it)
    raise TypeError(f"{type(it).__name__!r} object is not (async) iterable")


@operator
async def preserve(ait: AsyncIterable[T]) -> AsyncIterator[T]:
    """Generate values from an asynchronous iterable without
    explicitly closing the corresponding iterator."""
    async for item in ait:
        yield item


# Simple operators


@operator
async def just(value: T) -> AsyncIterator[T]:
    """Await if possible, and generate a single value."""
    if inspect.isawaitable(value):
        yield await value
    else:
        yield value


Y = TypeVar("Y", covariant=True)


class SyncCallable(Protocol[P, Y]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Y:
        ...


class AsyncCallable(Protocol[P, Y]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[Y]:
        ...


@operator
async def call(
    func: SyncCallable[P, T] | AsyncCallable[P, T], *args: P.args, **kwargs: P.kwargs
) -> AsyncIterator[T]:
    """Call the given function and generate a single value.

    Await if the provided function is asynchronous.
    """
    if asyncio.iscoroutinefunction(func):
        async_func = cast("AsyncCallable[P, T]", func)
        yield await async_func(*args, **kwargs)
    else:
        sync_func = cast("SyncCallable[P, T]", func)
        yield sync_func(*args, **kwargs)


@operator
async def throw(exc: Exception) -> AsyncIterator[None]:
    """Throw an exception without generating any value."""
    if False:
        yield
    raise exc


@operator
async def empty() -> AsyncIterator[None]:
    """Terminate without generating any value."""
    if False:
        yield


@operator
async def never() -> AsyncIterator[None]:
    """Hang forever without generating any value."""
    if False:
        yield
    future: asyncio.Future[None] = asyncio.Future()
    try:
        await future
    finally:
        future.cancel()


@operator
def repeat(
    value: T, times: int | None = None, *, interval: float = 0.0
) -> AsyncIterator[T]:
    """Generate the same value a given number of times.

    If ``times`` is ``None``, the value is repeated indefinitely.
    An optional interval can be given to space the values out.
    """
    args = () if times is None else (times,)
    it = itertools.repeat(value, *args)
    agen = from_iterable.raw(it)
    return time.spaceout.raw(agen, interval) if interval else agen


# Counting operators


@operator
def range(*args: int, interval: float = 0.0) -> AsyncIterator[int]:
    """Generate a given range of numbers.

    It supports the same arguments as the builtin function.
    An optional interval can be given to space the values out.
    """
    agen = from_iterable.raw(builtins.range(*args))
    return time.spaceout.raw(agen, interval) if interval else agen


@operator
def count(
    start: int = 0, step: int = 1, *, interval: float = 0.0
) -> AsyncIterator[int]:
    """Generate consecutive numbers indefinitely.

    Optional starting point and increment can be defined,
    respectively defaulting to ``0`` and ``1``.

    An optional interval can be given to space the values out.
    """
    agen = from_iterable.raw(itertools.count(start, step))
    return time.spaceout.raw(agen, interval) if interval else agen
