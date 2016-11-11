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


Synopsis
--------

This library provides a collection of stream operators that can be combined to create
asynchronous pipelines of operations.

It can be seen as an asynchronous version of itertools_, although some aspects are slightly different.
Essentially, all the provided operators return a unified interface called a stream.
A stream is an enhanced asynchronous iterable providing the following features:

- Pipe-lining of operators - using pipe symbol ``|``
- Repeatability - every iteration creates a different iterator
- Safe iteration context - using ``async with`` statement and the ``stream`` method
- Simplified execution - get the last element from a steam using ``await`` statement
- Slicing and indexing - using square brackets ``[]``
- Concatenation - using addition symbol ``+``



Requirements
------------

The stream operators rely heavily on asynchronous generators (`PEP 525`_):

- python >= 3.6


Example
-------

The following example demonstrates most of the streams capabilities:

.. sourcecode:: python

    import asyncio
    from aiostream import stream, pipe


    async def main():

        # Create a counting stream with a 0.2 seconds interval
        xs = stream.count(interval=0.2)

        # Operators can be piped using '|'
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


Operators
---------

Creation operators (non-pipable)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **iterate** ``(it)``:
    Generate values from a synchronous or asynchronous iterable.

- **preserve** ``(ait)``:
    Generate values from an asynchronous iterable without explicitly closing the corresponding iterator.

- **just** ``(value)``:
    Generate a single value.

- **empty** ``()``:
    Terminate without generating any value.

- **throw** ``(exc)``:
    Throw an exception without generating any value.

- **never** ``()``:
    Hang forever without generating any value.

- **repeat** ``(value, times=None, *, interval=0)``:
    Generate the same value a given number of times.

- **range** ``(*args, interval=0)``:
    Generate a given range of numbers.

- **count** ``(start=0, step=1, *, interval=0)``:
    Generate consecutive numbers indefinitely.


Transformation operators
^^^^^^^^^^^^^^^^^^^^^^^^

- **map** ``(source, func, *more_sources)``:
    Apply a given function to the elements of one or several asynchronous sequences.

- **enumerate** ``(source, start=0, step=1)``:
    Generate (index, value) tuples from an asynchronous sequence.

- **starmap** ``(source, func)``:
    Apply a given function to the unpacked elements of an asynchronous sequence.

- **cycle** ``(source)``:
    Iterate indefinitely over an asynchronous sequence.


Selection operators
^^^^^^^^^^^^^^^^^^^

- **take** ``(source, n)``:
    Forward the first n elements from an asynchronous sequence.

- **takelast** ``(source, n)``:
    Forward the last n elements from an asynchronous sequence.

- **skip** ``(source, n)``:
    Forward an asynchronous sequence, skipping the first n elements.

- **skiplast** ``(source, n)``:
    Forward an asynchronous sequence, skipping the last n elements.

- **filterindex** ``(source, func)``:
    Filter an asynchronous sequence using the index of the elements.

- **getitem** ``(source, index)``:
    Forward one or several items from an asynchronous sequence.

- **filter** ``(source, func)``:
    Filter an asynchronous sequence using an arbitrary function.

- **takewhile** ``(source, func)``:
    Forward an asynchronous sequence while a condition is met.

- **dropwhile** ``(source, func)``:
    Discard the elements from an asynchronous sequence while a condition is met.


Combination operators
^^^^^^^^^^^^^^^^^^^^^

- **map** ``(source, func, *more_sources)``:
    Apply a given function to the elements of one or several asynchronous sequences.

- **zip** ``(*sources)``:
    Combine and forward the elements of several asynchronous sequences.

- **merge** ``(*sources)``:
    Merge several asynchronous sequences together.

- **chain** ``(*sources)``:
    Chain asynchronous sequences together, in the order they are given.


Aggregatation operators
^^^^^^^^^^^^^^^^^^^^^^^

- **accumulate** ``(source, func=op.add, initializer=None)``:
    Generate a series of accumulated sums (or other binary function) from an asynchronous sequence.

- **reduce** ``(source, func, initializer=None)``:
    Apply a function of two arguments cumulatively to the items of an asynchronous sequence,
    reducing the sequence to a single value.

- **list** ``()``:
    Generate a single list from an asynchronous sequence.


Timing operators
^^^^^^^^^^^^^^^^

- **spaceout** ``(source, interval)``:
    Make sure the elements of an asynchronous sequence are separated in time by the given interval.

- **timeout** ``(source, timeout)``:
    Raise a time-out if an element of the asynchronous sequence takes too long to arrive.

- **delay** ``(source, delay)``:
    Delay the iteration of an asynchronous sequence.


Misc operators
^^^^^^^^^^^^^^

- **action** ``(source, func)``:
    Perform an action for each element of an asynchronous sequence without modifying it.

- **print** ``(source, template=None, **kwargs)``:
    Print each element of an asynchronous sequence without modifying it.


References
----------

This library is inspired by:

- `PEP 525`_: Asynchronous Generators
- `Rx`_ - Reactive Extensions
- aioreactive_ - Async/await reactive tools for Python 3.5+
- itertools_ - Functions creating iterators for efficient looping


Contact
-------

Vincent Michel: vxgmichel@gmail.com


.. _PEP 525: http://www.python.org/dev/peps/pep-0525/
.. _Rx: http://reactivex.io/
.. _aioreactive: http://github.com/dbrattli/aioreactive
.. _itertools: http://docs.python.org/3/library/itertools.html
