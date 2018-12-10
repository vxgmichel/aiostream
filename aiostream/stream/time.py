"""Time-specific operators."""

from .. import compat
from ..aiter_utils import anext
from ..core import operator, streamcontext

__all__ = ['spaceout', 'delay', 'timeout']


@operator(pipable=True)
async def spaceout(source, interval):
    """Make sure the elements of an asynchronous sequence are separated
    in time by the given interval.
    """
    timeout = 0
    async with streamcontext(source) as streamer:
        async for item in streamer:
            delta = timeout - await compat.time()
            delay = delta if delta > 0 else 0
            await compat.sleep(delay)
            yield item
            timeout = await compat.time() + interval


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
                async with compat.fail_after(timeout):
                    item = await anext(streamer)
            except StopAsyncIteration:
                break
            else:
                yield item


@operator(pipable=True)
async def delay(source, delay):
    """Delay the iteration of an asynchronous sequence."""
    await compat.sleep(delay)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield item
