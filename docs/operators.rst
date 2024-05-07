Stream operators
================

.. module:: aiostream.stream

The stream operators produce objects of
the `Stream <core.html#stream-base-class>`_ class.

They are separated in 7 categories:

.. include:: table.rst.inc

They can be found in the :mod:`aiostream.stream` module.

Custom stream operators can be created using the `@operator <core.html#operator-decorator>`_ decorator.


Pipe-lining
-----------

Most of the operators have a :meth:`pipe` method corresponding to their equivalent pipe operator.
They are also gathered and accessible through the :mod:`aiostream.pipe` module.
The pipe operators allow a 2-step instantiation.

For instance, the following stream::

  ys = stream.map(xs, lambda x: x**2)

is strictly equivalent to::

  ys = pipe.map(lambda x: x**2)(xs)

and can be written as::

  ys = xs | pipe.map(lambda x: x**2)

This syntax comes in handy when several operators are chained::

  ys = (xs
      | pipe.operator1(*args1)
      | pipe.operator2(*args2)
      | pipe.operator3(*args3))


Creation operators
------------------

.. note:: Those operators do not have a pipe equivalent.

.. autofunction:: iterate

.. autofunction:: preserve

.. autofunction:: just

.. autofunction:: call

.. autofunction:: empty

.. autofunction:: throw

.. autofunction:: never

.. autofunction:: repeat

.. autofunction:: range

.. autofunction:: count


Transformation operators
------------------------

.. autofunction:: map

   .. note:: :class:`map` is considered a combination operator
	     if used with extra sources, and a transformation operator otherwise

.. autofunction:: enumerate

.. autofunction:: starmap

.. autofunction:: cycle

.. autofunction:: chunks

Selection operators
-------------------

.. autofunction:: take

.. autofunction:: takelast

.. autofunction:: skip

.. autofunction:: skiplast

.. autofunction:: getitem

.. autofunction:: filter

.. autofunction:: until

.. autofunction:: takewhile

.. autofunction:: dropwhile

Combination operators
---------------------

.. autofunction:: map

   .. note:: :class:`map` is considered a combination operator
	     if used with extra sources, and a transformation operator otherwise

.. autofunction:: zip

.. autofunction:: merge

.. autofunction:: chain

.. autofunction:: ziplatest


Aggregatation operators
-----------------------

.. autofunction:: accumulate

.. autofunction:: reduce

.. autofunction:: list


Advanced operators
------------------

.. note:: The :class:`concat`, :class:`flatten` and :class:`switch` operators
   all take a **stream of streams** as an argument (also called **stream of
   higher order**) and return a flattened stream using their own merging
   strategy.

.. autofunction:: concat

.. autofunction:: flatten

.. autofunction:: switch

.. note:: The :class:`concatmap`, :class:`flatmap` and :class:`switchmap` operators
   provide a simpler access to the three merging strategy listed above.

.. autofunction:: concatmap

.. autofunction:: flatmap

.. autofunction:: switchmap


Timing operators
----------------

.. autofunction:: spaceout

.. autofunction:: timeout

.. autofunction:: delay


Miscellaneous operators
-----------------------

.. autofunction:: action

.. autofunction:: print
