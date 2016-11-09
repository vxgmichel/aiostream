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


Operators
---------

Creation operators (non-pipable)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- `iterate(it)`: Generate values from a synchronous or asychronous iterable.
- `preserve(ait)`: Generate values from an asynchronous iterable without explicitely closing
  the corresponding iterator.
- `just(value)`: Generate a single value.
- `empty()`: Terminate without generating any value.
- `throw(exc)`: Throw an exception without generating any value.
- `never()`: Hang forever without generating any value.
- `repeat(value, times=None, *, interval=0)`: Generate the same value a given number of times.
- `range(*args, interval=0)`: Generate a given range of numbers.
- `count(start=0, step=1, *, interval=0)`: Generate consecutive numbers indefinitely.


Transformation operators
^^^^^^^^^^^^^^^^^^^^^^^^

- `map(source, func, *more_sources)`: Apply a given function to the elements of one or several
  asynchronous sequences.
- `enumerate(source, start=0, step=1)`: Generate (index, value) tuples from an asynchronous sequence.
- `starmap(source, func)`: Apply a given function to the unpacked elements of an asynchronous sequence.
- `cycle(source)`: Iterate indefinitely over an asynchronous sequence.


Selection operators
^^^^^^^^^^^^^^^^^^^

- `take(source, n)`: Forward the first n elements from an asynchronous sequence.
- `take_last(source, n)`: Forward the last n elements from an asynchronous sequence.
- `skip(source, n)`: Forward an asynchronous sequence, skipping the first n elements.
- `skip_last(source, n)`: Forward an asynchronous sequence, skipping the last n elements.
- `filter_index(source, func)`: Filter an asynchronous sequence using the index of the elements.
- `slice(source, *args)`: Slice an asynchronous sequence.
- `item_at(source, index)`: Forward the nth element of an asynchronous sequence.
- `get_item(source, index)`: Forward one or several items from an asynchronous sequence.
- `filter(source, func)`: Filter an asynchronous sequence using an arbitrary function.
- `takewhile(source, func)`: Forward an asynchronous sequence while a condition is met.
- `dropwhile(source, func)`: Discard the elements from an asynchronous sequence while a condition is met.


Combination operators
^^^^^^^^^^^^^^^^^^^^^

- `map(source, func, *more_sources)`: Apply a given function to the elements of one or several
  asynchronous sequences.
- `zip(*sources)`: Combine and forward the elements of several asynchronous sequences.
- `merge(*sources)`: Merge several asynchronous sequences together.
- `chain(*sources)`: Chain asynchronous sequences together, in the order they are given.


Aggregatation operators
^^^^^^^^^^^^^^^^^^^^^^^

- `accumulate(source, func=op.add, initializer=None)`: Generate a series of accumulated sums
  (or other binary function) from an asynchronous sequence.
- `reduce(source, func, initializer=None)`: Apply a function of two arguments cumulatively to the items of
  an asynchronous sequence, from left to right, so as to reduce the sequence to a single value.
- `to_list()`: Generate a single list from an asynchronous sequence.


Timing operators
^^^^^^^^^^^^^^^^

- `space_out(source, interval)`: Make sure the elements of an asynchronous sequence are separated in time
  by the given interval.
- `timeout(source, timeout)`: Raise a timeout if an element of the asynchronous sequence takes too long to arrive.
- `delay(source, delay`: Delay the iteration of an asynchrnous sequence.


Misc operators
^^^^^^^^^^^^^^

- `action(source, func)`: Perform an action for each element of an asyncronous sequence,
  and forward this element without modifying it.
- `print(source, template=None, **kwargs)`: Print each element of an asynchronous sequence without modifying it.
