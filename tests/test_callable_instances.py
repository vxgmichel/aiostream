"""Async callable objects have the same operator behavior as async functions."""

import asyncio
from collections.abc import Awaitable, Callable
from functools import partial
from typing import cast

import pytest

from aiostream import stream


class AsyncDouble:
    async def __call__(self, value):
        return value * 2


class AsyncPredicate:
    async def __call__(self, value):
        return value < 2


class AsyncAdd:
    async def __call__(self, left, right):
        return left + right


class AsyncStream:
    async def __call__(self, value):
        return stream.just(value * 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap", [lambda func: func, partial])
async def test_call_async_callable_instance(wrap):
    callback = cast(Callable[[int], Awaitable[int]], wrap(AsyncDouble()))
    result = await stream.call(callback, 3)
    try:
        assert result == 6
    finally:
        if asyncio.iscoroutine(result):
            result.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap", [lambda func: func, partial])
async def test_map_async_callable_instance(wrap, assert_run):
    await assert_run(
        stream.map(stream.range(3), wrap(AsyncDouble()), task_limit=2), [0, 2, 4]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap", [lambda func: func, partial])
async def test_starmap_async_callable_instance(wrap, assert_run):
    source = stream.iterate([(1, 2), (3, 4)])
    await assert_run(stream.starmap(source, wrap(AsyncAdd())), [3, 7])


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap", [lambda func: func, partial])
@pytest.mark.parametrize(
    "operator, expected",
    [
        (stream.filter, [0, 1]),
        (stream.until, [0]),
        (stream.takewhile, [0, 1]),
        (stream.dropwhile, [2]),
    ],
)
async def test_selection_async_callable_instance(wrap, operator, expected, assert_run):
    await assert_run(operator(stream.range(3), wrap(AsyncPredicate())), expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap", [lambda func: func, partial])
async def test_accumulate_async_callable_instance(wrap, assert_run):
    await assert_run(stream.accumulate(stream.range(1, 4), wrap(AsyncAdd())), [1, 3, 6])


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap", [lambda func: func, partial])
@pytest.mark.parametrize(
    "operator", [stream.concatmap, stream.flatmap, stream.switchmap]
)
async def test_stream_mapping_async_callable_instance(wrap, operator, assert_run):
    await assert_run(operator(stream.just(3), wrap(AsyncStream())), [6])


@pytest.mark.asyncio
@pytest.mark.parametrize("wrap", [lambda func: func, partial])
async def test_action_async_callable_instance(wrap, assert_run):
    calls = []

    class AsyncAction:
        async def __call__(self, value):
            calls.append(value)

    await assert_run(stream.action(stream.range(3), wrap(AsyncAction())), [0, 1, 2])
    assert calls == [0, 1, 2]


@pytest.mark.asyncio
@pytest.mark.parametrize("descriptor", [staticmethod, classmethod])
async def test_async_call_descriptors(descriptor):
    class StaticCallback:
        @staticmethod
        async def __call__(value):
            return value * 2

    class ClassCallback:
        @classmethod
        async def __call__(cls, value):
            return value * 2

    callback = StaticCallback() if descriptor is staticmethod else ClassCallback()
    result = await stream.call(callback, 3)
    try:
        assert result == 6
    finally:
        if asyncio.iscoroutine(result):
            result.close()


@pytest.mark.asyncio
async def test_sync_callable_does_not_inspect_instance_call_attribute():
    class Callback:
        def __getattribute__(self, name):
            if name == "__call__":
                raise AssertionError("special method lookup does not access this")
            return super().__getattribute__(name)

        def __call__(self, value):
            return value * 2

    assert await stream.call(Callback(), 3) == 6


@pytest.mark.asyncio
async def test_sync_function_returning_awaitable_is_not_implicitly_awaited():
    async def value():
        return 6

    coro = value()
    try:
        assert await stream.call(lambda: coro) is coro
    finally:
        coro.close()
