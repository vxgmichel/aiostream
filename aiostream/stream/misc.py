"""Extra operators."""
import asyncio
import builtins

from .transform import map
from ..core import operator

__all__ = ['action', 'print']


@operator(pipable=True)
def action(source, func):
    """Perform an action for each element of an asynchronous sequence
    without modifying it.

    The given function can be synchronous or asynchronous.
    """
    if asyncio.iscoroutinefunction(func):
        async def innerfunc(arg):
            await func(arg)
            return arg
    else:
        def innerfunc(arg):
            func(arg)
            return arg
    return map.raw(source, innerfunc)


@operator(pipable=True)
def print(source, template=None, **kwargs):
    """Print each element of an asynchronous sequence without modifying it.

    An optional template can be provided to be formatted with the elements.
    All the keyword arguments are forwarded to the builtin function print.
    """
    def func(value):
        if template:
            value = template.format(value)
        builtins.print(value, **kwargs)
    return action.raw(source, func)
