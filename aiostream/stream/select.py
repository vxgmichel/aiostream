"""Selection operators."""
from __future__ import annotations

import asyncio
import builtins
import collections

from typing import Awaitable, Callable, TypeVar, AsyncIterable, AsyncIterator

from . import transform
from ..aiter_utils import aiter, anext
from ..core import streamcontext, pipable_operator

__all__ = [
    "take",
    "takelast",
    "skip",
    "skiplast",
    "getitem",
    "filter",
    "until",
    "dropwhile",
    "takewhile",
]

T = TypeVar("T")


@pipable_operator
async def take(source: AsyncIterable[T], n: int) -> AsyncIterator[T]:
    """Forward the first ``n`` elements from an asynchronous sequence.

    If ``n`` is negative, it simply terminates before iterating the source.
    """
    enumerated = transform.enumerate.raw(source)
    async with streamcontext(enumerated) as streamer:
        if n <= 0:
            return
        async for i, item in streamer:
            yield item
            if i >= n - 1:
                return


@pipable_operator
async def takelast(source: AsyncIterable[T], n: int) -> AsyncIterator[T]:
    """Forward the last ``n`` elements from an asynchronous sequence.

    If ``n`` is negative, it simply terminates after iterating the source.

    Note: it is required to reach the end of the source before the first
    element is generated.
    """
    queue: collections.deque[T] = collections.deque(maxlen=n if n > 0 else 0)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            queue.append(item)
        for item in queue:
            yield item


@pipable_operator
async def skip(source: AsyncIterable[T], n: int) -> AsyncIterator[T]:
    """Forward an asynchronous sequence, skipping the first ``n`` elements.

    If ``n`` is negative, no elements are skipped.
    """
    enumerated = transform.enumerate.raw(source)
    async with streamcontext(enumerated) as streamer:
        async for i, item in streamer:
            if i >= n:
                yield item


@pipable_operator
async def skiplast(source: AsyncIterable[T], n: int) -> AsyncIterator[T]:
    """Forward an asynchronous sequence, skipping the last ``n`` elements.

    If ``n`` is negative, no elements are skipped.

    Note: it is required to reach the ``n+1`` th element of the source
    before the first element is generated.
    """
    queue: collections.deque[T] = collections.deque(maxlen=n if n > 0 else 0)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            if n <= 0:
                yield item
                continue
            if len(queue) == n:
                yield queue[0]
            queue.append(item)


@pipable_operator
async def filterindex(
    source: AsyncIterable[T], func: Callable[[int], bool]
) -> AsyncIterator[T]:
    """Filter an asynchronous sequence using the index of the elements.

    The given function is synchronous, takes the index as an argument,
    and returns ``True`` if the corresponding should be forwarded,
    ``False`` otherwise.
    """
    enumerated = transform.enumerate.raw(source)
    async with streamcontext(enumerated) as streamer:
        async for i, item in streamer:
            if func(i):
                yield item


@pipable_operator
def slice(source: AsyncIterable[T], *args: int) -> AsyncIterator[T]:
    """Slice an asynchronous sequence.

    The arguments are the same as the builtin type slice.

    There are two limitations compare to regular slices:
    - Positive stop index with negative start index is not supported
    - Negative step is not supported
    """
    s = builtins.slice(*args)
    start, stop, step = s.start or 0, s.stop, s.step or 1
    aiterator = aiter(source)
    # Filter the first items
    if start < 0:
        aiterator = takelast.raw(aiterator, abs(start))
    elif start > 0:
        aiterator = skip.raw(aiterator, start)
    # Filter the last items
    if stop is not None:
        if stop >= 0 and start < 0:
            raise ValueError("Positive stop with negative start is not supported")
        elif stop >= 0:
            aiterator = take.raw(aiterator, stop - start)
        else:
            aiterator = skiplast.raw(aiterator, abs(stop))
    # Filter step items
    if step is not None:
        if step > 1:
            aiterator = filterindex.raw(aiterator, lambda i: i % step == 0)
        elif step < 0:
            raise ValueError("Negative step not supported")
    # Return
    return aiterator


@pipable_operator
async def item(source: AsyncIterable[T], index: int) -> AsyncIterator[T]:
    """Forward the ``n``th element of an asynchronous sequence.

    The index can be negative and works like regular indexing.
    If the index is out of range, and ``IndexError`` is raised.
    """
    # Prepare
    if index >= 0:
        source = skip.raw(source, index)
    else:
        source = takelast(source, abs(index))
    async with streamcontext(source) as streamer:
        # Get first item
        try:
            result = await anext(streamer)
        except StopAsyncIteration:
            raise IndexError("Index out of range")
        # Check length
        if index < 0:
            count = 1
            async for _ in streamer:
                count += 1
            if count != abs(index):
                raise IndexError("Index out of range")
        # Yield result
        yield result


@pipable_operator
def getitem(source: AsyncIterable[T], index: int | builtins.slice) -> AsyncIterator[T]:
    """Forward one or several items from an asynchronous sequence.

    The argument can either be a slice or an integer.
    See the slice and item operators for more information.
    """
    if isinstance(index, builtins.slice):
        return slice.raw(source, index.start, index.stop, index.step)
    if isinstance(index, int):
        return item.raw(source, index)
    raise TypeError("Not a valid index (int or slice)")


@pipable_operator
async def filter(
    source: AsyncIterable[T], func: Callable[[T], bool | Awaitable[bool]]
) -> AsyncIterator[T]:
    """Filter an asynchronous sequence using an arbitrary function.

    The function takes the item as an argument and returns ``True``
    if it should be forwarded, ``False`` otherwise.
    The function can either be synchronous or asynchronous.
    """
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result = func(item)
            if iscorofunc:
                assert isinstance(result, Awaitable)
                result = await result
            if result:
                yield item


@pipable_operator
async def until(
    source: AsyncIterable[T], func: Callable[[T], bool | Awaitable[bool]]
) -> AsyncIterator[T]:
    """Forward an asynchronous sequence until a condition is met.

    Contrary to the ``takewhile`` operator, the last tested element is included
    in the sequence.

    The given function takes the item as an argument and returns a boolean
    corresponding to the condition to meet. The function can either be
    synchronous or asynchronous.
    """
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result = func(item)
            if iscorofunc:
                assert isinstance(result, Awaitable)
                result = await result
            yield item
            if result:
                return


@pipable_operator
async def takewhile(
    source: AsyncIterable[T], func: Callable[[T], bool | Awaitable[bool]]
) -> AsyncIterator[T]:
    """Forward an asynchronous sequence while a condition is met.

    Contrary to the ``until`` operator, the last tested element is not included
    in the sequence.

    The given function takes the item as an argument and returns a boolean
    corresponding to the condition to meet. The function can either be
    synchronous or asynchronous.
    """
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result = func(item)
            if iscorofunc:
                assert isinstance(result, Awaitable)
                result = await result
            if not result:
                return
            yield item


@pipable_operator
async def dropwhile(
    source: AsyncIterable[T], func: Callable[[T], bool | Awaitable[bool]]
) -> AsyncIterator[T]:
    """Discard the elements from an asynchronous sequence
    while a condition is met.

    The given function takes the item as an argument and returns a boolean
    corresponding to the condition to meet. The function can either be
    synchronous or asynchronous.
    """
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result = func(item)
            if iscorofunc:
                assert isinstance(result, Awaitable)
                result = await result
            if not result:
                yield item
                break
        async for item in streamer:
            yield item
