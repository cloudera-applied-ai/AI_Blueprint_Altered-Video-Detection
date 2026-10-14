"""Environment setup for running blueprint services on CAI."""

from __future__ import annotations

import os
from pathlib import Path

from cai.lib.paths import PROJECT_ROOT


def configure_python_env() -> None:
    paths = [str(PROJECT_ROOT), str(PROJECT_ROOT / "src")]
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = ":".join(paths + ([existing] if existing else []))


def load_config_defaults() -> None:
    try:
        from cai.lib.app_config import apply_persisted_config

        apply_persisted_config()
    except Exception:
        pass
    configure_python_env()
