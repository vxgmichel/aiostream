Presentation
============

:ref:`aiostream` provides a collection of stream operators that can be combined to create
asynchronous pipelines of operations.

It can be seen as an asynchronous version of itertools_, although some aspects are slightly different.
Essentially, all the provided operators return a unified interface called a stream.
A stream is an enhanced asynchronous iterable providing the following features:

  - **Operator pipe-lining** - using pipe symbol ``|``
  - **Repeatability** - every iteration creates a different iterator
  - **Safe iteration context** - using ``async with`` and the ``stream`` method
  - **Simplified execution** - get the last element from a steam using ``await``
  - **Slicing and indexing** - using square brackets ``[]``
  - **Concatenation** - using addition symbol ``+``


Requirements
------------

The stream operators rely heavily on asynchronous generators (`PEP 525`_):

- python >= 3.6


Demonstration
-------------

The following example demonstrates most of the streams capabilities:

.. literalinclude:: ../examples/demo.py


Stream operators
----------------

.. module:: aiostream.stream

The `stream operators <operators.html>`_ are separated in 7 categories:

+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| **creation**       | :class:`iterate`, :class:`preserve`, :class:`just`, :class:`empty`, :class:`throw`, :class:`never`, :class:`repeat`, :class:`count`, :class:`range` |
+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| **transformation** | :class:`map`, :class:`enumerate`, :class:`starmap`, :class:`cycle`                                                                                  |
+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| **selection**      | :class:`take`, :class:`takelast`, :class:`skip`, :class:`skiplast`, :class:`getitem`, :class:`filter`, :class:`takewhile`, :class:`dropwhile`       |
+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| **combination**    | :class:`map`, :class:`zip`, :class:`merge`, :class:`chain`                                                                                          |
+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| **aggregation**    | :class:`accumulate`, :class:`reduce`, :class:`list`                                                                                                 |
+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| **timing**         | :class:`spaceout`, :class:`timeout`, :class:`delay`                                                                                                 |
+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+
| **miscellaneous**  | :class:`action`, :class:`print`                                                                                                                     |
+--------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------+


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
