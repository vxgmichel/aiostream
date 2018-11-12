"""Time-specific operators."""

import asyncio

from ..aiter_utils import anext
from ..core import operator, streamcontext

__all__ = ['spaceout', 'delay', 'timeout']


async def wait_for(aw, timeout):
    task = asyncio.ensure_future(aw)
    try:
        return await asyncio.wait_for(task, timeout)
    finally:
        # Python 3.6 compatibility
        if not task.done():  # pragma: no cover
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@operator(pipable=True)
async def spaceout(source, interval):
    """Make sure the elements of an asynchronous sequence are separated
    in time by the given interval.
    """
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
    """Raise a time-out if an element of the asynchronous sequence
    takes too long to arrive.

    Note: the timeout is not global but specific to each step of
    the iteration.
    """
    async with streamcontext(source) as streamer:
        while True:
            try:
                item = await wait_for(anext(streamer), timeout)
            except StopAsyncIteration:
                break
            else:
                yield item


@operator(pipable=True)
async def delay(source, delay):
    """Delay the iteration of an asynchronous sequence."""
    await asyncio.sleep(delay)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield item
