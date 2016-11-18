"""Utilities for asynchronous iteration."""

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
    """Check if the given object is an asynchronous iterable."""
    return hasattr(obj, '__aiter__')


def assert_async_iterable(obj):
    """Raise a TypeError if the given object is not an
    asynchronous iterable.
    """
    if not is_async_iterable(obj):
        raise TypeError(
            f"{type(obj).__name__!r} object is not async iterable")


def is_async_iterator(obj):
    """Check if the given object is an asynchronous iterator."""
    return hasattr(obj, '__anext__')


def assert_async_iterator(obj):
    """Raise a TypeError if the given object is not an
    asynchronous iterator.
    """
    if not is_async_iterator(obj):
        raise TypeError(
            f"{type(obj).__name__!r} object is not an async iterator")


# Async iterator context

class AsyncIteratorContext(AsyncIterator):
    """Asynchronous iterator with context management.

    The context management makes sure the aclose asynchronous method
    of the corresponding iterator has run before it exits. It also issues
    warnings and RuntimeError if it is used incorrectly.

    Correct usage::

        ait = some_asynchronous_iterable()
        aitcontext = AsyncIteratorContext(ait)
        async with ait context:
            async for item in ait:
                <block>

    It is nonetheless not meant to use directly.
    Prefer aitercontext helper instead.
    """

    _STANDBY = "STANDBY"
    _RUNNING = "RUNNING"
    _FINISHED = "FINISHED"

    def __init__(self, aiterator):
        """Initialize with an asynchrnous iterator."""
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
    """Return an asynchronous context manager from an asynchronous iterable.

    The context management makes sure the aclose asynchronous method
    has run before it exits. It also issues warnings and RuntimeError
    if it is used incorrectly.

    It is safe to use with any asynchronous iterable and prevent
    asynchronous iterator context to be wrapped twice.

    Correct usage::

        ait = some_asynchronous_iterable()
        async with aitercontext(ait) as safe_ait:
            async for item in safe_ait:
                <block>

    An optional subclass of AsyncIteratorContext can be provided.
    This class will be used to wrap the given iterable.
    """
    assert issubclass(cls, AsyncIteratorContext)
    aiterator = aiter(aiterable)
    if isinstance(aiterator, cls):
        return aiterator
    return cls(aiterator)
