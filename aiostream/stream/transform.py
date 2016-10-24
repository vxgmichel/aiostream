
import itertools

from ..core import operator


@operator(pipable=True)
async def enumerate(source, start=0, step=1):
    count = itertools.count(start, step)
    async with source.stream() as streamer:
        async for item in streamer:
            yield next(count), item
