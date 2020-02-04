"""Utilities for asynchronous iteration."""

import functools
from collections.abc import AsyncIterator

import outcome

from . import compat

__all__ = ['aiter', 'anext', 'await_', 'async_',
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
        """Initialize with an asynchronous iterator."""
        assert_async_iterator(aiterator)
        if isinstance(aiterator, AsyncIteratorContext):
            raise TypeError(
                f"{aiterator!r} is already an AsyncIteratorContext")
        self._state = self._STANDBY
        self._aiterator = aiterator
        self._lock = compat.create_lock()
        self._task_group = compat.create_task_group()
        self._item_sender, self._item_receiver = compat.open_channel()
        self._sync_sender, self._sync_receiver = compat.open_channel()

    async def _task_target(self):
        # Control the memory channel
        async with self._item_sender:

            # Control aiterator life span
            try:

                # Loop over items, using handshake synchronization
                while True:
                    await self._sync_receiver.receive()
                    result = await outcome.acapture(anext, self._aiterator)
                    await self._item_sender.send(result)

            # Safely terminates aiterator
            finally:

                # Look for an aclose method
                aclose = getattr(self._aiterator, 'aclose', None)

                # The ag_running attribute has been introduced with python 3.8
                running = getattr(self._aiterator, 'ag_running', False)
                closed = not getattr(self._aiterator, 'ag_frame', True)

                # A RuntimeError is raised if aiterator is running or closed
                if aclose and not running and not closed:
                    try:
                        async with compat.open_cancel_scope(shield=True):
                            await aclose()

                    # Work around bpo-35409
                    except GeneratorExit:  # pragma: no cover
                        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        # Unsafe iteration
        if self._state == self._STANDBY:
            raise RuntimeError(
                f"{type(self).__name__} is iterated outside of its context")

        # Closed context
        if self._state == self._FINISHED:
            raise RuntimeError(
                f"{type(self).__name__}  is closed and cannot be iterated")

        # Prevent concurrent access
        async with self._lock:

            # Perform a handshake
            await self._sync_sender.send(None)

            # Now waits for the next item
            result = await anext(self._item_receiver)

            # Unwrap the result
            return result.unwrap()

    async def __aenter__(self):
        if self._state in self._RUNNING:
            raise RuntimeError(
                f"{type(self).__name__} is running and cannot be entered")
        if self._state == self._FINISHED:
            raise RuntimeError(
                f"{type(self).__name__} is closed and cannot be entered")
        self._state = self._RUNNING

        await self._task_group.__aenter__()
        await self._task_group.spawn(self._task_target)
        return self

    async def __aexit__(self, typ, value, traceback):
        # Idempotency
        if self._state == self._FINISHED:
            return

        # Make sure the task group is exited
        try:

            # Throwing a GeneratorExit into the cancel scope is not a good idea
            if typ is GeneratorExit:
                typ, value, traceback = None, None, None

            # Cancel the task group if necessary
            if typ is None:
                await self._task_group.cancel_scope.cancel()

        # Perform the task group teardown
        finally:
            self._state = self._FINISHED
            await self._task_group.__aexit__(typ, value, traceback)


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
