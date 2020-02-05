#!/usr/bin/env python3
"""
Example to demonstrate the main aiostream features
"""

import anyio
import argparse
from aiostream import stream, pipe


async def main():

    # Create a counting stream with a 0.2 seconds interval
    xs = stream.count(interval=0.2)

    # Operators can be piped using '|'
    ys = xs | pipe.map(lambda x: x**2)

    # Streams can be sliced
    zs = ys[1:10:2]

    # Use a stream context for proper resource management
    async with zs.stream() as streamer:

        # Asynchronous iteration
        async for z in streamer:

            # Print 1, 9, 25, 49 and 81
            print('->', z)

    # Streams can be awaited and return the last value
    print('9² = ', await zs)

    # Streams can run several times
    print('9² = ', await zs)

    # Streams can be concatenated
    one_two_three = stream.just(1) + stream.range(2, 4)

    # Print [1, 2, 3]
    print(await stream.list(one_two_three))


# Run the main coroutine
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'backend', nargs='?', default='asyncio',
        help="Use one of `trio`, `curio` or `asyncio` (default)")
    namespace = parser.parse_args()
    anyio.run(main, backend=namespace.backend)
