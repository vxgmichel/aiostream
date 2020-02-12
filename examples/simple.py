"""
Example that builds a simple pipeline
"""

import anyio
import argparse
from aiostream import stream, pipe


async def main():
    # This stream computes 11² + 13² in 1.5 second
    xs = (
        stream.count(interval=0.1)      # Count from zero every 0.1 s
        | pipe.skip(10)                 # Skip the first 10 numbers
        | pipe.take(5)                  # Take the following 5
        | pipe.filter(lambda x: x % 2)  # Keep odd numbers
        | pipe.map(lambda x: x ** 2)    # Square the results
        | pipe.accumulate()             # Add the numbers together
    )
    print('11² + 13² = ', await xs)


# Run the main coroutine
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'backend', nargs='?', default='asyncio',
        help="Use one of `trio`, `curio` or `asyncio` (default)")
    namespace = parser.parse_args()
    anyio.run(main, backend=namespace.backend)
