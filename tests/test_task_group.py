import asyncio

import pytest
from aiostream.manager import TaskGroup


async def task1():
    await asyncio.sleep(1)
    return 1


async def task2():
    await asyncio.sleep(0)
    return 2


async def task3():
    await asyncio.sleep(0)
    raise ValueError(3)


async def task4():
    await asyncio.sleep(1)
    raise ValueError(4)


async def task5():
    try:
        await asyncio.sleep(1)
    finally:
        raise ValueError(5)


@pytest.mark.asyncio
async def test_task_group_cleanup():
    async with TaskGroup() as group:
        t1 = group.create_task(task1())
        t2 = group.create_task(task2())
        t3 = group.create_task(task3())
        t4 = group.create_task(task4())
        t5 = group.create_task(task5())
        # Cancel task1
        t1.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t1
        assert t1.cancelled()
        # Join task2
        assert await t2 == 2
        # Task 3 is finished
        assert t3.done()
        # Task 4 and 5 are not finished
        assert not t4.done()
        assert not t5.done()
