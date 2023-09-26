"""Aggregation operators."""
from __future__ import annotations

import asyncio
import builtins
import operator as op
from typing import AsyncIterator, Awaitable, Callable, TypeVar, AsyncIterable, cast


from . import select
from ..aiter_utils import anext
from ..core import pipable_operator, streamcontext

__all__ = ["accumulate", "reduce", "list"]

T = TypeVar("T")


@pipable_operator
async def accumulate(
    source: AsyncIterable[T],
    func: Callable[[T, T], Awaitable[T] | T] = op.add,
    initializer: T | None = None,
) -> AsyncIterator[T]:
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
            returned = func(value, item)
            if iscorofunc:
                awaitable_value = cast("Awaitable[T]", returned)
                value = await awaitable_value
            else:
                value = cast("T", returned)
            yield value


@pipable_operator
def reduce(
    source: AsyncIterable[T],
    func: Callable[[T, T], Awaitable[T] | T],
    initializer: T | None = None,
) -> AsyncIterator[T]:
    """Apply a function of two arguments cumulatively to the items
    of an asynchronous sequence, reducing the sequence to a single value.

    If ``initializer`` is present, it is placed before the items
    of the sequence in the calculation, and serves as a default when the
    sequence is empty.
    """
    acc = accumulate.raw(source, func, initializer)
    return select.item.raw(acc, -1)


@pipable_operator
async def list(source: AsyncIterable[T]) -> AsyncIterator[builtins.list[T]]:
    """Build a list from an asynchronous sequence.

    All the intermediate steps are generated, starting from the empty list.

    This operator can be used to easily convert a stream into a list::

        lst = await stream.list(x)

    ..note:: The same list object is produced at each step in order to avoid
    memory copies.
    """
    result: builtins.list[T] = []
    yield result
    async with streamcontext(source) as streamer:
        async for item in streamer:
            result.append(item)
            yield result
