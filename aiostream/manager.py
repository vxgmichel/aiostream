"""Provide a context to easily manage several streamers running
concurrently.
"""

import asyncio
import trio
import outcome
from collections import OrderedDict, deque

from .core import streamcontext
from .aiter_utils import anext
from .context_utils import AsyncExitStack


class BaseStreamerManager:
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


class TrioStreamerManager(BaseStreamerManager):
    """Could be much better, for example:\

    - self.streams need no longer be a dict, a set of stream object is enough,
      because we do not have "tasks".

    - It is written to confirm to the interface of the base class. But a standalone
      class might be written more naturally. On the other hand, there is a lot
      of duplicated code here.
    """

    async def __aenter__(self):
        """Asynchronous context manager support.
        """
        result = await super().__aenter__()
        self.nursery = await self.stack.enter_context(trio.open_nursery())

        # A first used a trio.Queue(0), but I suppose that for a completely faithful port
        # of wait(FIRST_COMPLETED), we need to be able to handle multiple or even all 
        # streamers returning a value at the same time - which means the queue maxlen
        # would need to dynamically adjust with the number of streamers.
        #
        # How about a Condition? But we do not really need the lock, only one consumer
        # is using completed(). Even if there were more than one consumer, the asyncio
        # vesrion would give all results that are available concurrenlty to the same
        # consumer, so we just make a local copy of the result array before we reset it.=
        # along with clearing the event. 
        #
        # So another case for an event with Event.clear()? 
        # See: https://github.com/python-trio/trio/issues/637.
        self.are_results_available = trio.Event()
        self.available_results = []
        return result

    async def cleanup(self):
        """Clean up all pending and active streamers."""
        # TRIO: CHANGED TO SKIP TASK CANCELLATION
        # Clear pending streamers
        for streamer in self.pending:
            await streamer.aclose()
        self.pending.clear()
        # Clear active streamers
        for task, streamer in self.streamers.items():
            await streamer.aclose()            
        self.streamers.clear()

    def schedule(self, streamer):
        """Schedule the given streamer to produce its next item."""
        # The task limit is reached        
        if self.full:
            self.pending.append(streamer)
        # Schedule next task
        else:
            async def get():
                result = await outcome.acapture(anext, streamer)
                self.available_results.append((streamer, result))
                self.are_results_available.set()
            self.nursery.start_soon(get)
            self.streamers[streamer] = streamer

    async def completed(self):
        """Asynchronously yield (streamer, getter) tuples as soon as the
        scheduled streamers produce an item, or raise an exception."""
        # Loop over wait operation
        while self.streamers:
            tasks = list(self.streamers)

            if not self.available_results:
                await self.are_results_available.wait()
                self.are_results_available.clear()

            done = self.available_results[::]
            self.available_results = []

            for (streamer, result) in sorted(done, key=lambda item: tasks.index(item[0])):
                # A cleanup can be performed between two yield statements
                if streamer not in self.streamers:
                    continue
                # Yield a (streamer, getter) tuple
                yield self.streamers.pop(streamer), lambda: result.unwrap()
            # Restore            
            self.restore()


StreamerManager = TrioStreamerManager