import asyncio
import random as random_module
from typing import AsyncIterable, AsyncIterator

from aiostream import operator, pipable_operator, pipe, streamcontext


@operator
async def random(
    offset: float = 0.0, width: float = 1.0, interval: float = 0.1
) -> AsyncIterator[float]:
    """Generate a stream of random numbers."""
    while True:
        await asyncio.sleep(interval)
        yield offset + width * random_module.random()


@pipable_operator
async def power(
    source: AsyncIterable[float], exponent: float | int
) -> AsyncIterator[float]:
    """Raise the elements of an asynchronous sequence to the given power."""
    async with streamcontext(source) as streamer:
        async for item in streamer:
            yield item**exponent


@pipable_operator
def square(source: AsyncIterable[float]) -> AsyncIterator[float]:
    """Square the elements of an asynchronous sequence."""
    return power.raw(source, 2)


async def main() -> None:
    xs = (
        random()  # Stream random numbers
        | square.pipe()  # Square the values
        | pipe.take(5)  # Take the first five
        | pipe.accumulate()
    )  # Sum the values
    print(await xs)


# Run main coroutine
asyncio.run(main())
