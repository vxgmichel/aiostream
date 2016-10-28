
import asyncio
import builtins
import collections

from .. import stream
from ..core import operator, streamcontext

__all__ = ['take', 'take_last', 'skip', 'skip_last',
           'filter_index', 'slice', 'filter']


@operator(pipable=True)
async def take(source, n):
    source = stream.enumerate(source)
    async with streamcontext(source) as streamer:
        if n <= 0:
            return
        async for i, item in streamer:
            yield item
            if i >= n-1:
                break


@operator(pipable=True)
async def take_last(source, n):
    queue = collections.deque(maxlen=n if n > 0 else 0)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            queue.append(item)
        for item in queue:
            yield item


@operator(pipable=True)
async def skip(source, n):
    source = stream.enumerate(source)
    async with streamcontext(source) as streamer:
        async for i, item in streamer:
            if i >= n:
                yield item


@operator(pipable=True)
async def skip_last(source, n):
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
async def filter_index(source, func):
    source = stream.enumerate(source)
    async with streamcontext(source) as streamer:
        async for i, item in streamer:
            if func(i):
                yield item


@operator(pipable=True)
def slice(source, *args):
    s = builtins.slice(*args)
    start, stop, step = s.start or 0, s.stop, s.step or 1
    # Filter the first items
    if start < 0:
        source = take_last(source, abs(start))
    elif start > 0:
        source = skip(source, start)
    # Filter the last items
    if stop is not None:
        if stop >= 0 and start < 0:
            raise ValueError(
                "Positive stop and negative start is not supported")
        elif stop >= 0:
            source = take(source, stop - start)
        else:
            source = skip_last(source, abs(stop))
    # Filter step items
    if step is not None:
        if step > 1:
            source = filter_index(source, lambda i: i % step == 0)
        elif step < 0:
            raise ValueError("Negative step not supported")
    # Return
    return source


@operator(pipable=True, position=1)
async def filter(func, source):
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            if iscorofunc:
                if await func(item):
                    yield item
            elif func(item):
                yield item
