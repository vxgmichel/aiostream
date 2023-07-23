"""Transformation operators."""

from __future__ import annotations

import asyncio
import itertools
from typing import (
    Protocol,
    TypeVar,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    cast,
)

from ..core import streamcontext, pipable_operator

from . import select
from . import create
from . import aggregate
from .combine import map, amap, smap

__all__ = ["map", "enumerate", "starmap", "cycle", "chunks"]

# map, amap and smap are also transform operators
map, amap, smap

T = TypeVar("T")
U = TypeVar("U")


@pipable_operator
async def enumerate(
    source: AsyncIterable[T], start: int = 0, step: int = 1
) -> AsyncIterator[tuple[int, T]]:
    """Generate ``(index, value)`` tuples from an asynchronous sequence.

    This index is computed using a starting point and an increment,
    respectively defaulting to ``0`` and ``1``.
    """
    count = itertools.count(start, step)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield next(count), item


X = TypeVar("X", contravariant=True)
Y = TypeVar("Y", covariant=True)


class AsyncStarmapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Awaitable[Y]:
        ...


class SyncStarmapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Y:
        ...


@pipable_operator
def starmap(
    source: AsyncIterable[tuple[T, ...]],
    func: SyncStarmapCallable[T, U] | AsyncStarmapCallable[T, U],
    ordered: bool = True,
    task_limit: int | None = None,
) -> AsyncIterator[U]:
    """Apply a given function to the unpacked elements of
    an asynchronous sequence.

    Each element is unpacked before applying the function.
    The given function can either be synchronous or asynchronous.

    The results can either be returned in or out of order, depending on
    the corresponding ``ordered`` argument. This argument is ignored if
    the provided function is synchronous.

    The coroutines run concurrently but their amount can be limited using
    the ``task_limit`` argument. A value of ``1`` will cause the coroutines
    to run sequentially. This argument is ignored if the provided function
    is synchronous.
    """
    if asyncio.iscoroutinefunction(func):
        async_func = cast("AsyncStarmapCallable[T, U]", func)

        async def astarfunc(args: tuple[T, ...], *_: object) -> U:
            awaitable = async_func(*args)
            return await awaitable

        return amap.raw(source, astarfunc, ordered=ordered, task_limit=task_limit)

    else:
        sync_func = cast("SyncStarmapCallable[T, U]", func)

        def starfunc(args: tuple[T, ...], *_: object) -> U:
            return sync_func(*args)

        return smap.raw(source, starfunc)


@pipable_operator
async def cycle(source: AsyncIterable[T]) -> AsyncIterator[T]:
    """Iterate indefinitely over an asynchronous sequence.

    Note: it does not perform any buffering, but re-iterate over
    the same given sequence instead. If the sequence is not
    re-iterable, the generator might end up looping indefinitely
    without yielding any item.
    """
    while True:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield item
            # Prevent blocking while loop if the stream is empty
            await asyncio.sleep(0)


@pipable_operator
async def chunks(source: AsyncIterable[T], n: int) -> AsyncIterator[list[T]]:
    """Generate chunks of size ``n`` from an asynchronous sequence.

    The chunks are lists, and the last chunk might contain less than ``n``
    elements.
    """
    async with streamcontext(source) as streamer:
        async for first in streamer:
            xs = select.take(create.preserve(streamer), n - 1)
            yield [first] + await aggregate.list(xs)
