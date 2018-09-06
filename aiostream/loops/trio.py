import trio
import inspect

class Trio:
    @staticmethod
    async def sleep_forever():
        await trio.sleep_forever()

    @staticmethod
    async def sleep(time):
        await trio.sleep(time)

    @staticmethod
    def time():
        return trio.current_time()

    @staticmethod
    def iscoroutinefunction(f):
        return inspect.iscoroutinefunction(f)

    @staticmethod
    async def gather(*async_fns):
        results = [None] * len(async_fns)

        async def run_one(i, async_fn):
            results[i] = await async_fn()

        async with trio.open_nursery() as nursery:
            for i, async_fn in enumerate(async_fns):
                nursery.start_soon(run_one, i, async_fn)

        return results

    @staticmethod
    async def wait_for_with_timeout(fn, timeout):
        with trio.fail_after(timeout):
            return await fn()