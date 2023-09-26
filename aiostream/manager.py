"""Provide a context to easily manage several streamers running
concurrently.
"""
from __future__ import annotations

import asyncio
from .aiter_utils import AsyncExitStack

from .aiter_utils import anext
from .core import streamcontext
from typing import (
    TYPE_CHECKING,
    Awaitable,
    List,
    Set,
    Tuple,
    Generic,
    TypeVar,
    Any,
    Type,
    AsyncIterable,
)
from types import TracebackType

if TYPE_CHECKING:
    from asyncio import Task
    from aiostream.core import Streamer

T = TypeVar("T")


class TaskGroup:
    def __init__(self) -> None:
        self._pending: set[Task[Any]] = set()

    async def __aenter__(self) -> TaskGroup:
        return self

    async def __aexit__(
        self,
        typ: Type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        while self._pending:
            task = self._pending.pop()
            await self.cancel_task(task)

    def create_task(self, coro: Awaitable[T]) -> Task[T]:
        task = asyncio.ensure_future(coro)
        self._pending.add(task)
        return task

    async def wait_any(self, tasks: List[Task[T]]) -> Set[Task[T]]:
        done, _ = await asyncio.wait(tasks, return_when="FIRST_COMPLETED")
        self._pending -= done
        return done

    async def wait_all(self, tasks: List[Task[T]]) -> Set[Task[T]]:
        if not tasks:
            return set()
        done, _ = await asyncio.wait(tasks)
        self._pending -= done
        return done

    async def cancel_task(self, task: Task[Any]) -> None:
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


class StreamerManager(Generic[T]):
    def __init__(self) -> None:
        self.tasks: dict[Streamer[T], Task[T]] = {}
        self.streamers: list[Streamer[T]] = []
        self.group: TaskGroup = TaskGroup()
        self.stack = AsyncExitStack()

    async def __aenter__(self) -> StreamerManager[T]:
        await self.stack.__aenter__()
        await self.stack.enter_async_context(self.group)
        return self

    async def __aexit__(
        self,
        typ: Type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        for streamer in self.streamers:
            task = self.tasks.pop(streamer, None)
            if task is not None:
                self.stack.push_async_callback(self.group.cancel_task, task)
            self.stack.push_async_exit(streamer)
        self.tasks.clear()
        self.streamers.clear()
        return await self.stack.__aexit__(typ, value, traceback)

    async def enter_and_create_task(self, aiter: AsyncIterable[T]) -> Streamer[T]:
        streamer = streamcontext(aiter)
        await streamer.__aenter__()
        self.streamers.append(streamer)
        self.create_task(streamer)
        return streamer

    def create_task(self, streamer: Streamer[T]) -> None:
        assert streamer in self.streamers
        assert streamer not in self.tasks
        self.tasks[streamer] = self.group.create_task(anext(streamer))

    async def wait_single_event(
        self, filters: list[Streamer[T]]
    ) -> Tuple[Streamer[T], Task[T]]:
        tasks = [self.tasks[streamer] for streamer in filters]
        done = await self.group.wait_any(tasks)
        for streamer in filters:
            if self.tasks.get(streamer) in done:
                return streamer, self.tasks.pop(streamer)
        assert False

    async def clean_streamer(self, streamer: Streamer[T]) -> None:
        task = self.tasks.pop(streamer, None)
        if task is not None:
            await self.group.cancel_task(task)
        await streamer.aclose()
        self.streamers.remove(streamer)

    async def clean_streamers(self, streamers: list[Streamer[T]]) -> None:
        tasks = [
            self.group.create_task(self.clean_streamer(streamer))
            for streamer in streamers
        ]
        done = await self.group.wait_all(tasks)
        # Raise exception if any
        for task in done:
            task.result()
