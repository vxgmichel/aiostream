import asyncio
from aiostream import stream, pipe

# This awaitable computes 11² + 13² in 1.5 second
observable = (
    stream.count(interval=0.1)         # Count from zero every 0.1 s
    | pipe.skip(10)                    # Skip the first 10 numbers
    | pipe.take(5)                     # Take the following 5
    | pipe.filter(lambda x: x % 2)     # Keep odd numbers
    | pipe.map(lambda x: x ** 2)       # Square the results
    | pipe.reduce(lambda x, y: x + y)  # Add the numbers together
)


# Run the awaitable
loop = asyncio.get_event_loop()
result = loop.run_until_complete(observable)
print('11² + 13² = ', result)

# Can run several times
result = loop.run_until_complete(observable)
print('11² + 13² = ', result)

# Clean up
loop.close()
