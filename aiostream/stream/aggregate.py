"""Aggregation operators."""

import asyncio
import operator as op

from . import select
from ..aiter_utils import anext
from ..core import operator, streamcontext

__all__ = ["accumulate", "reduce", "list"]


@operator(pipable=True)
async def accumulate(source, func=op.add, initializer=None):
    """Generate a series of accumulated sums (or other binary function)
    from an asynchronous sequence.

    If ``initializer`` is present, it is placed before the items
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

    If ``initializer`` is present, it is placed before the items
    of the sequence in the calculation, and serves as a default when the
    sequence is empty.
    """
    acc = accumulate.raw(source, func, initializer)
    return select.item.raw(acc, -1)


@operator(pipable=True)
async def list(source):
    """Build a list from an asynchronous sequence.

    All the intermediate steps are generated, starting from the empty list.

    This operator can be used to easily convert a stream into a list::

        lst = await stream.list(x)

    ..note:: The same list object is produced at each step in order to avoid
    memory copies.
    """
    result = []
    yield result
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result.append(item)
            yield result
