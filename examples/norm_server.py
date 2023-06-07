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

import asyncio
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
    def strip(x):
        return x.decode().strip()

    def nonempty(x):
        return x != ""

    def square(x):
        return x**2

    def write_cursor(x):
        return writer.write(b"> ")

    def square_root(x):
        return x**0.5

    # Create awaitable
    handle_request = (
        stream.iterate(reader)
        | pipe.print("string: {}")
        | pipe.map(strip)
        | pipe.takewhile(nonempty)
        | pipe.map(float)
        | pipe.map(square)
        | pipe.print("square: {:.2f}")
        | pipe.action(write_cursor)
        | pipe.accumulate(initializer=0)
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


def run_server(bind="127.0.0.1", port=8888):
    # Start the server
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(euclidean_norm_handler, bind, port)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print("Serving on {}".format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


# Main execution

if __name__ == "__main__":
    run_server()
