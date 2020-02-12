
import pytest

from aiostream import stream, pipe, compat


@pytest.mark.anyio
async def test_starmap(assert_run, event_loop):
    with event_loop.assert_cleanup():
        xs = stream.range(5)
        ys = stream.range(5)
        zs = xs | pipe.zip(ys) | pipe.starmap(lambda x, y: x+y)
        expected = [x*2 for x in range(5)]
        await assert_run(zs, expected)

    with event_loop.assert_cleanup():
        xs = stream.range(1, 4)
        ys = stream.range(1, 4)
        zs = xs | pipe.zip(ys) | pipe.starmap(compat.sleep)
        await assert_run(zs, [1, 2, 3])
        assert event_loop.steps == [1, 1, 1]

    with event_loop.assert_cleanup():
        xs = stream.range(1, 4)
        ys = stream.range(1, 4)
        zs = xs | pipe.zip(ys) | pipe.starmap(compat.sleep, task_limit=1)
        await assert_run(zs, [1, 2, 3])
        assert event_loop.steps == [1, 2, 3]


@pytest.mark.anyio
async def test_cycle(assert_run, event_loop, add_resource):
    with event_loop.assert_cleanup():
        xs = stream.empty() | pipe.cycle() | pipe.timeout(1)
        await assert_run(xs, [], compat.timeout_error())

    with event_loop.assert_cleanup():
        xs = (
            stream.empty()
            | add_resource.pipe(1)
            | pipe.cycle()
            | pipe.timeout(1)
        )
        await assert_run(xs, [], compat.timeout_error())

    with event_loop.assert_cleanup():
        xs = stream.just(1) | add_resource.pipe(1) | pipe.cycle()
        await assert_run(xs[:5], [1]*5)
        assert event_loop.steps == [1]*5


@pytest.mark.anyio
async def test_chunks(assert_run, event_loop, add_resource):
    with event_loop.assert_cleanup():
        xs = stream.range(3, interval=1) | pipe.chunks(3)
        await assert_run(xs, [[0, 1, 2]])

    with event_loop.assert_cleanup():
        xs = stream.range(4, interval=1) | pipe.chunks(3)
        await assert_run(xs, [[0, 1, 2], [3]])

    with event_loop.assert_cleanup():
        xs = stream.range(5, interval=1) | pipe.chunks(3)
        await assert_run(xs, [[0, 1, 2], [3, 4]])

    with event_loop.assert_cleanup():
        xs = (stream.count(interval=1)
              | add_resource.pipe(1)
              | pipe.chunks(3))
        await assert_run(xs[:1], [[0, 1, 2]])
