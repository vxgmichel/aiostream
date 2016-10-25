
import asyncio
import itertools

from ..core import operator
from .combine import map


@operator(pipable=True)
async def enumerate(source, start=0, step=1):
    count = itertools.count(start, step)
    async with source.stream() as streamer:
        async for item in streamer:
            yield next(count), item


@operator(pipable=True, position=1)
def starmap(func, source):
    if asyncio.iscoroutinefunction(func):
        async def starfunc(args):
            return await func(*args)
    else:
        starfunc = lambda args: func(*args)
    return map(starfunc, source)
