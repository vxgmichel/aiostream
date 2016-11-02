import asyncio
from aiostream import stream, pipe

# This stream computes 11² + 13² in 1.5 second
xs = (
    stream.count(interval=0.1)         # Count from zero every 0.1 s
    | pipe.skip(10)                    # Skip the first 10 numbers
    | pipe.take(5)                     # Take the following 5
    | pipe.filter(lambda x: x % 2)     # Keep odd numbers
    | pipe.map(lambda x: x ** 2)       # Square the results
    | pipe.reduce(lambda x, y: x + y)  # Add the numbers together
)

# The stream can be awaited
loop = asyncio.get_event_loop()
result = loop.run_until_complete(xs)
print('11² + 13² = ', result)

# The stream can run several times
result = loop.run_until_complete(xs)
print('11² + 13² = ', result)

# Clean up
loop.close()
