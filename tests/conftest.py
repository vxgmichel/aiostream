from aiostream.test_utils import (
    TimeTrackingTestLoop,
    add_resource,
    assert_cleanup,
    assert_run,
)

__all__ = [
    "add_resource",
    "assert_run",
    "assert_cleanup",
]


def pytest_asyncio_loop_factories():
    return {"custom": TimeTrackingTestLoop}
