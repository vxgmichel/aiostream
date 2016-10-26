
from .context import acontextmanager, AsyncExitStack

__all__ = [
    'acontextmanager', 'AsyncExitStack'
    'aiter', 'anext', '_await', 'aitercontext']


# Magic method shorcuts

def aiter(obj):
    """Access aiter magic method."""
    return obj.__aiter__()


def anext(obj):
    """Access anext magic method."""
    return obj.__anext__()


def _await(obj):
    """Access await magic method."""
    return obj.__await__()


# Aiter helpers

def aitercontext(obj):
    """Return an async context manager from an aiterable,
    whether the corresponding aiterator supports it or not."""
    ait = aiter(obj)
    try:
        ait.__enter__
    except AttributeError:
        return acontextmanager.empty(ait)
    else:
        return ait
