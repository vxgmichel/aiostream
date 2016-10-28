

import pytest
import asyncio

from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop

# Pytest fixtures
assert_run, event_loop


@pytest.mark.asyncio
async def test_timeout(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(3) | pipe.timeout(5)
        await assert_run(xs, [0, 1, 2])
        assert event_loop.steps == [5, 5, 5, 5]

    with event_loop.assert_cleanup():
        xs = stream.range(3) + stream.never()
        ys = xs | pipe.timeout(1)
        await assert_run(ys, [0, 1, 2], asyncio.TimeoutError())
        assert event_loop.steps == [1, 1, 1, 1]
