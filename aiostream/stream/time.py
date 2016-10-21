
import asyncio

from ..core import operator


@operator(pipable=True)
async def space_out(stream, interval):
    timeout = 0
    loop = asyncio.get_event_loop()
    async with source.stream() as streamer:
        async for item in streamer:
            await asyncio.sleep(timeout - loop.time())
            yield item
            timeout = loop.time() + interval
