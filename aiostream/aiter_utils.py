
import warnings
from collections import AsyncIterator

__all__ = ['aiter', 'anext', '_await',
           'AsyncIteratorContext', 'aitercontext']


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


# Async iterator context

class AsyncIteratorContext(AsyncIterator):
    """"Asynchronous iterator with context management."""

    _STANDBY = "STANDBY"
    _RUNNING = "RUNNING"
    _FINISHED = "FINISHED"

    def __init__(self, aiterator):
        if not isinstance(aiterator, AsyncIterator):
            raise TypeError('Expected an AsyncIterator')
        if isinstance(aiterator, AsyncIteratorContext):
            raise TypeError('Already an AsyncIteratorContext')
        self._state = self._STANDBY
        self._aiterator = aiterator

    def __aiter__(self):
        return self

    def __anext__(self):
        if self._state == self._FINISHED:
            raise RuntimeError(
                "AsyncIteratorContext is closed and cannot be iterated")
        if self._state == self._STANDBY:
            warnings.warn(
                "AsyncIteratorContext is iterated outside of its context")
        return anext(self._aiterator)

    async def __aenter__(self):
        if self._state == self._FINISHED:
            raise RuntimeError(
                "AsyncIteratorContext is closed and cannot be iterated")
        self._state = self._RUNNING
        return self

    async def __aexit__(self, *args):
        try:
            if self._state != self._FINISHED and \
               hasattr(self._aiterator, 'aclose'):
                await self._aiterator.aclose()
        finally:
            self._state = self._FINISHED


def aitercontext(aiterable, *, cls=AsyncIteratorContext):
    """Return an async context manager from an aiterable."""
    aiterator = aiter(aiterable)
    if isinstance(aiterator, cls):
        return aiterator
    return cls(aiterator)
