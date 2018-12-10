"""Advanced operators (to deal with streams of higher order) ."""

from . import combine

from .. import compat
from ..aiter_utils import anext
from ..core import operator, streamcontext

__all__ = ['concat', 'flatten', 'switch',
           'concatmap', 'flatmap', 'switchmap']


# Helper task

async def controlled_anext(streamer, semaphore=None):
    if semaphore is None:
        return await anext(streamer)
    async with semaphore:
        return await anext(streamer)


async def streamer_task(source, item_channel, control_channel, semaphore=None):
    # Enter semaphore
    if semaphore is not None:
        async with semaphore:
            return await streamer_task(source, item_channel, control_channel)
    # Loop over items
    async with item_channel:
        async with streamcontext(source) as streamer:
            async for item in streamer:
                await item_channel.send(item)
                await control_channel.receive()


# Advanced operators (for streams of higher order)

@operator(pipable=True)
async def concat(source, task_limit=None):
    """Given an asynchronous sequence of sequences, generate the elements
    of the sequences in order.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    Errors raised in the source or an element sequence are propagated.
    """
    # Task limit
    if task_limit is not None and not task_limit > 0:
        raise ValueError('The task limit must be None or greater than 0')

    async def meta_task(group, meta_channel, control_channel, semaphore):
        # Controlled context
        async with meta_channel:
            async with streamcontext(source) as streamer:

                # Loop over subsources
                while True:

                    # Get subsource, protected by the semaphore
                    try:
                        subsource = await controlled_anext(streamer, semaphore)
                    except StopAsyncIteration:
                        break

                    # Create new channel and spawn streamer task
                    send_channel, receive_channel = compat.open_channel()
                    await meta_channel.send(receive_channel)
                    await group.spawn(
                        streamer_task,
                        subsource,
                        send_channel,
                        control_channel.clone(),
                        semaphore)

                    # Let the streamer task start
                    await compat.sleep(0)

    # Use a task group
    async with compat.create_task_group() as group:

        # Create channels and spawn meta task
        semaphore = None if task_limit is None else compat.create_semaphore(task_limit)
        capacity = float('inf') if task_limit is None else task_limit
        meta_send_channel, meta_receive_channel = compat.open_channel(capacity)
        control_send_channel, control_receive_channel = compat.open_channel()
        await group.spawn(
            meta_task, group, meta_send_channel, control_receive_channel, semaphore)

        # Loop over channels
        async for channel in meta_receive_channel:
            # Loop over items
            async for item in channel:
                yield item
                await control_send_channel.send(None)


@operator(pipable=True)
async def flatten(source, task_limit=None):
    """Given an asynchronous sequence of sequences, generate the elements
    of the sequences as soon as they're received.

    The sequences are awaited concurrently, although it's possible to limit
    the amount of running sequences using the `task_limit` argument.

    Errors raised in the source or an element sequence are propagated.
    """
    # Task limit
    if task_limit is not None and not task_limit > 0:
        raise ValueError('The task limit must be None or greater than 0')

    async def meta_task(group, item_channel, control_channel, semaphore):
        # Controlled context
        async with item_channel:
            async with streamcontext(source) as streamer:

                # Loop over subsources
                while True:

                    # Get subsource, protected by the semaphore
                    try:
                        subsource = await controlled_anext(streamer, semaphore)
                    except StopAsyncIteration:
                        break

                    # Spawn streamer task
                    await group.spawn(
                        streamer_task,
                        subsource,
                        item_channel.clone(),
                        control_channel.clone(),
                        semaphore)

                    # Let the task start
                    await compat.sleep(0)

    # Use a task group
    async with compat.create_task_group() as group:

        # Create channels and spawn meta task
        semaphore = None if task_limit is None else compat.create_semaphore(task_limit)
        item_send_channel, item_receive_channel = compat.open_channel()
        control_send_channel, control_receive_channel = compat.open_channel()
        await group.spawn(
            meta_task, group, item_send_channel, control_receive_channel, semaphore)

        # Loop over items
        async for item in item_receive_channel:
            yield item
            await control_send_channel.send(None)


@operator(pipable=True)
async def switch(source):
    """Given an asynchronous sequence of sequences, generate the elements of
    the most recent sequence.

    Element sequences are generated eagerly, and closed once they are
    superseded by a more recent sequence. Once the main sequence is finished,
    the last subsequence will be exhausted completely.

    Errors raised in the source or an element sequence (that was not already
    closed) are propagated.
    """

    async def meta_task(item_channel, control_channel):
        # Controlled context
        async with item_channel:
            async with streamcontext(source) as streamer:

                # Get first subsource
                try:
                    subsource = await anext(streamer)
                except StopAsyncIteration:
                    return

                # Loop over subsources
                while True:

                    async with compat.create_task_group() as group:
                        # Spawn streamer task
                        await group.spawn(
                            streamer_task,
                            subsource,
                            item_channel.clone(),
                            control_channel.clone())

                        # Get next subsource
                        try:
                            subsource = await anext(streamer)
                        except StopAsyncIteration:
                            return

                        # Cancel the streamer task
                        await group.cancel_scope.cancel()

    # Use a task group
    async with compat.create_task_group() as group:

        # Create channels and spawn meta task
        item_send_channel, item_receive_channel = compat.open_channel()
        control_send_channel, control_receive_channel = compat.open_channel()
        await group.spawn(
            meta_task, item_send_channel, control_receive_channel)

        # Loop over items
        async for item in item_receive_channel:
            yield item
            await control_send_channel.send(None)


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
