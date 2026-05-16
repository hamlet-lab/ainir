from __future__ import annotations

import os
import fnmatch
import shutil
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


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def recreate_output_dir(path: str | Path, *, protected_roots: list[Path] | None = None) -> Path:
    """Safely recreate a demo/check output directory.

    Public demo eval helpers may clean their output directory before writing
    fresh reports. Refuse obviously dangerous targets such as the repository
    root, a parent of the repository, the user home directory, or an existing
    non-output directory inside the repository checkout.
    """
    out = Path(path).expanduser()
    resolved = out.resolve()
    protected = [Path.cwd().resolve(), Path.home().resolve()]
    protected.extend(p.resolve() for p in (protected_roots or []))

    if resolved == resolved.parent:
        raise ValueError(f"refusing to recreate filesystem root: {resolved}")

    for root in protected:
        if resolved == root or _is_within(root, resolved):
            raise ValueError(f"refusing to recreate protected output directory: {resolved}")

    if out.exists() and not out.is_dir():
        raise ValueError(f"output path exists and is not a directory: {resolved}")

    repo_roots = [root for root in protected_roots or [] if root.exists()]
    inside_repo = any(_is_within(resolved, root) for root in repo_roots)
    allowed_repo_output = (
        "*_results",
        "ainir_*",
        "phase*_results",
        "phase*_receipt*",
        "phase*_conformance*",
    )
    if out.exists() and inside_repo and not any(fnmatch.fnmatch(resolved.name, pat) for pat in allowed_repo_output):
        raise ValueError(f"refusing to remove non-output directory inside repository: {resolved}")

    if out.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
