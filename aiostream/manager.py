"""Provide a context to easily manage several streamers running
concurrently.
"""

import asyncio
from .aiter_utils import AsyncExitStack

from .aiter_utils import anext
from .core import streamcontext


class TaskGroup:
    def __init__(self):
        self._pending = set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        while self._pending:
            task = self._pending.pop()
            await self.cancel_task(task)

    def create_task(self, coro):
        task = asyncio.ensure_future(coro)
        self._pending.add(task)
        return task

    async def wait_any(self, tasks):
        done, _ = await asyncio.wait(tasks, return_when="FIRST_COMPLETED")
        self._pending -= done
        return done

    async def wait_all(self, tasks):
        if not tasks:
            return set()
        done, _ = await asyncio.wait(tasks)
        self._pending -= done
        return done

    async def cancel_task(self, task):
        try:
            # The task is already cancelled
            if task.cancelled():
                pass
            # The task is already finished
            elif task.done():
                # Discard the pending exception (if any).
                # This makes sense since we don't know in which context the exception
                # was meant to be processed. For instance, a `StopAsyncIteration`
                # might be raised to notify that the end of a streamer has been reached.
                task.exception()
            # The task needs to be cancelled and awaited
            else:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                # Silence any exception raised while cancelling the task.
                # This might happen if the `CancelledError` is silenced, and the
                # corresponding async generator returns, causing the `anext` call
                # to raise a `StopAsyncIteration`.
                except Exception:
                    pass
        finally:
            self._pending.discard(task)


class StreamerManager:
    def __init__(self):
        self.tasks = {}
        self.streamers = []
        self.group = TaskGroup()
        self.stack = AsyncExitStack()

    async def __aenter__(self):
        await self.stack.__aenter__()
        await self.stack.enter_async_context(self.group)
        return self

    async def __aexit__(self, *args):
        for streamer in self.streamers:
            task = self.tasks.pop(streamer, None)
            if task is not None:
                self.stack.push_async_callback(self.group.cancel_task, task)
            self.stack.push_async_exit(streamer)
        self.tasks.clear()
        self.streamers.clear()
        return await self.stack.__aexit__(*args)

    async def enter_and_create_task(self, aiter):
        streamer = streamcontext(aiter)
        await streamer.__aenter__()
        self.streamers.append(streamer)
        self.create_task(streamer)
        return streamer

    def create_task(self, streamer):
        assert streamer in self.streamers
        assert streamer not in self.tasks
        self.tasks[streamer] = self.group.create_task(anext(streamer))

    async def wait_single_event(self, filters):
        tasks = [self.tasks[streamer] for streamer in filters]
        done = await self.group.wait_any(tasks)
        for streamer in filters:
            if self.tasks.get(streamer) in done:
                return streamer, self.tasks.pop(streamer)

    async def clean_streamer(self, streamer):
        task = self.tasks.pop(streamer, None)
        if task is not None:
            await self.group.cancel_task(task)
        await streamer.aclose()
        self.streamers.remove(streamer)

    async def clean_streamers(self, streamers):
        tasks = [
            self.group.create_task(self.clean_streamer(streamer))
            for streamer in streamers
        ]
        done = await self.group.wait_all(tasks)
        # Raise exception if any
        for task in done:
            task.result()
