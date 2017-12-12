"""Advanced operators (to deal with streams of higher order) ."""

import asyncio

from . import create
from . import combine
from ..aiter_utils import anext
from ..context_utils import AsyncExitStack
from ..core import operator, streamcontext

__all__ = ['concat', 'flatten', 'switch',
           'concatmap', 'flatmap', 'switchmap']


# Helper to manage stream of higher order

@operator(pipable=True)
async def base_combine(source, switch=False):
    streamers = {}

    async def enter(stack, source):
        streamer = await stack.enter_context(streamcontext(source))
        schedule(streamer)
        return streamer

    async def cleanup():
        for task, streamer in streamers.items():
            task.cancel()
            await streamer.aclose()
        streamers.clear()

    def schedule(streamer):
        task = asyncio.ensure_future(anext(streamer))
        streamers[task] = streamer

    async def completed():
        while streamers:
            done, _ = await asyncio.wait(
                list(streamers), return_when="FIRST_COMPLETED")
            for task in done:
                yield streamers.pop(task), task.result

    # Safe context
    async with AsyncExitStack() as stack:
        stack.callback(cleanup)

        # Initialize
        main_streamer = await enter(stack, source)

        # Loop over events
        async for streamer, getter in completed():

            # Get result
            try:
                result = getter()
            # End of stream
            except StopAsyncIteration:
                continue

            # Switch mecanism
            if switch and streamer is main_streamer:
                await cleanup()

            # Setup a new source
            if streamer is main_streamer:
                await enter(stack, result)
            # Simply yield the result
            else:
                yield result

            # Re-schedule streamer
            schedule(streamer)


# Advanced operators (for streams of higher order)

@operator(pipable=True)
async def concat(source):
    """Given an asynchronous sequence of sequences, iterate over the element
    sequences in order.

    After one element sequence is exhausted, the next sequence is generated.
    Errors raised in the source or an element sequence are propagated.
    """
    async with streamcontext(source) as streamer:
        async for iterator in streamer:
            subsource = create.iterate.raw(iterator)
            async with streamcontext(subsource) as substreamer:
                async for item in substreamer:
                    yield item


@operator(pipable=True)
def flatten(source):
    """Given an asynchronous sequence of sequences, iterate over the element
    sequences in parallel.

    Element sequences are generated eagerly and iterated in parallel, yielding
    their elements interleaved as they arrive. Errors raised in the source or
    an element sequence are propagated.
    """
    return base_combine.raw(source, switch=False)


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
def concatmap(source, func, *more_sources):
    """Apply a given function that returns a sequence to the elements of one or
    several asynchronous sequences, and iterate over the returned sequences in
    order.

    The function is applied as described in `map`, and can return an iterable
    or an asynchronous sequence. After one sequence is exhausted, the next
    sequence is generated. Errors raised in a source or output sequence are
    propagated.
    """
    return concat.raw(combine.map.raw(source, func, *more_sources))


@operator(pipable=True)
def flatmap(source, func, *more_sources):
    """Apply a given function that returns a sequence to the elements of one or
    several asynchronous sequences, and iterate over the returned sequences in
    parallel.

    The function is applied as described in `map`, and can return an iterable
    or an asynchronous sequence. Sequences are generated eagerly and
    iterated in parallel, yielding their elements interleaved as they arrive.
    Errors raised in a source or output sequence are propagated.
    """
    return flatten.raw(combine.map.raw(source, func, *more_sources))


@operator(pipable=True)
def switchmap(source, func, *more_sources):
    """Apply a given function that returns a sequence to the elements of one or
    several asynchronous sequences, and iterate over the most recent sequence.

    The function is applied as described in `map`, and can return an iterable
    or an asynchronous sequence. Sequences are generated eagerly, and closed
    once they are superseded by a more recent sequence. Errors raised in a
    source or output sequence (that was not already closed) are propagated.
    """
    return switch.raw(combine.map.raw(source, func, *more_sources))
