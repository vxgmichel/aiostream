"""Extra operators."""
from __future__ import annotations

import asyncio
import builtins

from typing import TypeVar, Awaitable, Callable, AsyncIterable, AsyncIterator, Any

from .combine import amap, smap
from ..core import pipable_operator

__all__ = ["action", "print"]


T = TypeVar("T")


@pipable_operator
def action(
    source: AsyncIterable[T],
    func: Callable[[T], Awaitable[Any] | Any],
    ordered: bool = True,
    task_limit: int | None = None,
) -> AsyncIterator[T]:
    """Perform an action for each element of an asynchronous sequence
    without modifying it.

    The given function can be synchronous or asynchronous.

    The results can either be returned in or out of order, depending on
    the corresponding ``ordered`` argument. This argument is ignored if the
    provided function is synchronous.

    The coroutines run concurrently but their amount can be limited using
    the ``task_limit`` argument. A value of ``1`` will cause the coroutines
    to run sequentially. This argument is ignored if the provided function
    is synchronous.
    """
    if asyncio.iscoroutinefunction(func):

        async def ainnerfunc(arg: T, *_: object) -> T:
            awaitable = func(arg)
            assert isinstance(awaitable, Awaitable)
            await awaitable
            return arg

        return amap.raw(source, ainnerfunc, ordered=ordered, task_limit=task_limit)

    else:

        def innerfunc(arg: T, *_: object) -> T:
            func(arg)
            return arg

        return smap.raw(source, innerfunc)


@pipable_operator
def print(
    source: AsyncIterable[T],
    template: str = "{}",
    sep: str = " ",
    end: str = "\n",
    file: Any | None = None,
    flush: bool = False,
) -> AsyncIterator[T]:
    """Print each element of an asynchronous sequence without modifying it.

    An optional template can be provided to be formatted with the elements.
    All the keyword arguments are forwarded to the builtin function print.
    """

    def func(value: T) -> None:
        string = template.format(value)
        builtins.print(
            string,
            sep=sep,
            end=end,
            file=file,
            flush=flush,
        )

    return action.raw(source, func)
