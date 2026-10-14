"""Shared path helpers for CAI deployment scripts."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))
CAI_ROOT = PROJECT_ROOT / "cai"
CONFIG_DIR = CAI_ROOT / "config"
ENDPOINTS_ENV = CONFIG_DIR / "runtime_endpoints.env"
NIM_ENDPOINTS_JSON = CAI_ROOT / "nim_endpoints.json"
def runtime_python() -> str:
    """Python for subprocess calls — always the active CAI/runtime interpreter."""
    import sys

    return sys.executable


def media_dir() -> Path:
    override = (os.environ.get("MEDIA_DIR") or os.environ.get("VIDEOS_DIR") or "").strip()
    if override:
        return Path(override)
    return PROJECT_ROOT / "media"


def ensure_cai_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    media_dir().mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "volumes" / "models" / "synthetic-video-detector").mkdir(parents=True, exist_ok=True)
