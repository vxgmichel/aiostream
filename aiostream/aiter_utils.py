
import warnings
from collections import AsyncIterator

__all__ = ['aiter', 'anext', '_await',
           'is_async_iterable', 'assert_async_iterable',
           'is_async_iterator', 'assert_async_iterator',
           'AsyncIteratorContext', 'aitercontext']


# Magic method shorcuts

def aiter(obj):
    """Access aiter magic method."""
    assert_async_iterable(obj)
    return obj.__aiter__()


def anext(obj):
    """Access anext magic method."""
    assert_async_iterator(obj)
    return obj.__anext__()


def _await(obj):
    """Access await magic method."""
    return obj.__await__()


# Iterability helpers

def is_async_iterable(obj):
    return hasattr(obj, '__aiter__')


def assert_async_iterable(obj):
    if not is_async_iterable(obj):
        raise TypeError(
            f"{type(obj).__name__!r} object is not async iterable")


def is_async_iterator(obj):
    return hasattr(obj, '__anext__')


def assert_async_iterator(obj):
    if not is_async_iterator(obj):
        raise TypeError(
            f"{type(obj).__name__!r} object is not an async iterator")


# Async iterator context

class AsyncIteratorContext(AsyncIterator):
    """"Asynchronous iterator with context management."""

    _STANDBY = "STANDBY"
    _RUNNING = "RUNNING"
    _FINISHED = "FINISHED"

    def __init__(self, aiterator):
        assert_async_iterator(aiterator)
        if isinstance(aiterator, AsyncIteratorContext):
            raise TypeError(
                f'{aiterator!r} is already an AsyncIteratorContext')
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
