import asyncio

from aiostream import pipe, stream


def square(x: int, *_: int) -> int:
    return x**2


async def main() -> None:
    # Create a counting stream with a 0.2 seconds interval
    xs = stream.count(interval=0.2)

    # Operators can be piped using '|'
    ys = xs | pipe.map(square)

    # Streams can be sliced
    zs = ys[1:10:2]

    # Use a stream context for proper resource management
    async with zs.stream() as streamer:
        # Asynchronous iteration
        async for z in streamer:
            # Print 1, 9, 25, 49 and 81
            print("->", z)

    # Streams can be awaited and return the last value
    print("9² = ", await zs)

    # Streams can run several times
    print("9² = ", await zs)

    # Streams can be concatenated
    one_two_three = stream.just(1) + stream.range(2, 4)

    # Print [1, 2, 3]
    print(await stream.list(one_two_three))


# Run main coroutine
asyncio.run(main())
