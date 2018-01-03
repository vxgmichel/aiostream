"""Advanced operators (to deal with streams of higher order) ."""

import asyncio
from collections import OrderedDict, deque, defaultdict

from . import create
from . import combine
from ..aiter_utils import anext
from ..context_utils import AsyncExitStack
from ..core import operator, streamcontext

__all__ = ['concat', 'flatten', 'switch',
           'concatmap', 'flatmap', 'switchmap']


# Helper to manage stream of higher order

class StreamerManager:

    def __init__(self, task_limit=None):
        if task_limit is None:
            task_limit = float('inf')
        self.streamers = {}
        self.pending = deque()
        self.task_limit = task_limit
        self.stack = AsyncExitStack()
        self.stack.callback(self.cleanup)

    async def __aenter__(self):
        await self.stack.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)

    async def enter(self, source):
        streamer = await self.stack.enter_context(streamcontext(source))
        self.schedule(streamer)
        return streamer

    async def cleanup(self):
        # Clear pending streamers
        for streamer in self.pending:
            await streamer.aclose()
        self.pending.clear()
        # Clear active streamers
        for task, streamer in self.streamers.items():
            task.cancel()
            await streamer.aclose()
        self.streamers.clear()

    def schedule(self, streamer):
        # The task limit is reached
        if len(self.streamers) >= self.task_limit:
            self.pending.append(streamer)
            return False
        # Schedule next task
        task = asyncio.ensure_future(anext(streamer))
        self.streamers[task] = streamer
        return True

    def restore(self):
        while self.pending and self.schedule(self.pending.popleft()):
            pass

    async def completed(self):
        while self.streamers:
            done, _ = await asyncio.wait(
                list(self.streamers), return_when="FIRST_COMPLETED")
            for task in done:
                yield self.streamers.pop(task), task.result


@operator(pipable=True)
async def base_combine(source, switch=False, task_limit=None, ordered=False):
    # Argument check
    if task_limit is not None and not task_limit > 0:
        raise ValueError('The task limit must be None or greater than 0')

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
                if ordered and not finished[streamer]:
                    break
                while queue:
                    yield queue.popleft()


# Advanced operators (for streams of higher order)

@operator(pipable=True)
def concat(source, task_limit=None):
    """Given an asynchronous sequence of sequences, iterate over the element
    sequences in order.

    After one element sequence is exhausted, the next sequence is generated.
    Errors raised in the source or an element sequence are propagated.
    """
    return base_combine.raw(
        source, task_limit=task_limit, switch=False, ordered=True)


@operator(pipable=True)
def flatten(source, task_limit=None):
    """Given an asynchronous sequence of sequences, iterate over the element
    sequences in parallel.

    Element sequences are generated eagerly and iterated in parallel, yielding
    their elements interleaved as they arrive. Errors raised in the source or
    an element sequence are propagated.
    """
    return base_combine.raw(
        source, task_limit=task_limit, switch=False, ordered=False)


@operator(pipable=True)
def switch(source):
    """Given an asynchronous sequence of sequences, iterate over the most
    recent element sequence.

    Element sequences are generated eagerly, and closed once they are
    superseded by a more recent sequence. Errors raised in the source or an
    element sequence (that was not already closed) are propagated.
    """
    return base_combine.raw(source, switch=True)


# Advanced *-map operators

@operator(pipable=True)
def concatmap(source, func, *more_sources, task_limit=None):
    """Apply a given function that returns a sequence to the elements of one or
    several asynchronous sequences, and iterate over the returned sequences in
    order.

    The function is applied as described in `map`, and can return an iterable
    or an asynchronous sequence. After one sequence is exhausted, the next
    sequence is generated. Errors raised in a source or output sequence are
    propagated.
    """
    return concat.raw(
        combine.smap.raw(source, func, *more_sources), task_limit=task_limit)


@operator(pipable=True)
def flatmap(source, func, *more_sources, task_limit=None):
    """Apply a given function that returns a sequence to the elements of one or
    several asynchronous sequences, and iterate over the returned sequences in
    parallel.

    The function is applied as described in `map`, and can return an iterable
    or an asynchronous sequence. Sequences are generated eagerly and
    iterated in parallel, yielding their elements interleaved as they arrive.
    Errors raised in a source or output sequence are propagated.
    """
    return flatten.raw(
        combine.smap.raw(source, func, *more_sources), task_limit=task_limit)


@operator(pipable=True)
def switchmap(source, func, *more_sources):
    """Apply a given function that returns a sequence to the elements of one or
    several asynchronous sequences, and iterate over the most recent sequence.

    The function is applied as described in `map`, and can return an iterable
    or an asynchronous sequence. Sequences are generated eagerly, and closed
    once they are superseded by a more recent sequence. Errors raised in a
    source or output sequence (that was not already closed) are propagated.
    """
    return switch.raw(combine.smap.raw(source, func, *more_sources))
