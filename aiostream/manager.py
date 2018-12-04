"""Provide a context to easily manage several streamers running
concurrently.
"""

import asyncio
from .aiter_utils import AsyncExitStack

from .aiter_utils import anext
from .core import streamcontext


class TaskGroup:

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return

    def create_task(self, coro):
        return asyncio.ensure_future(coro)

    async def wait_any(self, tasks):
        done, _ = await asyncio.wait(tasks, return_when="FIRST_COMPLETED")
        return done

    async def wait_all(self, tasks):
        if not tasks:
            return set()
        done, _ = await asyncio.wait(tasks)
        return done

    async def stop_task(self, task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


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
        try:
            await self.clean()
        finally:
            return await self.stack.__aexit__(*args)

    async def enter_and_create_task(self, aiter):
        streamer = await self.stack.enter_async_context(streamcontext(aiter))
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
        self.streamers.remove(streamer)
        task = self.tasks.pop(streamer, None)
        if task is not None:
            await self.group.stop_task(task)
        await streamer.aclose()
        # TODO: Remove the streamer from the stack to prevent a memory leak

    async def clean_streamers(self, streamers):
        tasks = [
            self.group.create_task(self.clean_streamer(streamer))
            for streamer in streamers]
        done = await self.group.wait_all(tasks)
        # Raise exception if any
        for task in done:
            task.result()

    async def clean(self):
        await self.clean_streamers(self.streamers)
        assert not self.tasks
        assert not self.streamers
