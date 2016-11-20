"""Utilites for asynchronous context management."""

import sys
import functools
import collections

__all__ = ['async_context_manager', 'AsyncExitStack']


# Async context manager

def async_context_manager(func):
    """Asyncronous context manager decorator.

    Example usage::

        @async_context_manager
        async def mycontext():
            try:
                await prepare_context()
                yield some_value
            except SomeException:
                await exception_handling()
            finally:
                await resource_cleanup()

        async with mycontext() as some_value:
            <block>
    """

    @functools.wraps(func)
    def helper(*args, **kwargs):
        return AsyncGeneratorContextManager(func(*args, **kwargs))
    return helper


# Async context manager helper

class AsyncGeneratorContextManager(object):
    """Helper for @async_context_manager decorator."""

    def __init__(self, gen):
        self.gen = gen

    async def __aenter__(self):
        try:
            return await self.gen.__anext__()
        except StopAsyncIteration:
            raise RuntimeError("Async generator didn't yield")

    async def __aexit__(self, type, value, traceback):
        if type is None:
            try:
                await self.gen.__anext__()
            except StopAsyncIteration:
                return
            else:
                raise RuntimeError("Async generator didn't stop")
        else:
            if value is None:
                # Need to force instantiation so we can reliably
                # tell if we get the same exception back
                value = type()  # pragma: no cover
            try:
                await self.gen.athrow(type, value, traceback)
                raise RuntimeError("generator didn't stop after throw()")
            except StopAsyncIteration as exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value
            except:
                # only re-raise if it's *not* the exception that was
                # passed to throw(), because __exit__() must not raise
                # an exception unless __exit__() itself failed.  But throw()
                # has to raise the exception to signal propagation, so this
                # fixes the impedance mismatch between the throw() protocol
                # and the __exit__() protocol.
                #
                if sys.exc_info()[1] is not value:
                    raise


# Async exit stack

class AsyncExitStack:
    """Context manager to dynamically manage asynchronous exit callbacks."""

    def __init__(self):
        self._exit_callbacks = collections.deque()

    def pop_all(self):
        """Preserve the context stack by transferring it to a new instance"""
        new_stack = type(self)()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = collections.deque()
        return new_stack

    def _push_cm_exit(self, cm, cm_exit):
        """Helper to correctly register callbacks to __exit__ methods"""

        async def _exit_wrapper(*exc_details):
            return await cm_exit(cm, *exc_details)

        _exit_wrapper.__self__ = cm
        self.push(_exit_wrapper)

    def push(self, exit):
        """Registers a coroutine with the standard __aexit__ method signature

        Can suppress exceptions the same way __aexit__ methods can.

        Also accepts any object with an __aexit__ method (registering a call
        to the method instead of the object itself)
        """
        # We use an unbound method rather than a bound method to follow
        # the standard lookup behaviour for special methods
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__aexit__
        except AttributeError:
            # Not a context manager, so assume its a callable
            self._exit_callbacks.append(exit)
        else:
            self._push_cm_exit(exit, exit_method)
        # Allow use as a decorator
        return exit

    def callback(self, callback, *args, **kwds):
        """Registers an arbitrary callback and arguments.

        Cannot suppress exceptions.
        """
        async def _exit_wrapper(exc_type, exc, tb):
            await callback(*args, **kwds)
        # We changed the signature, so using @wraps is not appropriate, but
        # setting __wrapped__ may still help with introspection
        _exit_wrapper.__wrapped__ = callback
        self.push(_exit_wrapper)
        # Allow use as a decorator
        return callback

    async def enter_context(self, cm):
        """Enters the supplied context manager

        If successful, also pushes its __aexit__ method as a callback and
        returns the result of the __aenter__ method.
        """
        # Look up the special methods on the type to match the with statement
        _cm_type = type(cm)
        _exit = _cm_type.__aexit__
        result = await _cm_type.__aenter__(cm)
        self._push_cm_exit(cm, _exit)
        return result

    async def aclose(self):
        """Immediately unwind the context stack"""
        await self.__aexit__(None, None, None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_details):
        received_exc = exc_details[0] is not None

        # We manipulate the exception state so it behaves as though
        # we were actually nesting multiple with statements
        frame_exc = sys.exc_info()[1]

        def _fix_exception_context(new_exc, old_exc):
            # Context may not be correct, so find the end of the chain
            while 1:
                exc_context = new_exc.__context__
                if exc_context is old_exc:
                    # Context is already set correctly (see issue 20317)
                    return
                if exc_context is None or exc_context is frame_exc:
                    break
                new_exc = exc_context  # pragma: no cover
            # Change the end of the chain to point to the exception
            # we expect it to reference
            new_exc.__context__ = old_exc

        # Callbacks are invoked in LIFO order to match the behaviour of
        # nested context managers
        suppressed_exc = False
        pending_raise = False
        while self._exit_callbacks:
            cb = self._exit_callbacks.pop()
            try:
                if await cb(*exc_details):
                    suppressed_exc = True
                    pending_raise = False
                    exc_details = (None, None, None)
            except:
                new_exc_details = sys.exc_info()
                # simulate the stack of exceptions by setting the context
                _fix_exception_context(new_exc_details[1], exc_details[1])
                pending_raise = True
                exc_details = new_exc_details
        if pending_raise:
            try:
                # bare "raise exc_details[1]" replaces our carefully
                # set-up context
                fixed_ctx = exc_details[1].__context__
                raise exc_details[1]
            except BaseException:
                exc_details[1].__context__ = fixed_ctx
                raise
        return received_exc and suppressed_exc
