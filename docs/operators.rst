Stream operators
================

.. module:: aiostream.stream

The stream operators are separated in 7 categories:

.. include:: table.rst.inc

They can be found in the :mod:`aiostream.stream` module.

Pipe-lining
-----------

Most of the operators have a :meth:`pipe` method corresponding to their equivalent pipe operator.
They are also gathered and accessible through the :mod:`aiostream.pipe` module.
The pipe operators allow a 2-step instanciation.

For instance, the following stream::

  ys = stream.map(xs, lambda x: x**2)

is strictly equivalent to::

  ys = pipe.map(lambda x: x**2)(xs)

and can be written as::

  ys = xs | pipe.map(lambda x: x**2)

This synthax comes in handy when several operators are chained::

  ys = (xs
      | pipe.operator1(*args1)
      | pipe.operator2(*args2)
      | pipe.operator3(*args3))


Creation operators
------------------

.. note:: Those operators do not have a pipe equivalent.

.. autoclass:: iterate

.. autoclass:: preserve

.. autoclass:: just

.. autoclass:: call

.. autoclass:: empty

.. autoclass:: throw

.. autoclass:: never

.. autoclass:: repeat

.. autoclass:: range

.. autoclass:: count


Transformation operators
------------------------

.. autoclass:: map

   .. note:: :class:`map` is considered a combination operator
	     if used with extra sources, and a transformation operator otherwise

.. autoclass:: enumerate

.. autoclass:: starmap

.. autoclass:: cycle

.. autoclass:: chunks

Selection operators
-------------------

.. autoclass:: take

.. autoclass:: takelast

.. autoclass:: skip

.. autoclass:: skiplast

.. autoclass:: getitem

.. autoclass:: filter

.. autoclass:: takewhile

.. autoclass:: dropwhile

Combination operators
---------------------

.. autoclass:: map

   .. note:: :class:`map` is considered a combination operator
	     if used with extra sources, and a transformation operator otherwise

.. autoclass:: zip

.. autoclass:: merge

.. autoclass:: chain

.. autoclass:: ziplatest


Aggregatation operators
-----------------------

.. autoclass:: accumulate

.. autoclass:: reduce

.. autoclass:: list


Advanced operators
------------------

.. note:: The :class:`concat`, :class:`flatten` and :class:`switch` operators
   all take a **stream of streams** as an argument (also called **stream of
   higher order**) and return a flattened stream using their own merging
   strategy.

.. autoclass:: concat

.. autoclass:: flatten

.. autoclass:: switch

.. note:: The :class:`concatmap`, :class:`flatmap` and :class:`switchmap` operators
   provide a simpler access to the three merging strategy listed above.

.. autoclass:: concatmap

.. autoclass:: flatmap

.. autoclass:: switchmap


Timing operators
----------------

.. autoclass:: spaceout

.. autoclass:: timeout

.. autoclass:: delay


Miscellaneous operators
-----------------------

.. autoclass:: action

.. autoclass:: print
