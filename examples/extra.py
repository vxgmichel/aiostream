import asyncio
import random as random_module

from aiostream import operator, pipe, streamcontext


@operator
async def random(offset=0.0, width=1.0, interval=0.1):
    """Generate a stream of random numbers."""
    while True:
        await asyncio.sleep(interval)
        yield offset + width * random_module.random()


@operator(pipable=True)
async def power(source, exponent):
    """Raise the elements of an asynchronous sequence to the given power."""
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield item ** exponent


@operator(pipable=True)
def square(source):
    """Square the elements of an asynchronous sequence."""
    return power.raw(source, 2)


async def main():
    xs = (
        random()  # Stream random numbers
        | square.pipe()  # Square the values
        | pipe.take(5)  # Take the first five
        | pipe.accumulate()
    )  # Sum the values
    print(await xs)


# Run main coroutine
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
