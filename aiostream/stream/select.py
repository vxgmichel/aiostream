"""Selection operators."""

import asyncio
import builtins
import collections

from . import transform
from ..aiter_utils import anext
from ..core import operator, streamcontext

__all__ = ['take', 'takelast', 'skip', 'skiplast',
           'getitem', 'filter', 'dropwhile', 'takewhile']


@operator(pipable=True)
async def take(source, n):
    """Forward the first n elements from an asynchronous sequence.

    If n is negative, it simply terminates before iterating the source.
    """
    source = transform.enumerate.raw(source)
    async with streamcontext(source) as streamer:
        if n <= 0:
            return
        async for i, item in streamer:
            yield item
            if i >= n-1:
                return


@operator(pipable=True)
async def takelast(source, n):
    """Forward the last n elements from an asynchronous sequence.

    If n is negative, it simply terminates after iterating the source.

    Note: it is required to reach the end of the source before the first
    element is generated.
    """
    queue = collections.deque(maxlen=n if n > 0 else 0)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            queue.append(item)
        for item in queue:
            yield item


@operator(pipable=True)
async def skip(source, n):
    """Forward an asynchronous sequence, skipping the first n elements.

    If n is negative, no elements are skipped.
    """
    source = transform.enumerate.raw(source)
    async with streamcontext(source) as streamer:
        async for i, item in streamer:
            if i >= n:
                yield item


@operator(pipable=True)
async def skiplast(source, n):
    """Forward an asynchronous sequence, skipping the last n elements.

    If n is negative, no elements are skipped.

    Note: it is required to reach the (n+1)th element of the source
    before the first element is generated.
    """
    queue = collections.deque(maxlen=n if n > 0 else 0)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            if n <= 0:
                yield item
                continue
            if len(queue) == n:
                yield queue[0]
            queue.append(item)


@operator(pipable=True)
async def filterindex(source, func):
    """Filter an asynchronous sequence using the index of the elements.

    The given function is synchronous, takes the index as an argument,
    and returns True if the corresponding should be forwarded,
    False otherwise.
    """
    source = transform.enumerate.raw(source)
    async with streamcontext(source) as streamer:
        async for i, item in streamer:
            if func(i):
                yield item


@operator(pipable=True)
def slice(source, *args):
    """Slice an asynchronous sequence.

    The arguments are the same as the builtin type slice.

    There two limitations compare to regular slices:
    - Positive stop index + negative start index is not supported
    - Negative step is not supported
    """
    s = builtins.slice(*args)
    start, stop, step = s.start or 0, s.stop, s.step or 1
    # Filter the first items
    if start < 0:
        source = takelast.raw(source, abs(start))
    elif start > 0:
        source = skip.raw(source, start)
    # Filter the last items
    if stop is not None:
        if stop >= 0 and start < 0:
            raise ValueError(
                "Positive stop + negative start is not supported")
        elif stop >= 0:
            source = take.raw(source, stop - start)
        else:
            source = skiplast.raw(source, abs(stop))
    # Filter step items
    if step is not None:
        if step > 1:
            source = filterindex.raw(source, lambda i: i % step == 0)
        elif step < 0:
            raise ValueError("Negative step not supported")
    # Return
    return source


@operator(pipable=True)
async def item(source, index):
    """Forward the nth element of an asynchronous sequence.

    The index can be negative and works like regular indexing.
    If the index is out of range, and IndexError is raised.
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


@operator(pipable=True)
def getitem(source, index):
    """Forward one or several items from an asynchronous sequence.

    The argument can either be a slice or an integer.
    See the slice and item operators for more information.
    """
    if isinstance(index, builtins.slice):
        return slice.raw(source, index.start, index.stop, index.step)
    if isinstance(index, int):
        return item.raw(source, index)
    raise TypeError("Not a valid index (int or slice)")


@operator(pipable=True)
async def filter(source, func):
    """Filter an asynchronous sequence using an arbitrary function.

    The function takes the item as an argument and returns True
    if it should be forwarded, False otherwise.
    The function can either be synchronous or asynchronous.
    """
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result = func(item)
            if iscorofunc:
                result = await result
            if result:
                yield item


@operator(pipable=True)
async def takewhile(source, func):
    """Forward an asynchronous sequence while a condition is met.

    The given function takes the item as an argument and returns a boolean
    corresponding to the condition to meet. The function can either be
    synchronous or asynchronous.
    """
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result = func(item)
            if iscorofunc:
                result = await result
            if not result:
                return
            yield item


@operator(pipable=True)
async def dropwhile(source, func):
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
                result = await result
            if not result:
                yield item
                break
        async for item in streamer:
            yield item
