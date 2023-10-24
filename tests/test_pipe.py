from aiostream import stream, pipe


def test_pipe_module():
    for name in dir(stream):
        obj = getattr(stream, name)
        pipe_method = getattr(obj, "pipe", None)
        if pipe_method is None:
            continue
        assert getattr(pipe, name) == pipe_method
