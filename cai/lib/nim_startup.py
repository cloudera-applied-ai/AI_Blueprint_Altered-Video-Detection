"""Track open-weights model server startup for the runtime UI and Launchpad."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cai.lib.paths import CONFIG_DIR

NIM_STARTUP_JSON = CONFIG_DIR / "nim_startup.json"
SVD_OPEN_MODEL_LOG = CONFIG_DIR / "svd_open_model.log"


def _now() -> float:
    return time.time()


def _default_status() -> dict[str, Any]:
    return {
        "phase": "idle",
        "message": "Model server not started",
        "ready": False,
        "error": None,
        "started_at": None,
        "updated_at": None,
        "elapsed_s": 0,
        "checks": {
            "gpu_visible": False,
            "config_applied": False,
            "endpoints_wired": False,
            "model_process_started": False,
            "model_server_ready": False,
            "endpoints_published": False,
        },
        "log_tail": [],
    }


def tail_log(path: Path, *, lines: int = 12) -> list[str]:
    if not path.is_file():
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return [line.rstrip() for line in content[-lines:] if line.strip()]
    except OSError:
        return []


def reset_nim_startup(*, message: str = "Open model server startup initiated") -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    now = _now()
    payload = _default_status()
    payload.update(
        {
            "phase": "starting",
            "message": message,
            "started_at": now,
            "updated_at": now,
        }
    )
    NIM_STARTUP_JSON.write_text(json.dumps(payload, indent=2) + "\n")


def update_nim_startup(
    phase: str,
    message: str,
    *,
    ready: bool = False,
    error: str | None = None,
    checks: dict[str, bool] | None = None,
    log_paths: tuple[Path, ...] = (SVD_OPEN_MODEL_LOG,),
) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current = read_nim_startup() or _default_status()
    if current.get("started_at") is None:
        current["started_at"] = _now()
    merged_checks = dict(current.get("checks") or {})
    if checks:
        merged_checks.update(checks)
    started = float(current.get("started_at") or _now())
    now = _now()
    tail: list[str] = []
    for path in log_paths:
        tail.extend(tail_log(path, lines=6))
    payload = {
        **current,
        "phase": phase,
        "message": message,
        "ready": ready,
        "error": error,
        "checks": merged_checks,
        "updated_at": now,
        "elapsed_s": int(now - started),
        "log_tail": tail[-18:],
    }
    NIM_STARTUP_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[nim-startup] {phase}: {message}", flush=True)


def read_nim_startup() -> dict[str, Any] | None:
    if not NIM_STARTUP_JSON.exists():
        return None
    try:
        data = json.loads(NIM_STARTUP_JSON.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    started = data.get("started_at")
    updated = data.get("updated_at")
    if started and updated:
        data["elapsed_s"] = int(float(updated) - float(started))
    return data


def mark_nim_startup_error(message: str) -> None:
    update_nim_startup("error", message, error=message)
