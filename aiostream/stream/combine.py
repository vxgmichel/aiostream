"""Combination operators."""
from __future__ import annotations

import asyncio
import builtins

from typing import (
    Awaitable,
    Protocol,
    TypeVar,
    AsyncIterable,
    AsyncIterator,
    Callable,
    cast,
)
from typing_extensions import ParamSpec

from ..aiter_utils import AsyncExitStack, anext
from ..core import streamcontext, pipable_operator

from . import create
from . import select
from . import advanced
from . import aggregate

__all__ = ["chain", "zip", "map", "merge", "ziplatest", "amap", "smap"]

T = TypeVar("T")
U = TypeVar("U")
K = TypeVar("K")
P = ParamSpec("P")


@pipable_operator
async def chain(
    source: AsyncIterable[T], *more_sources: AsyncIterable[T]
) -> AsyncIterator[T]:
    """Chain asynchronous sequences together, in the order they are given.

    Note: the sequences are not iterated until it is required,
    so if the operation is interrupted, the remaining sequences
    will be left untouched.
    """
    sources = source, *more_sources
    for source in sources:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield item


@pipable_operator
async def zip(
    source: AsyncIterable[T], *more_sources: AsyncIterable[T]
) -> AsyncIterator[tuple[T, ...]]:
    """Combine and forward the elements of several asynchronous sequences.

    Each generated value is a tuple of elements, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted.

    Note: the different sequences are awaited in parrallel, so that their
    waiting times don't add up.
    """
    sources = source, *more_sources

    # One sources
    if len(sources) == 1:
        (source,) = sources
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield (item,)
        return

    # N sources
    async with AsyncExitStack() as stack:
        # Handle resources
        streamers = [
            await stack.enter_async_context(streamcontext(source)) for source in sources
        ]
        # Loop over items
        while True:
            try:
                coros = builtins.map(anext, streamers)
                items = await asyncio.gather(*coros)
            except StopAsyncIteration:
                break
            else:
                yield tuple(items)


X = TypeVar("X", contravariant=True)
Y = TypeVar("Y", covariant=True)


class SmapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Y:
        ...


class AmapCallable(Protocol[X, Y]):
    async def __call__(self, arg: X, /, *args: X) -> Y:
        ...


class MapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Awaitable[Y] | Y:
        ...


@pipable_operator
async def smap(
    source: AsyncIterable[T],
    func: SmapCallable[T, U],
    *more_sources: AsyncIterable[T],
) -> AsyncIterator[U]:
    """Apply a given function to the elements of one or several
    asynchronous sequences.

    Each element is used as a positional argument, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted. The function is treated synchronously.

    Note: if more than one sequence is provided, they're awaited concurrently
    so that their waiting times don't add up.
    """
    stream = zip(source, *more_sources)
    async with streamcontext(stream) as streamer:
        async for item in streamer:
            yield func(*item)


@pipable_operator
def amap(
    source: AsyncIterable[T],
    corofn: AmapCallable[T, U],
    *more_sources: AsyncIterable[T],
    ordered: bool = True,
    task_limit: int | None = None,
) -> AsyncIterator[U]:
    """Apply a given coroutine function to the elements of one or several
    asynchronous sequences.

    Each element is used as a positional argument, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted.

    The results can either be returned in or out of order, depending on
    the corresponding ``ordered`` argument.

    The coroutines run concurrently but their amount can be limited using
    the ``task_limit`` argument. A value of ``1`` will cause the coroutines
    to run sequentially.

    If more than one sequence is provided, they're also awaited concurrently,
    so that their waiting times don't add up.
    """

    async def func(arg: T, *args: T) -> AsyncIterable[U]:
        yield await corofn(arg, *args)

    if ordered:
        return advanced.concatmap.raw(
            source, func, *more_sources, task_limit=task_limit
        )
    return advanced.flatmap.raw(source, func, *more_sources, task_limit=task_limit)


@pipable_operator
def map(
    source: AsyncIterable[T],
    func: MapCallable[T, U],
    *more_sources: AsyncIterable[T],
    ordered: bool = True,
    task_limit: int | None = None,
) -> AsyncIterator[U]:
    """Apply a given function to the elements of one or several
    asynchronous sequences.

    Each element is used as a positional argument, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted. The function can either be synchronous or
    asynchronous (coroutine function).

    The results can either be returned in or out of order, depending on
    the corresponding ``ordered`` argument. This argument is ignored if the
    provided function is synchronous.

    The coroutines run concurrently but their amount can be limited using
    the ``task_limit`` argument. A value of ``1`` will cause the coroutines
    to run sequentially. This argument is ignored if the provided function
    is synchronous.

    If more than one sequence is provided, they're also awaited concurrently,
    so that their waiting times don't add up.

    It might happen that the provided function returns a coroutine but is not
    a coroutine function per se. In this case, one can wrap the function with
    ``aiostream.async_`` in order to force ``map`` to await the resulting
    coroutine. The following example illustrates the use ``async_`` with a
    lambda function::

        from aiostream import stream, async_
        ...
        ys = stream.map(xs, async_(lambda ms: asyncio.sleep(ms / 1000)))
    """
    if asyncio.iscoroutinefunction(func):
        return amap.raw(
            source, func, *more_sources, ordered=ordered, task_limit=task_limit
        )
    sync_func = cast("SmapCallable[T, U]", func)
    return smap.raw(source, sync_func, *more_sources)


@pipable_operator
def merge(
    source: AsyncIterable[T], *more_sources: AsyncIterable[T]
) -> AsyncIterator[T]:
    """Merge several asynchronous sequences together.

    All the sequences are iterated simultaneously and their elements
    are forwarded as soon as they're available. The generation continues
    until all the sequences are exhausted.
    """
    sources = [source, *more_sources]
    source_stream: AsyncIterable[AsyncIterable[T]] = create.iterate.raw(sources)
    return advanced.flatten.raw(source_stream)


@pipable_operator
def ziplatest(
    source: AsyncIterable[T],
    *more_sources: AsyncIterable[T],
    partial: bool = True,
    default: T | None = None,
) -> AsyncIterator[tuple[T | None, ...]]:
    """Combine several asynchronous sequences together, producing a tuple with
    the lastest element of each sequence whenever a new element is received.

    The value to use when a sequence has not procuded any element yet is given
    by the ``default`` argument (defaulting to ``None``).

    The producing of partial results can be disabled by setting the optional
    argument ``partial`` to ``False``.

    All the sequences are iterated simultaneously and their elements
    are forwarded as soon as they're available. The generation continues
    until all the sequences are exhausted.
    """
    sources = source, *more_sources
    n = len(sources)

    # Custom getter
    def getter(dct: dict[int, T]) -> Callable[[int], T | None]:
        return lambda key: dct.get(key, default)

    # Add source index to the items
    def make_func(i: int) -> SmapCallable[T, dict[int, T]]:
        def func(x: T, *_: object) -> dict[int, T]:
            return {i: x}

        return func

    new_sources = [smap.raw(source, make_func(i)) for i, source in enumerate(sources)]

    # Merge the sources
    merged = merge.raw(*new_sources)

    # Accumulate the current state in a dict
    accumulated = aggregate.accumulate.raw(merged, lambda x, e: {**x, **e})

    # Filter partial result
    filtered = (
        accumulated
        if partial
        else select.filter.raw(accumulated, lambda x: len(x) == n)
    )

    # Convert the state dict to a tuple
    def dict_to_tuple(x: dict[int, T], *_: object) -> tuple[T | None, ...]:
        return tuple(builtins.map(getter(x), range(n)))

    return smap.raw(filtered, dict_to_tuple)
