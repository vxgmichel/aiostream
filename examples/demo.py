import asyncio
from aiostream import stream, pipe


async def main():

    # Create a counting stream with a 0.2 second interval
    xs = stream.count(interval=0.2)

    # Pipe operators using '|'
    ys = xs | pipe.map(lambda x: x**2)

    # Streams can be sliced
    zs = ys[1:10:2]

    # Use a stream context for proper resource management
    async with zs.stream() as streamer:

        # Asynchronous iteration
        async for z in streamer:

            # Prints 1, 9, 25, 49, 81
            print('->', z)

    # Streams can be awaited and return the last value
    print('9² = ', await zs)

    # Streams can run several times
    print('9² = ', await zs)


# Run main coroutine
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
