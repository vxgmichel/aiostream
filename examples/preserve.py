import asyncio
from typing import AsyncIterator

from aiostream import operator, stream


async def main() -> None:
    async def agen() -> AsyncIterator[int]:
        yield 1
        yield 2
        yield 3

    # The xs stream does not preserve the generator
    xs = stream.iterate(agen())
    print(await xs[0])  # Print 1
    print(await stream.list(xs))  # Print [] (2 and 3 have never yielded)

    # The xs stream does preserve the generator
    xs = stream.preserve(agen())
    print(await xs[0])  # Print 1
    print(await stream.list(xs))  # Print [2, 3]

    # Transform agen into a stream operator
    agen_stream = operator(agen)
    xs = agen_stream()  # agen is now reusable
    print(await stream.list(xs))  # Print [1, 2, 3]
    print(await stream.list(xs))  # Print [1, 2, 3]


# Run main coroutine
asyncio.run(main())
