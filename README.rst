aiostream
=========

.. image:: https://img.shields.io/badge/docs-python_hosted-brightgreen.svg
   :target: http://pythonhosted.org/aiostream
   :alt:

.. image:: https://coveralls.io/repos/github/vxgmichel/aiostream/badge.svg?branch=master
   :target: https://coveralls.io/github/vxgmichel/aiostream?branch=master
   :alt:

.. image:: https://travis-ci.org/vxgmichel/aiostream.svg?branch=master
   :target: https://travis-ci.org/vxgmichel/aiostream
   :alt:

.. image:: https://img.shields.io/pypi/v/aiostream.svg
   :target: https://pypi.python.org/pypi/aiostream
   :alt:

.. image:: https://img.shields.io/pypi/pyversions/aiostream.svg
   :target: https://pypi.python.org/pypi/aiostream/
   :alt:

Generator-based operators for asynchronous iteration


Synopsis
--------

aiostream_ provides a collection of stream operators that can be combined to create
asynchronous pipelines of operations.

It can be seen as an asynchronous version of itertools_, although some aspects are slightly different.
Essentially, all the provided operators return a unified interface called a stream.
A stream is an enhanced asynchronous iterable providing the following features:

- **Operator pipe-lining** - using pipe symbol ``|``
- **Repeatability** - every iteration creates a different iterator
- **Safe iteration context** - using ``async with`` and the ``stream`` method
- **Simplified execution** - get the last element from a stream using ``await``
- **Slicing and indexing** - using square brackets ``[]``
- **Concatenation** - using addition symbol ``+``


Requirements
------------

The stream operators rely heavily on asynchronous generators (`PEP 525`_):

- python >= 3.6


Stream operators
----------------

The `stream operators`_ are separated in 7 categories:

+--------------------+--------------------------------------------------------------------------------+
| **creation**       | iterate_, preserve_, just_, empty_, throw_, never_, repeat_, count_, range_    |
+--------------------+--------------------------------------------------------------------------------+
| **transformation** | map_, enumerate_, starmap_, cycle_, chunks_                                    |
+--------------------+--------------------------------------------------------------------------------+
| **selection**      | take_, takelast_, skip_, skiplast_, getitem_, filter_, takewhile_, dropwhile_  |
+--------------------+--------------------------------------------------------------------------------+
| **combination**    | map_, zip_, merge_, chain_                                                     |
+--------------------+--------------------------------------------------------------------------------+
| **aggregation**    | accumulate_, reduce_, list_                                                    |
+--------------------+--------------------------------------------------------------------------------+
| **timing**         | spaceout_, timeout_, delay_                                                    |
+--------------------+--------------------------------------------------------------------------------+
| **miscellaneous**  | action_, print_                                                                |
+--------------------+--------------------------------------------------------------------------------+


Demonstration
-------------

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

More examples are available in the `example section`_ of the documentation.


Contact
-------

Vincent Michel: vxgmichel@gmail.com


.. _aiostream: https://github.com/vxgmichel/aiostream
.. _PEP 525: http://www.python.org/dev/peps/pep-0525/
.. _Rx: http://reactivex.io/
.. _aioreactive: http://github.com/dbrattli/aioreactive
.. _itertools: http://docs.python.org/3/library/itertools.html

.. _stream operators: http://pythonhosted.org/aiostream/operators.html
.. _example section: http://pythonhosted.org/aiostream/examples.html

.. _iterate: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.iterate
.. _preserve: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.preserve
.. _just: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.just
.. _throw: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.throw
.. _empty: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.empty
.. _never: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.never
.. _repeat: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.repeat
.. _range: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.range
.. _count: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.count
.. _map: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.map
.. _enumerate: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.enumerate
.. _starmap: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.starmap
.. _cycle: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.cycle
.. _chunks: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.chunks
.. _take: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.take
.. _takelast: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.takelast
.. _skip: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.skip
.. _skiplast: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.skiplast
.. _getitem: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.getitem
.. _filter: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.filter
.. _dropwhile: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.dropwhile
.. _takewhile: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.takewhile
.. _chain: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.chain
.. _zip: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.zip
.. _merge: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.merge
.. _accumulate: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.accumulate
.. _reduce: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.reduce
.. _list: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.list
.. _spaceout: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.spaceout
.. _delay: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.delay
.. _timeout: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.timeout
.. _action: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.action
.. _print: http://pythonhosted.org/aiostream/operators.html#aiostream.stream.print
