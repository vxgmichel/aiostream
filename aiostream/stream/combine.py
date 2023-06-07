"""Combination operators."""
from __future__ import annotations

import asyncio
import builtins

from typing import Awaitable, TypeVar, AsyncIterable, AsyncIterator, Callable
from typing_extensions import ParamSpec

from ..aiter_utils import AsyncExitStack, anext
from ..core import operator, streamcontext

from . import create
from . import select
from . import advanced
from . import aggregate

__all__ = ["chain", "zip", "map", "merge", "ziplatest"]

T = TypeVar("T")
U = TypeVar("U")
K = TypeVar("K")
P = ParamSpec("P")


@operator(pipable=True)
async def chain(*sources: AsyncIterable[T]) -> AsyncIterator[T]:
    """Chain asynchronous sequences together, in the order they are given.

    Note: the sequences are not iterated until it is required,
    so if the operation is interrupted, the remaining sequences
    will be left untouched.
    """
    for source in sources:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield item


@operator(pipable=True)
async def zip(*sources: AsyncIterable[T]) -> AsyncIterator[tuple[T, ...]]:
    """Combine and forward the elements of several asynchronous sequences.

    Each generated value is a tuple of elements, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted.

    Note: the different sequences are awaited in parrallel, so that their
    waiting times don't add up.
    """
    # Zero sources
    if len(sources) == 0:
        return

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


@operator(pipable=True)
async def smap(
    source: AsyncIterable[T], func: Callable[..., U], *more_sources: AsyncIterable[T]
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


@operator(pipable=True)
def amap(
    source: AsyncIterable[T],
    corofn: Callable[P, Awaitable[U]],
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

    def func(*args: P.args, **kwargs: P.kwargs) -> AsyncIterable[U]:
        return create.call(corofn, *args, **kwargs)  # type: ignore

    if ordered:
        return advanced.concatmap.raw(
            source, func, *more_sources, task_limit=task_limit
        )
    return advanced.flatmap.raw(source, func, *more_sources, task_limit=task_limit)


@operator(pipable=True)
def map(
    source: AsyncIterable[T],
    func: Callable[P, Awaitable[U] | U],
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
    return smap.raw(source, func, *more_sources)  # type: ignore


@operator(pipable=True)
def merge(*sources: AsyncIterable[T]) -> AsyncIterator[T]:
    """Merge several asynchronous sequences together.

    All the sequences are iterated simultaneously and their elements
    are forwarded as soon as they're available. The generation continues
    until all the sequences are exhausted.
    """
    return advanced.flatten.raw(create.iterate.raw(sources))


@operator(pipable=True)
def ziplatest(
    *sources: AsyncIterable[T], partial: bool = True, default: T | None = None
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
    n = len(sources)

    # Custom getter
    def getter(dct: dict[int, T]) -> Callable[[int], T | None]:
        return lambda key: dct.get(key, default)

    # Add source index to the items
    new_sources = [
        smap.raw(source, lambda x, i=i: {i: x}) for i, source in enumerate(sources)
    ]

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
    return smap.raw(filtered, lambda x: tuple(builtins.map(getter(x), range(n))))
