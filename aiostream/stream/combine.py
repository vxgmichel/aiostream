
import asyncio
import builtins

from ..core import operator
from ..utils import AsyncExitStack, anext, aitercontext


@operator(pipable=True)
async def chain(*sources):
    for source in sources:
        async with aitercontext(source) as streamer:
            async for item in streamer:
                yield item


@operator(pipable=True)
async def zip(*sources):
    async with AsyncExitStack() as stack:
        # Handle resources
        streamers = []
        for source in sources:
            streamers.append(await stack.enter_context(aitercontext(source)))
        # Loop over items
        while True:
            try:
                coros = builtins.map(anext, streamers)
                items = await asyncio.gather(*coros)
            except StopAsyncIteration:
                break
            else:
                yield tuple(items)


@operator(pipable=True, position=1)
async def map(func, *sources):
    iscorofunc = asyncio.iscoroutinefunction(func)
    source = zip(*sources) if len(sources) > 1 else sources[0]
    async with aitercontext(source) as streamer:
        async for item in streamer:
            if len(sources) == 1:
                item = (item,)
            if iscorofunc:
                yield await func(*item)
            else:
                yield func(*item)


@operator(pipable=True)
async def merge(*sources):
    async with AsyncExitStack() as stack:
        # Schedule first anext
        streamers = {}
        for source in sources:
            streamer = await stack.enter_context(aitercontext(source))
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
