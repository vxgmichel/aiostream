import pytest
import asyncio

from aiostream.test_utils import event_loop, add_resource
from aiostream import stream, streamcontext

# Pytest fixtures
event_loop


@pytest.mark.asyncio
async def test_streamcontext(event_loop):

    with event_loop.assert_cleanup():
        xs = stream.range(3) | add_resource.pipe(1)
        async with streamcontext(xs) as streamer:
            it = iter(range(3))
            async for item in streamer:
                assert item == next(it)
        assert event_loop.steps == [1]

    with event_loop.assert_cleanup():
        xs = stream.range(5) | add_resource.pipe(1)
        async with xs.stream() as streamer:
            it = iter(range(5))
            async for item in streamer:
                assert item == next(it)
        assert event_loop.steps == [1]
