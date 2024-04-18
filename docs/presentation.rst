Presentation
============

aiostream_ provides a collection of `stream operators <operators.html>`_ that can be combined to create
asynchronous pipelines of operations.

It can be seen as an asynchronous version of itertools_, although some aspects are slightly different.
Essentially, all the provided operators return a unified interface called a `stream <core.html#stream-base-class>`_.
A stream is an enhanced asynchronous iterable providing the following features:

  - **Operator pipe-lining** - using pipe symbol ``|``
  - **Repeatability** - every iteration creates a different iterator
  - **Safe iteration context** - using ``async with`` and the ``stream`` method
  - **Simplified execution** - get the last element from a stream using ``await``
  - **Slicing and indexing** - using square brackets ``[]``
  - **Concatenation** - using addition symbol ``+``


Stream operators
----------------

.. module:: aiostream.stream

The `stream operators <operators.html>`_ are separated in 7 categories:

.. include:: table.rst.inc


Demonstration
-------------

The following example demonstrates most of the streams capabilities:

.. literalinclude:: ../examples/demo.py

More examples are available in the `example section <examples.html>`_.


References
----------

This library is inspired by:

- `PEP 525`_: Asynchronous Generators
- `Rx`_ - Reactive Extensions
- aioreactive_ - Async/await reactive tools for Python 3.5+
- itertools_ - Functions creating iterators for efficient looping


.. _aiostream: https://github.com/vxgmichel/aiostream
.. _PEP 525: http://www.python.org/dev/peps/pep-0525/
.. _Rx: http://reactivex.io/
.. _aioreactive: http://github.com/dbrattli/aioreactive
.. _itertools: http://docs.python.org/3/library/itertools.html
