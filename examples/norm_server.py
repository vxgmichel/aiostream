#!/usr/bin/env python3
"""Run a TCP server that computes euclidean norm of vectors for its clients.

Run the server:

    $ ./norm_server.py
    Serving on ('127.0.0.1', 8888)

Test using netcat client:

    $ nc localhost 8888
    --------------------------------------
    Compute the Euclidean norm of a vector
    --------------------------------------
    [...]
"""

import asyncio
import argparse
from aiostream import stream, pipe

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

async def euclidean_norm_handler(reader, writer):

    # Define lambdas
    strip = lambda x: x.decode().strip()
    nonempty = lambda x: x != ''
    square = lambda x: x ** 2
    write_cursor = lambda x: writer.write(b'> ')
    square_root = lambda x: x ** 0.5

    # Create awaitable
    handle_request = (
        stream.iterate(reader)
        | pipe.print('string: {}')
        | pipe.map(strip)
        | pipe.takewhile(nonempty)
        | pipe.map(float)
        | pipe.map(square)
        | pipe.print('square: {:.2f}')
        | pipe.action(write_cursor)
        | pipe.accumulate(initializer=0)
        | pipe.map(square_root)
        | pipe.print('norm -> {:.2f}')
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

async def main(bind="localhost", port=8888):
    server = await asyncio.start_server(euclidean_norm_handler, bind, port)
    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


# Main execution

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--bind", default="localhost", help="bind address (default: localhost)")
    parser.add_argument(
        "--port", default=8888, help="socket port (default: 8888)")
    namespace = parser.parse_args()
    asyncio.run(main(namespace.bind, namespace.port))
