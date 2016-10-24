
import asyncio
import builtins

from ..core import operator
from ..utils import AsyncExitStack, anext


@operator(pipable=True)
async def chain(*sources):
    for source in sources:
        async with source.stream() as streamer:
            async for item in streamer:
                yield item


@operator(pipable=True)
async def zip(*sources):
    async with AsyncExitStack() as stack:
        # Handler resources
        streamers = []
        for source in sources:
            streamers.append(await stack.enter_context(source.stream()))
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
    async with source.stream() as streamer:
        async for item in streamer:
            if len(sources) == 1:
                item = (item,)
            if iscorofunc:
                yield await func(*item)
            else:
                yield func(*item)


@operator(pipable=True, position=1)
def starmap(func, source):
    if asyncio.iscoroutinefunction(func):
        async def starfunc(args):
            return await func(*args)
    else:
        starfunc = lambda args: func(*args)
    return map(starfunc, source)
