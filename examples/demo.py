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


# Run main coroutine
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
