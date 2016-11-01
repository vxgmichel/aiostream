
import pytest
import asyncio

from aiostream.test_utils import event_loop
from aiostream.context_utils import async_context_manager, AsyncExitStack

# Pytest fixtures
event_loop


@pytest.mark.asyncio
async def test_contextmanager(event_loop):

    @async_context_manager
    async def acontext(catch=()):
        await asyncio.sleep(1)
        try:
            yield "Something"
        except catch:
            return
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

    with event_loop.assert_cleanup():
        async with acontext(IOError) as value:
            assert value == "Something"
            await asyncio.sleep(1)
            raise IOError
        assert event_loop.steps == [1]*3



@pytest.mark.asyncio
async def test_invalid_contextmanager(event_loop):

    @async_context_manager
    async def broken():
        if False:
            yield

    with pytest.raises(RuntimeError):
        async with broken() as value:
            pass

    @async_context_manager
    async def broken2():
        try:
            yield 1
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


@pytest.mark.asyncio
async def test_exitstack(event_loop):

    @async_context_manager
    async def acontext(arg):
        await asyncio.sleep(1)
        try:
            yield arg
        finally:
            await asyncio.sleep(1)

    with event_loop.assert_cleanup():
        async with AsyncExitStack() as stack:
            for i in range(5):
                value = await stack.enter_context(acontext(i))
                assert value == i
        assert event_loop.steps == [1]*10

    with event_loop.assert_cleanup():
        async with AsyncExitStack() as stack:
            for i in range(5):
                value = await stack.enter_context(acontext(i))
                assert value == i
            await stack.aclose()
            assert event_loop.steps == [1]*10

    with event_loop.assert_cleanup():
        async with AsyncExitStack() as stack:
            for i in range(5):
                value = await stack.enter_context(acontext(i))
                assert value == i
            new_stack = stack.pop_all()
        assert event_loop.steps == [1]*5
        async with new_stack:
            pass
        assert event_loop.steps == [1]*10

    with event_loop.assert_cleanup():
        async with AsyncExitStack() as stack:
            @stack.callback
            async def cleanup():
                await asyncio.sleep(1)
            for i in range(5):
                value = await stack.enter_context(acontext(i))
                assert value == i
        assert event_loop.steps == [1]*11

    with event_loop.assert_cleanup():
        async with AsyncExitStack() as stack:
            for i in range(5):
                context = acontext(i)
                assert await context.__aenter__() == i
                stack.push(context)
        assert event_loop.steps == [1]*10

    with event_loop.assert_cleanup():
        with pytest.raises(KeyError):
            async with AsyncExitStack() as stack:
                for i in range(5):
                    value = await stack.enter_context(acontext(i))
                    assert value == i
                raise KeyError('test')
        assert event_loop.steps == [1]*10


@pytest.mark.asyncio
async def test_complex_exitstack(event_loop):

    class TestContext:
        def __init__(self, raises=None, result=None):
            self.raises = raises
            self.result = result

        async def __aenter__(self):
            await asyncio.sleep(1)
            return self

        async def __aexit__(self, *args):
            await asyncio.sleep(1)
            if self.raises:
                raise self.raises
            return self.result

    with event_loop.assert_cleanup():
        with pytest.raises(KeyError):
            async with AsyncExitStack() as stack:
                await stack.enter_context(TestContext(raises=KeyError()))
                await stack.enter_context(TestContext(raises=IOError()))
        assert event_loop.steps == [1]*4

    with pytest.raises(KeyError):
        async with AsyncExitStack() as stack:
            await stack.enter_context(TestContext(raises=KeyError()))
            await stack.enter_context(TestContext(result=True))
        assert event_loop.steps == [1]*4
