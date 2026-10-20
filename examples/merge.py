import asyncio

from aiostream import pipe, stream


async def main() -> None:
    # Both sources emit the same values, so label them before merging.
    left = stream.iterate(["ready", "done"])
    right = stream.iterate(["ready", "done"])
    merged = stream.merge(
        left | pipe.map(lambda value, *_: ("left", value)),
        right | pipe.map(lambda value, *_: ("right", value)),
    )

    async with merged.stream() as streamer:
        async for source, value in streamer:
            print(f"{source}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
