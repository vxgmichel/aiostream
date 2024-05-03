"""Run a TCP server that computes euclidean norm of vectors for its clients.

Run the server:

    $ python3.6 norm_server.py
    Serving on ('127.0.0.1', 8888)

Test using netcat client:

    $ nc localhost 8888
    --------------------------------------
    Compute the Euclidean norm of a vector
    --------------------------------------
    [...]
"""

import math
import asyncio

from aiostream import pipe, stream

# Constants

INSTRUCTIONS = """\
--------------------------------------
Compute the Euclidean norm of a vector
--------------------------------------
Enter each coordinate of the vector on a separate line, and add an empty
line at the end to get the result. Anything else will result in an error.
> """

ERROR = """\
-> Error ! Try again...
"""

RESULT = """\
-> Euclidean norm: {}
"""


# Client handler


async def euclidean_norm_handler(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    # Define lambdas
    def strip(x: bytes, *_: object) -> str:
        return x.decode().strip()

    def nonempty(x: str) -> bool:
        return x != ""

    def to_float(x: str, *_: object) -> float:
        return float(x)

    def square(x: float, *_: object) -> float:
        return x**2

    def write_cursor(_: float) -> None:
        return writer.write(b"> ")

    def square_root(x: float, *_: object) -> float:
        return math.sqrt(x)

    # Create awaitable
    handle_request = (
        stream.iterate(reader)
        | pipe.print("string: {}")
        | pipe.map(strip)
        | pipe.takewhile(nonempty)
        | pipe.map(to_float)
        | pipe.map(square)
        | pipe.print("square: {:.2f}")
        | pipe.action(write_cursor)
        | pipe.accumulate(initializer=0.0)
        | pipe.map(square_root)
        | pipe.print("norm -> {:.2f}")
    )

    # Loop over norm computations
    while not reader.at_eof():
        writer.write(INSTRUCTIONS.encode())
        try:
            result = await handle_request
        except ValueError:
            writer.write(ERROR.encode())
        else:
            writer.write(RESULT.format(result).encode())


# Main function


async def main(bind: str = "127.0.0.1", port: int = 8888) -> None:
    # Start the server
    server = await asyncio.start_server(euclidean_norm_handler, bind, port)

    # Serve requests until Ctrl+C is pressed
    print("Serving on {}".format(server.sockets[0].getsockname()))

    async with server:
        await server.serve_forever()


# Main execution

if __name__ == "__main__":
    asyncio.run(main())
