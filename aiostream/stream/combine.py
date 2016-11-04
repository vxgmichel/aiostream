
import asyncio
import builtins

from ..aiter_utils import anext
from ..context_utils import AsyncExitStack
from ..core import operator, streamcontext

__all__ = ['chain', 'zip', 'map', 'merge']


@operator(pipable=True)
async def chain(*sources):
    for source in sources:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield item


@operator(pipable=True)
async def zip(*sources):
    async with AsyncExitStack() as stack:
        # Handle resources
        streamers = []
        for source in sources:
            streamers.append(await stack.enter_context(streamcontext(source)))
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
async def map(source, func, *sources):
    iscorofunc = asyncio.iscoroutinefunction(func)
    if sources:
        source = zip(source, *sources)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            if not sources:
                item = (item,)
            result = func(*item)
            if iscorofunc:
                result = await result
            yield result


@operator(pipable=True)
async def merge(*sources):
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
