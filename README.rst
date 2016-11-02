aiostream
=========

.. image:: https://coveralls.io/repos/github/vxgmichel/aiostream/badge.svg?branch=master
    :target: https://coveralls.io/github/vxgmichel/aiostream?branch=master

.. image:: https://travis-ci.org/vxgmichel/aiostream.svg?branch=master
    :target: https://travis-ci.org/vxgmichel/aiostream

.. image:: https://img.shields.io/pypi/v/aiostream.svg
    :target: https://pypi.python.org/pypi/aiostream

.. image:: https://img.shields.io/pypi/pyversions/aiostream.svg
    :target: https://pypi.python.org/pypi/aiostream/

Generator-based operators for asynchronous iteration


Requirements
------------

- python 3.6


Example
-------

.. sourcecode:: python

    import asyncio
    from aiostream import stream, pipe

    # This stream computes 11² + 13² in 1.5 second
    xs = (
        stream.count(interval=0.1)         # Count from zero every 0.1 s
        | pipe.skip(10)                    # Skip the first 10 numbers
        | pipe.take(5)                     # Take the following 5
        | pipe.filter(lambda x: x % 2)     # Keep odd numbers
        | pipe.map(lambda x: x ** 2)       # Square the results
        | pipe.reduce(lambda x, y: x + y)  # Add the numbers together
    )

    # The stream can be awaited
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(xs)
    print('11² + 13² = ', result)

    # The stream can run several times
    result = loop.run_until_complete(xs)
    print('11² + 13² = ', result)

    # Clean up
    loop.close()



Operators
---------

- create operators (non-pipable):
    - iterate
    - just
    - empty
    - throw
    - never
    - repeat
    - range
    - count

- transform operators:
    - map
    - enumerate
    - starmap
    - cycle

- select operators:
    - take
    - take_last
    - skip
    - skip_last
    - filter_index
    - slice
    - item_at
    - get_item
    - filter
    - dropwhile
    - takewhile

- combine operators:
    - map
    - zip
    - merge
    - chain

- aggregate operators:
    - accumulate
    - reduce
    - to_list

- timing operators:
    - space_out
    - timeout

- misc operators:
    - action
    - print
