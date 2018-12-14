import asyncio
from aiostream import stream, pipe


def test_timeout_when_not_reached(assert_run, add_resource):
    xs = stream.range(3) | add_resource.pipe(1) | pipe.timeout(5)
    assert_run(xs, [0, 1, 2], steps=[1])


def test_timeout_when_reached(assert_run, add_resource):
    xs = stream.range(3) + stream.never()
    ys = xs | add_resource.pipe(1) | pipe.timeout(5)
    assert_run(ys, [0, 1, 2], asyncio.TimeoutError(), steps=[5, 1])
