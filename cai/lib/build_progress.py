"""Track pipeline build progress for the Launchpad UI."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from cai.lib.paths import CONFIG_DIR

BUILD_PROGRESS_JSON = CONFIG_DIR / "build_progress.json"
BUILD_LOCK = CONFIG_DIR / "build.lock"

StepStatus = Literal["pending", "running", "done", "skipped", "error"]


def _now() -> float:
    return time.time()


def read_build_progress() -> dict[str, Any] | None:
    if not BUILD_PROGRESS_JSON.exists():
        return None
    try:
        return json.loads(BUILD_PROGRESS_JSON.read_text())
    except (json.JSONDecodeError, OSError):
        return None


STALE_BUILD_SECONDS = 30 * 60
STALE_FAILED_BUILD_SECONDS = 5 * 60


def reconcile_stale_build(
    *,
    pipeline_failed: bool = False,
    failed_services: list[dict[str, str]] | None = None,
    any_deployed_apps: bool = False,
) -> dict[str, Any] | None:
    """Clear builds left in_progress after a crash or interrupted deploy."""
    progress = read_build_progress()
    if not progress or not progress.get("in_progress"):
        return progress
    updated = float(progress.get("updated_at") or progress.get("started_at") or 0)
    if not updated:
        return progress
    age = _now() - updated
    if not any_deployed_apps and age > 120:
        finish_build_progress(
            False,
            "Previous build did not finish. Click Build pipeline to try again.",
        )
        return read_build_progress()
    if not any_deployed_apps:
        steps = progress.get("steps") or []
        any_step_started = any(step.get("status") in {"running", "done", "error", "skipped"} for step in steps)
        if not any_step_started:
            finish_build_progress(
                False,
                "Previous build did not start. Click Build pipeline to try again.",
            )
            return read_build_progress()
    threshold = STALE_FAILED_BUILD_SECONDS if pipeline_failed else STALE_BUILD_SECONDS
    if age <= threshold:
        return progress
    if pipeline_failed and failed_services:
        summary = "; ".join(f"{item['name']} ({item['status']})" for item in failed_services)
        message = f"Build incomplete: {summary}"
    else:
        message = "Previous build did not finish (timed out or interrupted). Redeploy from the Launchpad."
    finish_build_progress(False, message)
    return read_build_progress()


def is_build_in_progress() -> bool:
    reconcile_stale_build()
    progress = read_build_progress()
    return bool(progress and progress.get("in_progress"))


def start_build_progress(mode: str, steps: list[dict[str, str]]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "in_progress": True,
        "mode": mode,
        "phase": steps[0]["id"] if steps else "starting",
        "message": steps[0]["label"] if steps else "Starting build…",
        "started_at": _now(),
        "updated_at": _now(),
        "error": None,
        "steps": [{**step, "status": "pending", "detail": ""} for step in steps],
    }
    BUILD_PROGRESS_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    BUILD_LOCK.write_text(str(payload["started_at"]))


def finish_build_progress(success: bool, message: str = "") -> None:
    progress = read_build_progress() or {}
    progress["in_progress"] = False
    progress["updated_at"] = _now()
    progress["finished_at"] = _now()
    progress["success"] = success
    if message:
        progress["message"] = message
    if not success and message:
        progress["error"] = message
    BUILD_PROGRESS_JSON.write_text(json.dumps(progress, indent=2) + "\n")
    if BUILD_LOCK.exists():
        BUILD_LOCK.unlink(missing_ok=True)


def set_step(step_id: str, status: StepStatus, detail: str = "", message: str | None = None) -> None:
    progress = read_build_progress()
    if not progress:
        return
    for step in progress.get("steps", []):
        if step["id"] == step_id:
            step["status"] = status
            if detail:
                step["detail"] = detail
    progress["phase"] = step_id
    if message:
        progress["message"] = message
    progress["updated_at"] = _now()
    BUILD_PROGRESS_JSON.write_text(json.dumps(progress, indent=2) + "\n")


def mark_prior_steps_done(current_step_id: str) -> None:
    progress = read_build_progress()
    if not progress:
        return
    seen_current = False
    for step in progress.get("steps", []):
        if step["id"] == current_step_id:
            seen_current = True
            continue
        if not seen_current and step.get("status") in {"pending", "running"}:
            step["status"] = "done"
    BUILD_PROGRESS_JSON.write_text(json.dumps(progress, indent=2) + "\n")
