import io
import pytest
import asyncio

from aiostream import stream, pipe
from aiostream.test_utils import add_resource


@pytest.mark.asyncio
async def test_action(assert_run, assert_cleanup):
    with assert_cleanup():
        lst = []
        xs = stream.range(3) | add_resource.pipe(1) | pipe.action(lst.append)
        await assert_run(xs, [0, 1, 2])
        assert lst == [0, 1, 2]

    with assert_cleanup():
        queue = asyncio.Queue()
        xs = stream.range(3) | add_resource.pipe(1) | pipe.action(queue.put)
        await assert_run(xs, [0, 1, 2])
        assert queue.get_nowait() == 0
        assert queue.get_nowait() == 1
        assert queue.get_nowait() == 2


@pytest.mark.asyncio
async def test_print(assert_run, assert_cleanup):
    with assert_cleanup():
        f = io.StringIO()
        xs = stream.range(3) | add_resource.pipe(1) | pipe.print(file=f)
        await assert_run(xs, [0, 1, 2])
        assert f.getvalue() == "0\n1\n2\n"

    with assert_cleanup():
        f = io.StringIO()
        xs = (
            stream.range(3)
            | add_resource.pipe(1)
            | pipe.print("{:.1f}", end="|", file=f)
        )
        await assert_run(xs, [0, 1, 2])
        assert f.getvalue() == "0.0|1.0|2.0|"
