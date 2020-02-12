

import pytest

from aiostream import stream, pipe, compat


@pytest.mark.anyio
async def test_timeout(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(3) | pipe.timeout(5)
        await assert_run(xs, [0, 1, 2])
        assert event_loop.steps == []

    with event_loop.assert_cleanup():
        xs = stream.range(3) + stream.never()
        ys = xs | pipe.timeout(1)
        await assert_run(ys, [0, 1, 2], compat.timeout_error())
        assert event_loop.steps == [1]
