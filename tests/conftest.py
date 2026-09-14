from aiostream.test_utils import (
    add_resource,
    assert_run,
    assert_cleanup,
    TimeTrackingTestLoop,
)

__all__ = [
    "add_resource",
    "assert_run",
    "assert_cleanup",
]


def pytest_asyncio_loop_factories():
    return {"custom": TimeTrackingTestLoop}
