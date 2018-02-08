"""Provide a context to easily manage several streamers running
concurrently.
"""

import asyncio
from collections import OrderedDict, deque

from .core import streamcontext
from .aiter_utils import anext
from .context_utils import AsyncExitStack


class StreamerManager:
    """An asynchronous context manager to deal with several streamers running
    concurrently."""

    def __init__(self, task_limit=None):
        """The number of concurrent task can be limited using the task_limit
        argument."""
        # Argument check
        if task_limit is not None and not task_limit > 0:
            raise ValueError('The task limit must be None or greater than 0')
        # Initialize internals
        self.pending = deque()
        self.task_limit = task_limit
        self.stack = AsyncExitStack()
        self.streamers = OrderedDict()
        self.stack.callback(self.cleanup)

    @property
    def full(self):
        """Indicates that the task limit has been reached."""
        if self.task_limit is None:
            return False
        return len(self.streamers) >= self.task_limit

    async def __aenter__(self):
        """Asynchronous context manager support."""
        await self.stack.__aenter__()
        return self

    async def __aexit__(self, *args):
        """Asynchronous context manager support."""
        return await self.stack.__aexit__(*args)

    async def enter(self, source):
        """Enter a stream and schedule the streamer in a safe manner."""
        streamer = await self.stack.enter_context(streamcontext(source))
        self.schedule(streamer)
        return streamer

    async def cleanup(self):
        """Clean up all pending and active streamers."""
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
        """Schedule the given streamer to produce its next item."""
        # The task limit is reached
        if self.full:
            self.pending.append(streamer)
        # Schedule next task
        else:
            task = asyncio.ensure_future(anext(streamer))
            self.streamers[task] = streamer

    def restore(self):
        """Restore as many pending streamers as possible."""
        while self.pending and not self.full:
            self.schedule(self.pending.popleft())

    async def completed(self):
        """Asynchronously yield (streamer, getter) tuples as soon as the
        scheduled streamers produce an item, or raise an exception."""
        # Loop over wait operation
        while self.streamers:
            tasks = list(self.streamers)
            # Sorted wait for first completed item
            done, _ = await asyncio.wait(tasks, return_when="FIRST_COMPLETED")
            for task in sorted(done, key=tasks.index):
                # A cleanup can be performed between two yield statements
                if task not in self.streamers:
                    continue
                # Yield a (streamer, getter) tuple
                yield self.streamers.pop(task), task.result
            # Restore
            self.restore()
