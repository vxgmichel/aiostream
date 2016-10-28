

import pytest
import asyncio

from aiostream.test_utils import event_loop
from aiostream.aiter_utils import AsyncIteratorContext, aitercontext, anext

# Pytest fixtures
event_loop


@pytest.mark.asyncio
async def test_aitercontext(event_loop):

    async def agen():
        for x in range(5):
            await asyncio.sleep(1)
            yield x

    with event_loop.assert_cleanup():
        async with aitercontext(agen()) as safe_gen:
            it = iter(range(5))
            async for item in safe_gen:
                assert item == next(it)
        assert event_loop.steps == [1]*5

        with pytest.raises(RuntimeError):
            await anext(safe_gen)

        with pytest.raises(RuntimeError):
            async with safe_gen:
                pass

    safe_gen = aitercontext(agen())
    with pytest.warns(UserWarning):
        await anext(safe_gen)

    with pytest.raises(TypeError):
        AsyncIteratorContext(None)

    with pytest.raises(TypeError):
        AsyncIteratorContext(safe_gen)
