Stream operators
================

.. module:: aiostream.stream

The stream operators are separated in 7 categories:

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

They can be found in the :mod:`aiostream.stream` module.

Stream vs pipe operators
------------------------

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

**Streams from iterators:**

  .. autoclass:: iterate

  .. autoclass:: preserve

**Basic streams:**

  .. autoclass:: just

  .. autoclass:: empty

  .. autoclass:: throw

  .. autoclass:: never

**Other streams:**

  .. autoclass:: repeat

  .. autoclass:: range

  .. autoclass:: count


Transformation operators
------------------------

.. autoclass:: map

   Note: :class:`map` is considered a combination operator
   if used with extra sources, and a transformation operator otherwise

.. autoclass:: enumerate

.. autoclass:: starmap

.. autoclass:: cycle


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

   Note: :class:`map` is considered a combination operator
   if used with extra sources, and a transformation operator otherwise

.. autoclass:: zip

.. autoclass:: merge

.. autoclass:: chain


Aggregatation operators
-----------------------

.. autoclass:: accumulate

.. autoclass:: reduce

.. autoclass:: list


Timing operators
----------------

.. autoclass:: spaceout

.. autoclass:: timeout

.. autoclass:: delay


Miscellaneous operators
-----------------------

.. autoclass:: action

.. autoclass:: print
