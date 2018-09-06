import asyncio


class AsyncIO:
    @staticmethod
    async def sleep_forever():
        future = asyncio.Future()
        try:
            await future
        finally:
            future.cancel()

    @staticmethod
    async def sleep(time):
        await asyncio.sleep(time)

    @staticmethod
    def time():
        return asyncio.get_event_loop().time()

    @staticmethod
    def iscoroutinefunction(f):
        return asyncio.iscoroutinefunction(f)

    @staticmethod
    async def gather(*async_fns):
        return await asyncio.gather(*[f() for f in async_fns])

    @staticmethod
    async def wait_for_with_timeout(fn, timeout):
        return await asyncio.wait_for(fn(), timeout)