"""Utilities for asynchronous iteration."""

import warnings
import functools
from collections.abc import AsyncIterator

try:
    from contextlib import AsyncExitStack
except ImportError:  # pragma: no cover
    from async_exit_stack import AsyncExitStack

__all__ = [
    "aiter",
    "anext",
    "await_",
    "async_",
    "is_async_iterable",
    "assert_async_iterable",
    "is_async_iterator",
    "assert_async_iterator",
    "AsyncIteratorContext",
    "aitercontext",
    "AsyncExitStack",
]


# Magic method shorcuts


def aiter(obj):
    """Access aiter magic method."""
    assert_async_iterable(obj)
    return obj.__aiter__()


def anext(obj):
    """Access anext magic method."""
    assert_async_iterator(obj)
    return obj.__anext__()


# Async / await helper functions


async def await_(obj):
    """Identity coroutine function."""
    return await obj


def async_(fn):
    """Wrap the given function into a coroutine function."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        return await fn(*args, **kwargs)

    return wrapper


# Iterability helpers


def is_async_iterable(obj):
    """Check if the given object is an asynchronous iterable."""
    return hasattr(obj, "__aiter__")


def assert_async_iterable(obj):
    """Raise a TypeError if the given object is not an
    asynchronous iterable.
    """
    if not is_async_iterable(obj):
        raise TypeError(f"{type(obj).__name__!r} object is not async iterable")


def is_async_iterator(obj):
    """Check if the given object is an asynchronous iterator."""
    return hasattr(obj, "__anext__")


def assert_async_iterator(obj):
    """Raise a TypeError if the given object is not an
    asynchronous iterator.
    """
    if not is_async_iterator(obj):
        raise TypeError(f"{type(obj).__name__!r} object is not an async iterator")


# Async iterator context


class AsyncIteratorContext(AsyncIterator):
    """Asynchronous iterator with context management.

    The context management makes sure the aclose asynchronous method
    of the corresponding iterator has run before it exits. It also issues
    warnings and RuntimeError if it is used incorrectly.

    Correct usage::

        ait = some_asynchronous_iterable()
        async with AsyncIteratorContext(ait) as safe_ait:
            async for item in safe_ait:
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
            raise TypeError(f"{aiterator!r} is already an AsyncIteratorContext")
        self._state = self._STANDBY
        self._aiterator = aiterator

    def __aiter__(self):
        return self

    def __anext__(self):
        if self._state == self._FINISHED:
            raise RuntimeError(
                f"{type(self).__name__} is closed and cannot be iterated"
            )
        if self._state == self._STANDBY:
            warnings.warn(
                f"{type(self).__name__} is iterated outside of its context",
                stacklevel=2,
            )
        return anext(self._aiterator)

    async def __aenter__(self):
        if self._state == self._RUNNING:
            raise RuntimeError(f"{type(self).__name__} has already been entered")
        if self._state == self._FINISHED:
            raise RuntimeError(
                f"{type(self).__name__} is closed and cannot be iterated"
            )
        self._state = self._RUNNING
        return self

    async def __aexit__(self, typ, value, traceback):
        try:
            if self._state == self._FINISHED:
                return False
            try:

                # No exception to throw
                if typ is None:
                    return False

                # Prevent GeneratorExit from being silenced
                if typ is GeneratorExit:
                    return False

                # No method to throw
                if not hasattr(self._aiterator, "athrow"):
                    return False

                # No frame to throw
                if not getattr(self._aiterator, "ag_frame", True):
                    return False

                # Cannot throw at the moment
                if getattr(self._aiterator, "ag_running", False):
                    return False

                # Throw
                try:
                    await self._aiterator.athrow(typ, value, traceback)
                    raise RuntimeError("Async iterator didn't stop after athrow()")

                # Exception has been (most probably) silenced
                except StopAsyncIteration as exc:
                    return exc is not value

                # A (possibly new) exception has been raised
                except BaseException as exc:
                    if exc is value:
                        return False
                    raise
            finally:
                # Look for an aclose method
                aclose = getattr(self._aiterator, "aclose", None)

                # The ag_running attribute has been introduced with python 3.8
                running = getattr(self._aiterator, "ag_running", False)
                closed = not getattr(self._aiterator, "ag_frame", True)

                # A RuntimeError is raised if aiterator is running or closed
                if aclose and not running and not closed:
                    try:
                        await aclose()

                    # Work around bpo-35409
                    except GeneratorExit:
                        pass  # pragma: no cover
        finally:
            self._state = self._FINISHED

    async def aclose(self):
        await self.__aexit__(None, None, None)

    async def athrow(self, exc):
        if self._state == self._FINISHED:
            raise RuntimeError(f"{type(self).__name__} is closed and cannot be used")
        return await self._aiterator.athrow(exc)


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
