"""Generator-based operators for asynchronous iteration.

The two main modules are:
- stream: provide all the stream operators (to create new stream objects)
- pipe: provides all the pipe operators (to combine operators using '|')

Additionally, three core objects are exposed:
- streamcontext: a context for safe stream iteration
- StreamEmpty: the exception raised when an empty stream is awaited
- operator: a decorator to create stream operators from async generators

Some utility modules are also provided:
- aiter_utils: utilties for asynchronous iteration
- context_utils: utilites for asynchronous context
- test_utils: utilities for testing stream operators (require pytest)
"""

from . import stream, pipe
from .aiter_utils import async_, await_
from .core import StreamEmpty, operator, pipable_operator, streamcontext

__all__ = [
    "stream",
    "pipe",
    "async_",
    "await_",
    "operator",
    "pipable_operator",
    "streamcontext",
    "StreamEmpty",
]
