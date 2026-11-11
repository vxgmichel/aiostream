"""Callback types shared by the mapping operators."""

from __future__ import annotations

from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Protocol,
    TypeAlias,
    TypeVar,
    Union,
)

__all__ = [
    "SmapCallable",
    "AmapCallable",
    "MapCallable",
    "VariadicSmapCallable",
    "VariadicAmapCallable",
    "VariadicMapCallable",
]

X = TypeVar("X", contravariant=True)
Y = TypeVar("Y", covariant=True)


# Mapping callbacks take one argument per source. Variadic callbacks are
# accepted for any number of sources, while single-argument callbacks are also
# accepted so that the common single-source case doesn't require a dummy `*_`
# parameter. Note that type checkers can't check the number of arguments
# against the number of sources: this relation cannot be expressed using
# a `TypeVarTuple` since PEP 646 does not provide a `Map` operator.


class VariadicSmapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Y: ...


class VariadicAmapCallable(Protocol[X, Y]):
    # Not declared as `async def`, since pyright would then expect the more
    # specific `CoroutineType` instead of `Coroutine` (e.g for `async_`)
    def __call__(self, arg: X, /, *args: X) -> Coroutine[Any, Any, Y]: ...


class VariadicMapCallable(Protocol[X, Y]):
    def __call__(self, arg: X, /, *args: X) -> Awaitable[Y] | Y: ...


SmapCallable: TypeAlias = Union[Callable[[X], Y], VariadicSmapCallable[X, Y]]
AmapCallable: TypeAlias = Union[
    Callable[[X], Coroutine[Any, Any, Y]], VariadicAmapCallable[X, Y]
]
MapCallable: TypeAlias = Union[
    Callable[[X], Union[Awaitable[Y], Y]], VariadicMapCallable[X, Y]
]
