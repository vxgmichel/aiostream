
import asyncio

from ..core import operator
from ..utils import anext, aitercontext


@operator(pipable=True)
async def space_out(source, interval):
    timeout = 0
    loop = asyncio.get_event_loop()
    async with aitercontext(source) as streamer:
        async for item in streamer:
            delta = timeout - loop.time()
            delay = delta if delta > 0 else 0
            await asyncio.sleep(delay)
            yield item
            timeout = loop.time() + interval


@operator(pipable=True)
async def timeout(source, timeout):
    async with aitercontext(source) as streamer:
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
    async with aitercontext(source) as streamer:
        async for item in streamer:
            yield item
