
import asyncio

from ..aiter_utils import anext
from ..core import operator, streamcontext

__all__ = ['space_out', 'delay', 'timeout']


@operator(pipable=True)
async def space_out(source, interval):
    timeout = 0
    loop = asyncio.get_event_loop()
    async with streamcontext(source) as streamer:
        async for item in streamer:
            delta = timeout - loop.time()
            delay = delta if delta > 0 else 0
            await asyncio.sleep(delay)
            yield item
            timeout = loop.time() + interval


@operator(pipable=True)
async def timeout(source, timeout):
    async with streamcontext(source) as streamer:
        while True:
            try:
                item = await asyncio.wait_for(anext(streamer), timeout)
            except StopAsyncIteration:
                break
            else:
                yield item


@operator(pipable=True)
async def delay(source, delay):
    await asyncio.sleep(delay)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield item
