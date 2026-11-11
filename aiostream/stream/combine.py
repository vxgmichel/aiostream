"""Combination operators."""

from __future__ import annotations

import builtins
import enum
import inspect
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Protocol,
    TypeVar,
    cast,
    overload,
)

from typing_extensions import ParamSpec

from ..aiter_utils import AsyncExitStack, anext
from ..core import Stream, pipable_operator, sources_operator, streamcontext
from ..manager import TaskGroup
from . import advanced, aggregate, create, select
from ._callbacks import AmapCallable, MapCallable, SmapCallable

__all__ = ["chain", "zip", "map", "merge", "ziplatest", "amap", "smap"]

T = TypeVar("T")
U = TypeVar("U")
K = TypeVar("K")
P = ParamSpec("P")


@sources_operator
async def chain(*sources: AsyncIterable[T]) -> AsyncIterator[T]:
    """Chain asynchronous sequences together, in the order they are given.

    Note: the sequences are not iterated until it is required,
    so if the operation is interrupted, the remaining sequences
    will be left untouched.
    """
    for source in sources:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield item


_StopSentinelType = enum.Enum("_StopSentinelType", "STOP_SENTINEL")
STOP_SENTINEL = _StopSentinelType.STOP_SENTINEL


@sources_operator
async def zip(
    *sources: AsyncIterable[T], strict: bool = False
) -> AsyncIterator[tuple[T, ...]]:
    """Combine and forward the elements of several asynchronous sequences.

    Each generated value is a tuple of elements, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted.

    With the `strict` argument set to `True`, the operator makes sure that
    all the sequences have the same length. If not, a `ValueError` is raised.

    Note: the different sequences are awaited in parrallel, so that their
    waiting times don't add up.
    """
    # No sources
    if not sources:
        return

    # One source
    if len(sources) == 1:
        (source,) = sources
        async with streamcontext(source) as streamer:
            async for item in streamer:
                yield (item,)
        return

    # N sources
    async with AsyncExitStack() as stack:

        # Handle resources
        streamers = [
            await stack.enter_async_context(streamcontext(source)) for source in sources
        ]

        # Loop over items
        while True:

            # Concurrency is handled with a TaskGroup to avoid leaving pending tasks if an exception is raised
            async with TaskGroup["T | _StopSentinelType"]() as group:

                # Strict mode requires that we wait for all sources to either produce an item or terminate
                if strict:
                    coros = (anext(streamer, STOP_SENTINEL) for streamer in streamers)
                    tasks = [group.create_task(coro) for coro in coros]
                    done = await group.wait_first_exception(tasks)
                    maybe_items = tuple(task.result() for task in done)
                    if all(item is STOP_SENTINEL for item in maybe_items):
                        break
                    elif any(item is STOP_SENTINEL for item in maybe_items):
                        raise ValueError("The provided sources have different lengths")

                # Non-strict mode requires that we stop at the first terminating source
                else:
                    coros = (anext(streamer) for streamer in streamers)
                    tasks = [group.create_task(coro) for coro in coros]
                    done = await group.wait_first_exception(tasks)
                    # Explicitly retrieve all exceptions to avoid warnings
                    exceptions = [task.exception() for task in done]
                    # Explicitly ignore other exceptions if one source is exhausted
                    if any(isinstance(e, StopAsyncIteration) for e in exceptions):
                        break
                    # Raise other exceptions here if any
                    maybe_items = tuple(task.result() for task in done)

            # `group.wait_first exception` guarantees order
            # and that all tasks have completed when no exception occurred
            assert len(maybe_items) == len(sources)

            # This holds because we've ruled out STOP_SENTINEL above
            yield cast("tuple[T, ...]", maybe_items)


@pipable_operator
async def smap(
    source: AsyncIterable[T],
    func: SmapCallable[T, U],
    *more_sources: AsyncIterable[T],
) -> AsyncIterator[U]:
    """Apply a given function to the elements of one or several
    asynchronous sequences.

    Each element is used as a positional argument, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted. The function is treated synchronously.

    Note: if more than one sequence is provided, they're awaited concurrently
    so that their waiting times don't add up.
    """
    stream = zip(source, *more_sources)
    async with streamcontext(stream) as streamer:
        async for item in streamer:
            yield func(*item)


@pipable_operator
def amap(
    source: AsyncIterable[T],
    corofn: AmapCallable[T, U],
    *more_sources: AsyncIterable[T],
    ordered: bool = True,
    task_limit: int | None = None,
) -> AsyncIterator[U]:
    """Apply a given coroutine function to the elements of one or several
    asynchronous sequences.

    Each element is used as a positional argument, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted.

    The results can either be returned in or out of order, depending on
    the corresponding ``ordered`` argument.

    The coroutines run concurrently but their amount can be limited using
    the ``task_limit`` argument. A value of ``1`` will cause the coroutines
    to run sequentially.

    If more than one sequence is provided, they're also awaited concurrently,
    so that their waiting times don't add up.
    """

    async def func(arg: T, *args: T) -> AsyncIterable[U]:
        yield await corofn(arg, *args)

    if ordered:
        return advanced.concatmap.raw(
            source, func, *more_sources, task_limit=task_limit
        )
    return advanced.flatmap.raw(source, func, *more_sources, task_limit=task_limit)


class MapOperator(Protocol):
    """Explicit type for the `map` operator.

    The generic `PipableOperator` type cannot be used here: the callback
    return type `Awaitable[U] | U` is ambiguous for coroutine functions,
    which leads mypy to infer `Never` for `U` (see issue #128). Instead,
    an overload for coroutine functions is checked first, before falling
    back to the original signature.

    Note that the type checkers cannot distinguish a coroutine function from
    a synchronous function returning a coroutine (which is not awaited by
    `map`, unless it is wrapped with `aiostream.async_`).
    """

    @overload
    def __call__(
        self,
        source: AsyncIterable[T],
        /,
        func: AmapCallable[T, U],
        *more_sources: AsyncIterable[T],
        ordered: bool = True,
        task_limit: int | None = None,
    ) -> Stream[U]: ...

    @overload
    def __call__(
        self,
        source: AsyncIterable[T],
        /,
        func: MapCallable[T, U],
        *more_sources: AsyncIterable[T],
        ordered: bool = True,
        task_limit: int | None = None,
    ) -> Stream[U]: ...

    @overload
    @staticmethod
    def raw(
        source: AsyncIterable[T],
        /,
        func: AmapCallable[T, U],
        *more_sources: AsyncIterable[T],
        ordered: bool = True,
        task_limit: int | None = None,
    ) -> AsyncIterator[U]: ...

    @overload
    @staticmethod
    def raw(
        source: AsyncIterable[T],
        /,
        func: MapCallable[T, U],
        *more_sources: AsyncIterable[T],
        ordered: bool = True,
        task_limit: int | None = None,
    ) -> AsyncIterator[U]: ...

    @overload
    @staticmethod
    def pipe(
        func: AmapCallable[T, U],
        *more_sources: AsyncIterable[T],
        ordered: bool = True,
        task_limit: int | None = None,
    ) -> Callable[[AsyncIterable[T]], Stream[U]]: ...

    @overload
    @staticmethod
    def pipe(
        func: MapCallable[T, U],
        *more_sources: AsyncIterable[T],
        ordered: bool = True,
        task_limit: int | None = None,
    ) -> Callable[[AsyncIterable[T]], Stream[U]]: ...


def _map_operator(func: Callable[..., AsyncIterator[Any]]) -> MapOperator:
    return cast("MapOperator", pipable_operator(func))


@_map_operator
def map(
    source: AsyncIterable[T],
    func: MapCallable[T, U],
    *more_sources: AsyncIterable[T],
    ordered: bool = True,
    task_limit: int | None = None,
) -> AsyncIterator[U]:
    """Apply a given function to the elements of one or several
    asynchronous sequences.

    Each element is used as a positional argument, using the same order as
    their respective sources. The generation continues until the shortest
    sequence is exhausted. The function can either be synchronous or
    asynchronous (coroutine function).

    If the function is asynchronous, the results can either be returned in
    or out of order, depending on the corresponding ``ordered`` argument.
    A ``ValueError`` is raised if this argument is provided and the provided
    function is synchronous.

    If the function is asynchronous, the coroutines run concurrently but their
    amount can be limited using the ``task_limit`` argument. A value of ``1``
    will cause the coroutines to run sequentially. A ``ValueError`` is raised
    if this argument is provided and the provided function is synchronous.

    If more than one sequence is provided, they're also awaited concurrently,
    so that their waiting times don't add up.

    It might happen that the provided function returns a coroutine but is not
    recognized as a coroutine function by ``inspect.iscoroutinefunction``.
    In this case, one can wrap the function with ``aiostream.async_`` in order
    to force ``map`` to await the resulting coroutine. The following example
    illustrates the use of ``async_`` with a lambda function::

        from aiostream import stream, async_
        ...
        ys = stream.map(xs, async_(lambda ms: asyncio.sleep(ms / 1000)))

    Instances with an asynchronous ``__call__`` method also need this explicit
    wrapper::

        class AsyncDouble:
            async def __call__(self, value):
                return value * 2

        ys = stream.map(xs, async_(AsyncDouble()))
    """
    if inspect.iscoroutinefunction(func):
        return amap.raw(
            source, func, *more_sources, ordered=ordered, task_limit=task_limit
        )

    if not ordered:
        raise ValueError(
            "The 'ordered' argument can only be used when the provided function is asynchronous."
        )

    if task_limit is not None:
        raise ValueError(
            "The 'task_limit' argument can only be used when the provided function is asynchronous."
        )

    sync_func = cast("SmapCallable[T, U]", func)
    return smap.raw(source, sync_func, *more_sources)


@sources_operator
def merge(
    *sources: AsyncIterable[T],
) -> AsyncIterator[T]:
    """Merge several asynchronous sequences together.

    All the sequences are iterated simultaneously and their elements
    are forwarded as soon as they're available. The generation continues
    until all the sequences are exhausted.
    """
    source_stream: AsyncIterable[AsyncIterable[T]] = create.iterate.raw(sources)
    return advanced.flatten.raw(source_stream)


@sources_operator
def ziplatest(
    *sources: AsyncIterable[T],
    partial: bool = True,
    default: T | None = None,
) -> AsyncIterator[tuple[T | None, ...]]:
    """Combine several asynchronous sequences together, producing a tuple with
    the lastest element of each sequence whenever a new element is received.

    The value to use when a sequence has not procuded any element yet is given
    by the ``default`` argument (defaulting to ``None``).

    The producing of partial results can be disabled by setting the optional
    argument ``partial`` to ``False``.

    All the sequences are iterated simultaneously and their elements
    are forwarded as soon as they're available. The generation continues
    until all the sequences are exhausted.
    """
    n = len(sources)

    # Custom getter
    def getter(dct: dict[int, T]) -> Callable[[int], T | None]:
        return lambda key: dct.get(key, default)

    # Add source index to the items
    def make_func(i: int) -> SmapCallable[T, dict[int, T]]:
        def func(x: T) -> dict[int, T]:
            return {i: x}

        return func

    new_sources = [smap.raw(source, make_func(i)) for i, source in enumerate(sources)]

    # Merge the sources
    merged = merge.raw(*new_sources)

    # Accumulate the current state in a dict
    accumulated = aggregate.accumulate.raw(merged, lambda x, e: {**x, **e})

    # Filter partial result
    filtered = (
        accumulated
        if partial
        else select.filter.raw(accumulated, lambda x: len(x) == n)
    )

    # Convert the state dict to a tuple
    def dict_to_tuple(x: dict[int, T]) -> tuple[T | None, ...]:
        return tuple(builtins.map(getter(x), range(n)))

    return smap.raw(filtered, dict_to_tuple)
