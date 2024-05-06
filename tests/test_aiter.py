import pytest
import asyncio

from aiostream.aiter_utils import AsyncIteratorContext, aitercontext, anext


# Some async iterators for testing


async def agen():
    for x in range(5):
        await asyncio.sleep(1)
        yield x


async def silence_agen():
    while True:
        try:
            yield 1
        except BaseException:
            return


async def reraise_agen():
    while True:
        try:
            yield 1
        except BaseException as exc:
            raise RuntimeError from exc


async def stuck_agen():
    try:
        yield 1
    except BaseException:
        yield 2


class not_an_agen(list):
    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return self.pop()
        except IndexError:
            raise StopAsyncIteration


# Tests


@pytest.mark.asyncio
async def test_simple_aitercontext(assert_cleanup):
    with assert_cleanup() as loop:
        async with aitercontext(agen()) as safe_gen:
            # Cannot enter twice
            with pytest.raises(RuntimeError):
                async with safe_gen:
                    pass

            it = iter(range(5))
            async for item in safe_gen:
                assert item == next(it)
        assert loop.steps == [1] * 5

    # Exiting is idempotent
    await safe_gen.__aexit__(None, None, None)
    await safe_gen.aclose()

    with pytest.raises(RuntimeError):
        await anext(safe_gen)

    with pytest.raises(RuntimeError):
        async with safe_gen:
            pass

    with pytest.raises(RuntimeError):
        await safe_gen.athrow(ValueError())


@pytest.mark.asyncio
async def test_athrow_in_aitercontext():
    async with aitercontext(agen()) as safe_gen:
        assert await safe_gen.__anext__() == 0
        with pytest.raises(ZeroDivisionError):
            await safe_gen.athrow(ZeroDivisionError())
        async for _ in safe_gen:
            assert False  # No more items


@pytest.mark.asyncio
async def test_aitercontext_wrong_usage():
    safe_gen = aitercontext(agen())
    with pytest.warns(UserWarning):
        await anext(safe_gen)

    with pytest.raises(TypeError):
        AsyncIteratorContext(None)  # type: ignore

    with pytest.raises(TypeError):
        AsyncIteratorContext(safe_gen)


@pytest.mark.asyncio
async def test_raise_in_aitercontext():
    with pytest.raises(ZeroDivisionError):
        async with aitercontext(agen()) as safe_gen:
            async for _ in safe_gen:
                raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        async with aitercontext(agen()) as safe_gen:
            async for _ in safe_gen:
                pass
            raise ZeroDivisionError

    with pytest.raises(GeneratorExit):
        async with aitercontext(agen()) as safe_gen:
            async for _ in safe_gen:
                raise GeneratorExit

    with pytest.raises(GeneratorExit):
        async with aitercontext(agen()) as safe_gen:
            async for _ in safe_gen:
                pass
            raise GeneratorExit


@pytest.mark.asyncio
async def test_silence_exception_in_aitercontext():
    async with aitercontext(silence_agen()) as safe_gen:
        async for item in safe_gen:
            assert item == 1
            raise ZeroDivisionError

    # Silencing a generator exit is forbidden
    with pytest.raises(GeneratorExit):
        async with aitercontext(silence_agen()) as safe_gen:
            async for _ in safe_gen:
                raise GeneratorExit


@pytest.mark.asyncio
async def test_reraise_exception_in_aitercontext():
    with pytest.raises(RuntimeError) as info:
        async with aitercontext(reraise_agen()) as safe_gen:
            async for item in safe_gen:
                assert item == 1
                raise ZeroDivisionError
    assert type(info.value.__cause__) is ZeroDivisionError

    with pytest.raises(RuntimeError) as info:
        async with aitercontext(reraise_agen()) as safe_gen:
            async for item in safe_gen:
                assert item == 1
                raise GeneratorExit
    assert type(info.value.__cause__) is GeneratorExit


@pytest.mark.asyncio
async def test_stuck_in_aitercontext():
    with pytest.raises(RuntimeError) as info:
        async with aitercontext(stuck_agen()) as safe_gen:
            async for item in safe_gen:
                assert item == 1
                raise ZeroDivisionError
    assert "didn't stop after athrow" in str(info.value)

    with pytest.raises(RuntimeError) as info:
        async with aitercontext(stuck_agen()) as safe_gen:
            async for item in safe_gen:
                assert item == 1
                raise GeneratorExit
    # GeneratorExit relies on aclose, not athrow
    # The message is a bit different
    assert "async generator ignored GeneratorExit" in str(info.value)

    # Check athrow behavior
    async with aitercontext(stuck_agen()) as safe_gen:
        assert await safe_gen.__anext__() == 1
        assert await safe_gen.athrow(ZeroDivisionError()) == 2


@pytest.mark.asyncio
async def test_not_an_agen_in_aitercontext():
    async with aitercontext(not_an_agen([1])) as safe_gen:
        async for item in safe_gen:
            assert item == 1

    with pytest.raises(ZeroDivisionError):
        async with aitercontext(not_an_agen([1])) as safe_gen:
            async for item in safe_gen:
                raise ZeroDivisionError


@pytest.mark.asyncio
async def test_aitercontext_idempotent():
    async with aitercontext(aitercontext(agen())) as safe_gen:
        async for item in safe_gen:
            assert item == 0
            break
