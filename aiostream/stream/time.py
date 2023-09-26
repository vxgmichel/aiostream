"""Time-specific operators."""
from __future__ import annotations
import asyncio

from ..aiter_utils import anext
from ..core import streamcontext, pipable_operator

from typing import TypeVar, AsyncIterable, AsyncIterator

__all__ = ["spaceout", "delay", "timeout"]


T = TypeVar("T")


@pipable_operator
async def spaceout(source: AsyncIterable[T], interval: float) -> AsyncIterator[T]:
    """Make sure the elements of an asynchronous sequence are separated
    in time by the given interval.
    """
    timeout = 0.0
    loop = asyncio.get_event_loop()
    async with streamcontext(source) as streamer:
        async for item in streamer:
            delta = timeout - loop.time()
            delay = delta if delta > 0 else 0.0
            await asyncio.sleep(delay)
            yield item
            timeout = loop.time() + interval


@pipable_operator
async def timeout(source: AsyncIterable[T], timeout: float) -> AsyncIterator[T]:
    """Raise a time-out if an element of the asynchronous sequence
    takes too long to arrive.

    Note: the timeout is not global but specific to each step of
    the iteration.
    """
    async with streamcontext(source) as streamer:
        while True:
            try:
                item = await asyncio.wait_for(anext(streamer), timeout)
            except StopAsyncIteration:
                break
            else:
                yield item


@pipable_operator
async def delay(source: AsyncIterable[T], delay: float) -> AsyncIterator[T]:
    """Delay the iteration of an asynchronous sequence."""
    await asyncio.sleep(delay)
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield item
