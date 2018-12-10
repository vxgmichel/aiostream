from asyncio import iscoroutinefunction


import anyio
from anyio import sleep, fail_after, create_task_group, create_semaphore


__all__ = ['iscoroutinefunction', 'time', 'sleep_forever',
           'sleep', 'fail_after', 'create_task_group', 'create_semaphore']


async def sleep_forever():
    while True:
        # Sleep for a day
        await anyio.sleep(60 * 60 * 24)


async def time():
    asynclib = anyio._detect_running_asynclib()
    if asynclib == 'asyncio':
        import asyncio
        return asyncio.get_running_loop().time()
    if asynclib == 'trio':
        import trio
        return trio.current_time()
    if asynclib == 'curio':
        import curio
        return await curio.clock()
    raise RuntimeError("Asynclib detection failed")
