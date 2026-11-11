"""Callback types shared by the mapping operators."""

from __future__ import annotations

from typing import Awaitable, Protocol, TypeVar

__all__ = ["SmapCallable", "AmapCallable", "MapCallable"]

X = TypeVar("X", contravariant=True)
Y = TypeVar("Y", covariant=True)


class SmapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Y: ...


class AmapCallable(Protocol[X, Y]):
    async def __call__(self, arg: X, /, *args: X) -> Y: ...


class MapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Awaitable[Y] | Y: ...
