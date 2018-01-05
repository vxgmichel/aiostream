"""Advanced operators (to deal with streams of higher order) ."""

from collections import OrderedDict, deque, defaultdict

from . import combine
from ..core import operator
from ..manager import StreamerManager

__all__ = ['concat', 'flatten', 'switch',
           'concatmap', 'flatmap', 'switchmap']


# Helper to manage stream of higher order

@operator(pipable=True)
async def base_combine(source, switch=False, ordered=False, task_limit=None):
    """Base operator for managing an asynchronous sequence of sequences.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    The ``switch`` argument enables the switch mecanism, which cause the
    previous subsequence to be discarded when a new one is created.

    The items can either be generated in order or as soon as they're received,
    depending on the ``ordered`` argument.
    """
    # Data structures
    results = OrderedDict()
    finished = defaultdict(bool)

    # Safe context
    async with StreamerManager(task_limit) as manager:

        # Initialize
        main_streamer = await manager.enter(source)

        # Loop over events
        async for streamer, getter in manager.completed():

            # Get result
            try:
                result = getter()

            # End of stream
            except StopAsyncIteration:
                manager.restore()
                finished[streamer] = True

            # Process result
            else:

                # Switch mecanism
                if switch and streamer is main_streamer:
                    results.clear()
                    await manager.cleanup()

                # Setup a new source
                if streamer is main_streamer:
                    results[await manager.enter(result)] = deque()

                # Append the result
                else:
                    results[streamer].append(result)

                # Re-schedule streamer
                manager.schedule(streamer)

            # Yield results
            for streamer, queue in results.items():

                # Yield all items
                while queue:
                    yield queue.popleft()

                # Guarantee order
                if ordered and not finished[streamer]:
                    break


# Advanced operators (for streams of higher order)

@operator(pipable=True)
def concat(source, task_limit=None):
    """Given an asynchronous sequence of sequences, generate the elements
    of the sequences in order.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    Errors raised in the source or an element sequence are propagated.
    """
    return base_combine.raw(
        source, task_limit=task_limit, switch=False, ordered=True)


@operator(pipable=True)
def flatten(source, task_limit=None):
    """Given an asynchronous sequence of sequences, generate the elements
    of the sequences as soon as they're received.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    Errors raised in the source or an element sequence are propagated.
    """
    return base_combine.raw(
        source, task_limit=task_limit, switch=False, ordered=False)


@operator(pipable=True)
def switch(source):
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

@operator(pipable=True)
def concatmap(source, func, *more_sources, task_limit=None):
    """Apply a given function that creates a sequence from the elements of one
    or several asynchronous sequences, and generate the elements of the created
    sequences in order.

    The function is applied as described in `map`, and must return an
    asynchronous sequence. The returned sequences are awaited concurrently,
    although it's possible to limit the amount of running sequences using
    the `task_limit` argument.
    """
    return concat.raw(
        combine.smap.raw(source, func, *more_sources), task_limit=task_limit)


@operator(pipable=True)
def flatmap(source, func, *more_sources, task_limit=None):
    """Apply a given function that creates a sequence from the elements of one
    or several asynchronous sequences, and generate the elements of the created
    sequences as soon as they arrive.

    The function is applied as described in `map`, and must return an
    asynchronous sequence. The returned sequences are awaited concurrently,
    although it's possible to limit the amount of running sequences using
    the `task_limit` argument.

    Errors raised in a source or output sequence are propagated.
    """
    return flatten.raw(
        combine.smap.raw(source, func, *more_sources), task_limit=task_limit)


@operator(pipable=True)
def switchmap(source, func, *more_sources):
    """Apply a given function that creates a sequence from the elements of one
    or several asynchronous sequences and generate the elements of the most
    recently created sequence.

    The function is applied as described in `map`, and must return an
    asynchronous sequence. Errors raised in a source or output sequence (that
    was not already closed) are propagated.
    """
    return switch.raw(combine.smap.raw(source, func, *more_sources))
