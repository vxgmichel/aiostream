"""Combination operators."""

import asyncio
import builtins

from ..aiter_utils import anext
from ..context_utils import AsyncExitStack
from ..core import operator, streamcontext

__all__ = ['chain', 'zip', 'map', 'merge']


@operator(pipable=True)
async def chain(*sources):
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
async def zip(*sources):
    """Combine and forward the elements of several asynchronous sequences.

    Each generated value is a tuple of elements, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted.

    Note: the different sequences are awaited in parrallel, so that their
    waiting times don't add up.
    """
    async with AsyncExitStack() as stack:
        # Handle resources
        streamers = [await stack.enter_context(streamcontext(source))
                     for source in sources]
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
async def map(source, func, *more_sources):
    """Apply a given function to the elements of one or several
    asynchronous sequences.

    Each element is used as a positional argument, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted. The function can either be synchronous or
    asynchronous.

    Note: the different sequences are awaited in parrallel, so that their
    waiting times don't add up.
    """
    iscorofunc = asyncio.iscoroutinefunction(func)
    if more_sources:
        source = zip(source, *more_sources)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            if not more_sources:
                item = (item,)
            result = func(*item)
            if iscorofunc:
                result = await result
            yield result


@operator(pipable=True)
async def merge(*sources):
    """Merge several asynchronous sequences together.

    All the sequences are iterated simultaneously and their elements
    are forwarded as soon as they're available. The generation continues
    until all the sequences are exhausted.
    """
    async with AsyncExitStack() as stack:
        # Schedule first anext
        streamers = {}
        for source in sources:
            streamer = await stack.enter_context(streamcontext(source))
            task = asyncio.ensure_future(anext(streamer))
            streamers[task] = streamer
        # Loop over events
        while streamers:
            done, pending = await asyncio.wait(
                list(streamers), return_when="FIRST_COMPLETED")
            # Loop over items
            for task in done:
                try:
                    yield task.result()
                # End of stream
                except StopAsyncIteration:
                    streamers.pop(task)
                # Schedule next anext
                else:
                    streamer = streamers.pop(task)
                    task = asyncio.ensure_future(anext(streamer))
                    streamers[task] = streamer
