"""Callback types shared by the mapping operators."""

from __future__ import annotations

from typing import Any, Awaitable, Coroutine, Protocol, TypeVar

__all__ = ["SmapCallable", "AmapCallable", "MapCallable"]

X = TypeVar("X", contravariant=True)
Y = TypeVar("Y", covariant=True)


class SmapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Y: ...


class AmapCallable(Protocol[X, Y]):
    # Not declared as `async def`, since pyright would then expect the more
    # specific `CoroutineType` instead of `Coroutine` (e.g for `async_`)
    def __call__(self, arg: X, /, *args: X) -> Coroutine[Any, Any, Y]: ...


class MapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Awaitable[Y] | Y: ...
