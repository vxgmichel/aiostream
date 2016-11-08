"""Transformation operators."""

import asyncio
import itertools

from .combine import map
from ..core import operator, streamcontext

__all__ = ['map', 'enumerate', 'starmap', 'cycle']


@operator(pipable=True)
async def enumerate(source, start=0, step=1):
    """Generate (index, value) tuples from an asynchronous sequence.

    This index is computed using a starting point and an increment,
    respectively defaulting to 0 and 1.
    """
    count = itertools.count(start, step)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield next(count), item


@operator(pipable=True)
def starmap(source, func):
    """Apply a given function to the unpacked elements of
    an asynchronous sequence.

    Each element is unpacked before applying the function.
    The given function can either be synchronous or asynchronous.
    """
    if asyncio.iscoroutinefunction(func):
        async def starfunc(args):
            return await func(*args)
    else:
        def starfunc(args):
            return func(*args)
    return map.raw(source, starfunc)


@operator(pipable=True)
async def cycle(source):
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
