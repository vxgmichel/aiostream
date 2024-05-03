import pytest
import asyncio

from aiostream import stream, pipe


@pytest.mark.asyncio
async def test_timeout(assert_run, assert_cleanup):
    with assert_cleanup() as loop:
        xs = stream.range(3) | pipe.timeout(5)
        await assert_run(xs, [0, 1, 2])
        assert loop.steps == []

    with assert_cleanup():
        xs = stream.range(3) + stream.never()
        ys = xs | pipe.timeout(1)
        await assert_run(ys, [0, 1, 2], asyncio.TimeoutError())
        assert loop.steps == [1]
