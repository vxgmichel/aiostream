

import io
import pytest

from aiostream import stream, pipe, async_, compat


@pytest.mark.anyio
async def test_action(assert_run, event_loop, add_resource):
    with event_loop.assert_cleanup():
        lst = []
        xs = stream.range(3) | add_resource.pipe(1) | pipe.action(lst.append)
        await assert_run(xs, [0, 1, 2])
        assert lst == [0, 1, 2]

    with event_loop.assert_cleanup():
        queue = compat.anyio.create_queue(0)
        xs = stream.range(3) | add_resource.pipe(1) | pipe.action(async_(queue.put))
        await assert_run(xs, [0, 1, 2])
        assert queue.get_nowait() == 0
        assert queue.get_nowait() == 1
        assert queue.get_nowait() == 2


@pytest.mark.anyio
async def test_print(assert_run, event_loop, add_resource):
    with event_loop.assert_cleanup():
        f = io.StringIO()
        xs = stream.range(3) | add_resource.pipe(1) | pipe.print(file=f)
        await assert_run(xs, [0, 1, 2])
        assert f.getvalue() == '0\n1\n2\n'

    with event_loop.assert_cleanup():
        f = io.StringIO()
        xs = (
            stream.range(3)
            | add_resource.pipe(1)
            | pipe.print('{:.1f}', end='|', file=f)
        )
        await assert_run(xs, [0, 1, 2])
        assert f.getvalue() == '0.0|1.0|2.0|'
