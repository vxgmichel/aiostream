"""Go-style generators."""

import asyncio
import functools
from .aiter_utils import AsyncIteratorContext


class ConcurrentIteratorContext(AsyncIteratorContext):

    def __init__(self, aiterable, buffering=0):
        super().__init__(aiterable)
        self._buffering = buffering
        self._in_queue = asyncio.Queue(self.maxsize)
        self._out_queue = asyncio.Queue(self.maxsize)
        self._task = None

    @property
    def maxsize(self):
        if self._buffering < 0:
            return 0
        if self._buffering == 0:
            return 1
        return self._buffering

    # Task handling

    async def __aenter__(self):
        await super().__aenter__()
        self._task = asyncio.ensure_future(self._safe_target())
        return self

    async def __aexit__(self, *args):
        try:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        finally:
            self._state = self._FINISHED

    # Target for task

    async def _safe_target(self):
        try:
            await self._target()
        finally:
            if hasattr(self._aiterator, 'aclose'):
                await self._aiterator.aclose()

    async def _target(self):
        coro = super()._asend()
        while True:
            # Get data from iterator
            try:
                value = await coro
            # Cancellation
            except asyncio.CancelledError:
                print('oops', self._aiterator)
                return
            # Termination
            except BaseException as exc:
                if isinstance(exc, GeneratorExit):
                    exc = StopAsyncIteration()
                await self._out_queue.put((None, exc))
                return
            await self._out_queue.put((value, None))
            # Buffering mode
            if self._buffering:
                coro = super()._asend()
                continue
            # Handshake
            args = await self._in_queue.get()
            coro = super()._asend(*args)

    # Internal logic

    async def _asend(self, value=None, exc=None):
        # Perform checks
        if value is not None:
            self._aiterator.asend
            assert not self.buffering
        if exc is not None:
            self._aiterator.athrow
            assert not self.buffering
        # Handshake
        if not self._buffering:
            await self._in_queue.put((value, exc))
        # Get data
        value, exc = await self._out_queue.get()
        if exc is not None:
            raise exc
        return value


# Utilities


def gocontext(aiterable, buffering=0):
    return ConcurrentIteratorContext(aiterable, buffering=buffering)


def gogenerator(aiterable=None, buffering=0):
    def decorator(aiterable):
        @functools.wraps(aiterable)
        def wrapper(*args, **kwargs):
            return gocontext(aiterable(*args, **kwargs), buffering)
        return wrapper
    if aiterable is None:
        return decorator
    return decorator(aiterable)
