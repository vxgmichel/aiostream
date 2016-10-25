
import pytest
import asyncio

from aiostream import stream, pipe
from aiostream.test_utils import assert_run, event_loop


@pytest.mark.asyncio
async def test_starmap(assert_run, event_loop):
    xs = stream.range(5)
    ys = stream.range(5)
    zs = xs | pipe.zip(ys) | pipe.starmap(lambda x, y: x+y)
    expected = [x*2 for x in range(5)]
    await assert_run(zs, expected)

    xs = stream.range(1, 4)
    ys = stream.range(1, 4)
    zs = xs | pipe.zip(ys) | pipe.starmap(asyncio.sleep)
    await assert_run(zs, [1, 2, 3])
    assert event_loop.steps == [1, 2, 3]
    event_loop.steps.clear()
