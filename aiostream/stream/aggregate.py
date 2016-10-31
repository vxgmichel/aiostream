
import asyncio
import operator as op

from . import select
from ..aiter_utils import anext
from ..core import operator, streamcontext


@operator(pipable=True)
async def accumulate(source, func=op.add, initializer=None):
    iscorofunc = asyncio.iscoroutinefunction(func)
    async with streamcontext(source) as streamer:
        # Initialize
        if initializer is None:
            try:
                value = await anext(streamer)
            except StopAsyncIteration:
                return
        else:
            value = initializer
        # First value
        yield value
        # Iterate streamer
        async for item in streamer:
            value = func(value, item)
            if iscorofunc:
                value = await value
            yield value


@operator(pipable=True, position=1)
def reduce(func, source, initializer=None):
    acc = accumulate.raw(source, func, initializer)
    return select.item_at.raw(acc, -1)


@operator(pipable=True)
async def to_list(source):
    result = []
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result.append(item)
    yield result
