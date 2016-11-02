aiostream
=========

.. image:: https://coveralls.io/repos/github/vxgmichel/aiostream/badge.svg?branch=master
    :target: https://coveralls.io/github/vxgmichel/aiostream?branch=master

.. image:: https://travis-ci.org/vxgmichel/aiostream.svg?branch=master
    :target: https://travis-ci.org/vxgmichel/aiostream

Generator-based operators for asynchronous iteration


Requirements
------------

- python 3.6


Example
-------

.. literalinclude:: examples/simple.py


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
  - get_item (index
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
