from sniffio import current_async_library


def get_loop():
    library = current_async_library()
    if library == 'asyncio':
        from .asyncio import AsyncIO
        return AsyncIO

    if library == 'trio':
        from .trio import Trio
        return Trio

    raise RuntimeError('Unknown async library detected: %s', library)