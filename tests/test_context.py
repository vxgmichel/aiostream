
import pytest
import asyncio

from aiostream.test_utils import event_loop
from aiostream.context_utils import acontextmanager, AsyncExitStack

# Pytest fixtures
event_loop


@pytest.mark.asyncio
async def test_acontextmanager(event_loop):

    @acontextmanager
    async def acontext():
        await asyncio.sleep(1)
        try:
            yield "Something"
        finally:
            await asyncio.sleep(1)

    with event_loop.assert_cleanup():
        async with acontext() as value:
            assert value == "Something"
            await asyncio.sleep(1)
        assert event_loop.steps == [1]*3

    with event_loop.assert_cleanup():
        with pytest.raises(IOError):
            async with acontext() as value:
                assert value == "Something"
                await asyncio.sleep(1)
                raise IOError
        assert event_loop.steps == [1]*3

    @acontextmanager
    async def broken():
        if False:
            yield

    with pytest.raises(RuntimeError):
        async with broken() as value:
            pass

    @acontextmanager
    async def broken2():
        try:
            yield 1
        except KeyError:
            print('hey')
            return
        except IOError:
            yield 2
        else:
            yield 3

    with pytest.raises(RuntimeError):
        async with broken2() as value:
            assert value == 1

    with pytest.raises(RuntimeError):
        async with broken2() as value:
            raise IOError
