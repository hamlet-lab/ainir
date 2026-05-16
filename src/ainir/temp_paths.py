from __future__ import annotations

import os
import tempfile
from pathlib import Path


def ainir_temp_root() -> Path:
    """Return the cross-platform temp root for AiNIR demo/check outputs.

    Set AINIR_TEMP_ROOT to override the default. Otherwise this uses
    tempfile.gettempdir(), which maps to /tmp on most Unix systems and the
    user temp directory on Windows.
    """
    return Path(os.environ.get("AINIR_TEMP_ROOT") or tempfile.gettempdir())


def ainir_temp_path(name: str) -> Path:
    return ainir_temp_root() / name


def ainir_temp_str(name: str) -> str:
    return str(ainir_temp_path(name))
