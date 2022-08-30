import asyncio
from aiostream import stream, pipe


async def main():
    # This stream computes 11² + 13² in 1.5 second
    xs = (
        stream.count(interval=0.1)  # Count from zero every 0.1 s
        | pipe.skip(10)  # Skip the first 10 numbers
        | pipe.take(5)  # Take the following 5
        | pipe.filter(lambda x: x % 2)  # Keep odd numbers
        | pipe.map(lambda x: x**2)  # Square the results
        | pipe.accumulate()  # Add the numbers together
    )
    print("11² + 13² = ", await xs)


# Run main coroutine
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
