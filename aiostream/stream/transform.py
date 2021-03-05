"""Transformation operators."""

import asyncio
import itertools

from ..core import operator, streamcontext

from . import select
from . import create
from . import aggregate
from .combine import map, amap, smap

__all__ = ["map", "enumerate", "starmap", "cycle", "chunks"]

# map, amap and smap are also transform operators
map, amap, smap


@operator(pipable=True)
async def enumerate(source, start=0, step=1):
    """Generate ``(index, value)`` tuples from an asynchronous sequence.

    This index is computed using a starting point and an increment,
    respectively defaulting to ``0`` and ``1``.
    """
    count = itertools.count(start, step)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield next(count), item


@operator(pipable=True)
def starmap(source, func, ordered=True, task_limit=None):
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

        async def starfunc(args):
            return await func(*args)

    else:

        def starfunc(args):
            return func(*args)

    return map.raw(source, starfunc, ordered=ordered, task_limit=task_limit)


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


@operator(pipable=True)
async def chunks(source, n):
    """Generate chunks of size ``n`` from an asynchronous sequence.

    The chunks are lists, and the last chunk might contain less than ``n``
    elements.
    """
    async with streamcontext(source) as streamer:
        async for first in streamer:
            xs = select.take(create.preserve(streamer), n - 1)
            yield [first] + await aggregate.list(xs)
