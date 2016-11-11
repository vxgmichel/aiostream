"""Aggregation operators."""

import asyncio
import operator as op

from . import select
from ..aiter_utils import anext
from ..core import operator, streamcontext


@operator(pipable=True)
async def accumulate(source, func=op.add, initializer=None):
    """Generate a series of accumulated sums (or other binary function)
    from an asynchronous sequence.

    If initializer is present, it is placed before the items
    of the sequence in the calculation, and serves as a default
    when the sequence is empty.
    """
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


@operator(pipable=True)
def reduce(source, func, initializer=None):
    """Apply a function of two arguments cumulatively to the items
    of an asynchronous sequence, reducing the sequence to a single value.

    If initializer is present, it is placed before the items
    of the sequence in the calculation, and serves as a default when the
    sequence is empty.
    """
    acc = accumulate.raw(source, func, initializer)
    return select.item.raw(acc, -1)


@operator(pipable=True)
async def list(source):
    """Generate a single list from an asynchronous sequence."""
    result = []
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result.append(item)
    yield result
