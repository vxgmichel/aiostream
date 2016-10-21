
import pytest
from aiostream import stream


async def safe_run(xs):
    result = []
    try:
        async with xs.stream() as s:
            async for x in s:
                result.append(x)
    except Exception as exc:
        return result, exc
    else:
        return result, None


@pytest.mark.asyncio
async def test_just():
    xs = stream.just(3)
    result, exc = await safe_run(xs)
    assert result == [3]
    assert exc == None
    assert await xs == 3
