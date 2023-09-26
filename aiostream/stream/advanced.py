"""Advanced operators (to deal with streams of higher order) ."""
from __future__ import annotations

from typing import AsyncIterator, AsyncIterable, TypeVar, Union, cast
from typing_extensions import ParamSpec

from . import combine

from ..core import Streamer, pipable_operator
from ..manager import StreamerManager


__all__ = ["concat", "flatten", "switch", "concatmap", "flatmap", "switchmap"]


T = TypeVar("T")
U = TypeVar("U")
P = ParamSpec("P")


# Helper to manage stream of higher order


@pipable_operator
async def base_combine(
    source: AsyncIterable[AsyncIterable[T]],
    switch: bool = False,
    ordered: bool = False,
    task_limit: int | None = None,
) -> AsyncIterator[T]:
    """Base operator for managing an asynchronous sequence of sequences.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    The ``switch`` argument enables the switch mecanism, which cause the
    previous subsequence to be discarded when a new one is created.

    The items can either be generated in order or as soon as they're received,
    depending on the ``ordered`` argument.
    """

    # Task limit
    if task_limit is not None and not task_limit > 0:
        raise ValueError("The task limit must be None or greater than 0")

    # Safe context
    async with StreamerManager[Union[AsyncIterable[T], T]]() as manager:
        main_streamer: Streamer[
            AsyncIterable[T] | T
        ] | None = await manager.enter_and_create_task(source)

        # Loop over events
        while manager.tasks:
            # Extract streamer groups
            substreamers = manager.streamers[1:]
            mainstreamers = [main_streamer] if main_streamer in manager.tasks else []

            # Switch - use the main streamer then the substreamer
            if switch:
                filters = mainstreamers + substreamers
            # Concat - use the first substreamer then the main streamer
            elif ordered:
                filters = substreamers[:1] + mainstreamers
            # Flat - use the substreamers then the main streamer
            else:
                filters = substreamers + mainstreamers

            # Wait for next event
            streamer, task = await manager.wait_single_event(filters)

            # Get result
            try:
                result = task.result()

            # End of stream
            except StopAsyncIteration:
                # Main streamer is finished
                if streamer is main_streamer:
                    main_streamer = None

                # A substreamer is finished
                else:
                    await manager.clean_streamer(streamer)

                    # Re-schedule the main streamer if necessary
                    if main_streamer is not None and main_streamer not in manager.tasks:
                        manager.create_task(main_streamer)

            # Process result
            else:
                # Switch mecanism
                if switch and streamer is main_streamer:
                    await manager.clean_streamers(substreamers)

                # Setup a new source
                if streamer is main_streamer:
                    assert isinstance(result, AsyncIterable)
                    await manager.enter_and_create_task(result)

                    # Re-schedule the main streamer if task limit allows it
                    if task_limit is None or task_limit > len(manager.tasks):
                        manager.create_task(streamer)

                # Yield the result
                else:
                    item = cast("T", result)
                    yield item

                    # Re-schedule the streamer
                    manager.create_task(streamer)


# Advanced operators (for streams of higher order)


@pipable_operator
def concat(
    source: AsyncIterable[AsyncIterable[T]], task_limit: int | None = None
) -> AsyncIterator[T]:
    """Given an asynchronous sequence of sequences, generate the elements
    of the sequences in order.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    Errors raised in the source or an element sequence are propagated.
    """
    return base_combine.raw(source, task_limit=task_limit, switch=False, ordered=True)


@pipable_operator
def flatten(
    source: AsyncIterable[AsyncIterable[T]], task_limit: int | None = None
) -> AsyncIterator[T]:
    """Given an asynchronous sequence of sequences, generate the elements
    of the sequences as soon as they're received.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    Errors raised in the source or an element sequence are propagated.
    """
    return base_combine.raw(source, task_limit=task_limit, switch=False, ordered=False)


@pipable_operator
def switch(source: AsyncIterable[AsyncIterable[T]]) -> AsyncIterator[T]:
    """Given an asynchronous sequence of sequences, generate the elements of
    the most recent sequence.

    Element sequences are generated eagerly, and closed once they are
    superseded by a more recent sequence. Once the main sequence is finished,
    the last subsequence will be exhausted completely.

    Errors raised in the source or an element sequence (that was not already
    closed) are propagated.
    """
    return base_combine.raw(source, switch=True)


# Advanced *-map operators


@pipable_operator
def concatmap(
    source: AsyncIterable[T],
    func: combine.SmapCallable[T, AsyncIterable[U]],
    *more_sources: AsyncIterable[T],
    task_limit: int | None = None,
) -> AsyncIterator[U]:
    """Apply a given function that creates a sequence from the elements of one
    or several asynchronous sequences, and generate the elements of the created
    sequences in order.

    The function is applied as described in `map`, and must return an
    asynchronous sequence. The returned sequences are awaited concurrently,
    although it's possible to limit the amount of running sequences using
    the `task_limit` argument.
    """
    mapped = combine.smap.raw(source, func, *more_sources)
    return concat.raw(mapped, task_limit=task_limit)


@pipable_operator
def flatmap(
    source: AsyncIterable[T],
    func: combine.SmapCallable[T, AsyncIterable[U]],
    *more_sources: AsyncIterable[T],
    task_limit: int | None = None,
) -> AsyncIterator[U]:
    """Apply a given function that creates a sequence from the elements of one
    or several asynchronous sequences, and generate the elements of the created
    sequences as soon as they arrive.

    The function is applied as described in `map`, and must return an
    asynchronous sequence. The returned sequences are awaited concurrently,
    although it's possible to limit the amount of running sequences using
    the `task_limit` argument.

    Errors raised in a source or output sequence are propagated.
    """
    mapped = combine.smap.raw(source, func, *more_sources)
    return flatten.raw(mapped, task_limit=task_limit)


@pipable_operator
def switchmap(
    source: AsyncIterable[T],
    func: combine.SmapCallable[T, AsyncIterable[U]],
    *more_sources: AsyncIterable[T],
) -> AsyncIterator[U]:
    """Apply a given function that creates a sequence from the elements of one
    or several asynchronous sequences and generate the elements of the most
    recently created sequence.

    The function is applied as described in `map`, and must return an
    asynchronous sequence. Errors raised in a source or output sequence (that
    was not already closed) are propagated.
    """
    mapped = combine.smap.raw(source, func, *more_sources)
    return switch.raw(mapped)
