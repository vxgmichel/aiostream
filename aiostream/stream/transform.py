
import asyncio
import itertools

from .combine import map
from ..core import operator, streamcontext

__all__ = ['map', 'enumerate', 'starmap']


@operator(pipable=True)
async def enumerate(source, start=0, step=1):
    count = itertools.count(start, step)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield next(count), item


@operator(pipable=True, position=1)
def starmap(func, source):
    if asyncio.iscoroutinefunction(func):
        async def starfunc(args):
            return await func(*args)
    else:
        def starfunc(args):
            return func(*args)
    return map(starfunc, source)
