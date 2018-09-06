"""Time-specific operators."""

import functools
from ..aiter_utils import anext
from ..core import operator, streamcontext
from ..loops import get_loop

__all__ = ['spaceout', 'delay', 'timeout']


@operator(pipable=True)
async def spaceout(source, interval):
    """Make sure the elements of an asynchronous sequence are separated
    in time by the given interval.
    """
    timeout = 0
    loop = get_loop()
    async with streamcontext(source) as streamer:
        async for item in streamer:
            delta = timeout - loop.time()
            delay = delta if delta > 0 else 0
            await loop.sleep(delay)
            yield item
            timeout = loop.time() + interval


@operator(pipable=True)
async def timeout(source, timeout):
    """Raise a time-out if an element of the asynchronous sequence
    takes too long to arrive.

    Note: the timeout is not global but specific to each step of
    the iteration.
    """
    loop = get_loop()
    async with streamcontext(source) as streamer:
        while True:
            try:
                item = await loop.wait_for_with_timeout(
                    functools.partial(anext, streamer), timeout)
            except StopAsyncIteration:
                break
            else:
                yield item


@operator(pipable=True)
async def delay(source, delay):
    """Delay the iteration of an asynchronous sequence."""
    await get_loop().sleep(delay)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield item
