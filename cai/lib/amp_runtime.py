"""Helpers for CAI AMP session and application entry points."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable


def bootstrap_sys_path() -> Path:
    """Ensure the CAI project root wins over baked-in runtime image paths."""
    root = Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))
    root_str = str(root)
    # Unified runtime image sets PYTHONPATH=/opt/synthetic-video-detector — drop it so
    # project sources (pip install -e . / uploaded files) are used instead.
    image_roots = ("/opt/synthetic-video-detector",)
    sys.path[:] = [p for p in sys.path if not any(p.startswith(r) for r in image_roots)]
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
    return root


def _running_in_ipython() -> bool:
    try:
        get_ipython  # type: ignore[name-defined]  # noqa: F821
    except NameError:
        return False
    return True


def should_run_amp_entry(module_name: str) -> bool:
    """True when invoked as a script or from a CAI/Jupyter run_session kernel."""
    if module_name == "__main__":
        return True
    return _running_in_ipython()


def run_amp_entry(main_func: Callable[[], int], module_name: str) -> None:
    """Call main() for CLI and CAI AMP session execution."""
    if not should_run_amp_entry(module_name):
        return
    code = main_func()
    # IPython/Jupyter run_session kernels treat SystemExit as an error even when
    # code is 0, which makes CAI report "Engine exited with status 1".
    if _running_in_ipython() and code == 0:
        return
    raise SystemExit(code)
