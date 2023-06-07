"""Gather the pipe operators."""
from __future__ import annotations

from . import stream

__all__: list[str] = []


def update_pipe_module() -> None:
    """Populate the pipe module dynamically."""
    module_dir = __all__
    operators = stream.__dict__
    for key, value in operators.items():
        if getattr(value, "pipe", None):
            globals()[key] = value.pipe
            if key not in module_dir:
                module_dir.append(key)


# Populate the module
update_pipe_module()
