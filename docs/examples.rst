.. _example section:

Examples
========

Demonstration
-------------

The following example demonstrates most of the streams capabilities:

.. literalinclude:: ../examples/demo.py


Simple computation
------------------

This simple example computes ``11² + 13²`` in 1.5 second:

.. literalinclude:: ../examples/simple.py


Preserve a generator
--------------------

This example shows how to preserve an async generator from being closed
by the iteration context:

.. literalinclude:: ../examples/preserve.py


Norm server
-----------

The next example runs a TCP server that computes the euclidean norm of vectors for its clients.

Run the server:

.. sourcecode:: console

    $ python3.6 norm_server.py
    Serving on ('127.0.0.1', 8888)

Test using a netcat client:

.. sourcecode:: console

    $ nc localhost 8888
    --------------------------------------
    Compute the Euclidean norm of a vector
    --------------------------------------
    [...]

Check the logs on the server side, and see how the computation is performed on the fly.

.. literalinclude:: ../examples/norm_server.py
   :lines: 17-


Extra operators
---------------

This example shows how extra operators can be created and combined with others:

.. literalinclude:: ../examples/extra.py
