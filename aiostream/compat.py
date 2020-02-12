
import math
import inspect
from asyncio import iscoroutinefunction

import anyio
import sniffio

try:
    from contextlib import asynccontextmanager
except ImportError:
    from async_generator import asynccontextmanager  # pragma: no cover

from anyio import (
    create_task_group, create_semaphore, open_cancel_scope, create_lock
)

__all__ = ['iscoroutinefunction', 'time', 'sleep_forever', 'open_channel',
           'sleep', 'fail_after', 'create_task_group', 'create_semaphore',
           'open_cancel_scope', 'create_lock']


async def sleep(time, result=None):
    await anyio.sleep(time)
    return result


async def sleep_forever():
    while True:
        # Sleep for a day
        await anyio.sleep(60 * 60 * 24)


async def time():
    return await anyio.current_time()


@asynccontextmanager
async def safe_generator(obj):
    asynclib = sniffio.current_async_library()
    if asynclib == 'curio' and inspect.isasyncgen(obj):
        import curio
        curio.meta.finalize._finalized.add(obj)
        try:
            yield obj
        finally:
            curio.meta.finalize._finalized.discard(obj)
    else:
        yield obj


def timeout_error():
    asynclib = sniffio.current_async_library()
    if asynclib == 'asyncio':
        import asyncio
        return asyncio.TimeoutError()
    if asynclib == 'trio':
        import trio
        return trio.TooSlowError()
    if asynclib == 'curio':
        import curio
        return curio.TaskTimeout()
    raise RuntimeError("Asynclib detection failed")  # pragma: no cover


def fail_after(*args, **kwargs):

    async def _fail_after():
        try:
            async with anyio.fail_after(*args, **kwargs) as value:
                yield value
        except TimeoutError:
            raise timeout_error()

    asynclib = sniffio.current_async_library()
    if asynclib == 'curio':
        import curio.meta
        _fail_after = curio.meta.safe_generator(_fail_after)

    return asynccontextmanager(_fail_after)()


def open_channel(capacity=0):
    asynclib = sniffio.current_async_library()
    if asynclib == 'trio':
        import trio
        return trio.open_memory_channel(capacity)

    class ClosedResourceError(IOError):
        pass

    senders = set()
    sentinel = object()
    send_queue = anyio.create_queue(1)
    maxsize = 0 if capacity == math.inf else 1 if capacity == 0 else capacity
    receive_queue = anyio.create_queue(maxsize)

    class ReceiveChannel:

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return await self.receive()
            except ClosedResourceError:
                raise StopAsyncIteration

        async def receive(self):
            item = sentinel
            while item == sentinel:
                if not senders and receive_queue.empty():
                    raise ClosedResourceError
                item = await receive_queue.get()
            if capacity == 0:
                await send_queue.put(None)
            return item

        @classmethod
        def clone(cls):
            return cls()

    class SendChannel:

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            senders.remove(self)
            if not receive_queue.full():
                await receive_queue.put(sentinel)

        async def send(self, item):
            await receive_queue.put(item)
            if capacity == 0:
                await send_queue.get()

        @classmethod
        def clone(cls):
            instance = cls()
            senders.add(instance)
            return instance

    return SendChannel.clone(), ReceiveChannel.clone()
