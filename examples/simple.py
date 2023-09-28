import asyncio

from aiostream import pipe, stream


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
asyncio.run(main())
