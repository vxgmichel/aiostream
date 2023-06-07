"""Extra operators."""
from __future__ import annotations

import asyncio
import builtins

from typing import TypeVar, Awaitable, Callable, AsyncIterable, AsyncIterator, Any

from .transform import map
from ..core import operator

__all__ = ["action", "print"]


T = TypeVar("T")


@operator(pipable=True)
def action(
    source: AsyncIterable[T], func: Callable[[T], Awaitable[Any] | Any]
) -> AsyncIterator[T]:
    """Perform an action for each element of an asynchronous sequence
    without modifying it.

    The given function can be synchronous or asynchronous.
    """
    if asyncio.iscoroutinefunction(func):

        async def ainnerfunc(arg: T) -> T:
            awaitable = func(arg)
            assert isinstance(awaitable, Awaitable)
            await awaitable
            return arg

        return map.raw(source, ainnerfunc)

    else:

        def innerfunc(arg: T) -> T:
            func(arg)
            return arg

        return map.raw(source, innerfunc)


@operator(pipable=True)
def print(
    source: AsyncIterable[T], template: str = "{}", **kwargs: Any
) -> AsyncIterator[T]:
    """Print each element of an asynchronous sequence without modifying it.

    An optional template can be provided to be formatted with the elements.
    All the keyword arguments are forwarded to the builtin function print.
    """

    def func(value: T) -> None:
        string = template.format(value)
        builtins.print(string, **kwargs)

    return action.raw(source, func)
