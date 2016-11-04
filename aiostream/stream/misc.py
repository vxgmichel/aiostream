
import asyncio
import builtins

from .transform import map
from ..core import operator

__all__ = ['action', 'print']


@operator(pipable=True)
def action(source, func):
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
    def func(value):
        if template:
            value = template.format(value)
        builtins.print(value, **kwargs)
    return action.raw(source, func)
