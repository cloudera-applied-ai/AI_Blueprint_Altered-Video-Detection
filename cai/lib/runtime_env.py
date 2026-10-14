"""Resolve the ML runtime docker image from the running CAI workload environment."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cai.lib.paths import CONFIG_DIR, PROJECT_ROOT

RUNTIME_CONTEXT_JSON = CONFIG_DIR / "runtime_context.json"

# Env vars Cloudera AI / CML may inject into running sessions and applications.
# Checked in order; first value that looks like a container image wins.
RUNTIME_IMAGE_ENV_VARS: tuple[str, ...] = (
    "RUNTIME_IDENTIFIER",
    "ML_RUNTIME_IMAGE",
    "ML_RUNTIME_DOCKER_IMAGE",
    "CDSW_RUNTIME_IMAGE",
    "CDSW_ML_RUNTIME_IMAGE",
    "DOCKER_IMAGE",
    "IMAGE_NAME",
    "CONTAINER_IMAGE",
    "HEAD_RUNTIME_IDENTIFIER",
    "WORKER_RUNTIME_IDENTIFIER",
)


def _looks_like_image_ref(value: str) -> bool:
    value = value.strip()
    return bool(value) and ("/" in value or ":" in value) and " " not in value


def runtime_identifier_from_environ() -> str | None:
    """Return runtime image from process environment (live, no cache)."""
    for key in RUNTIME_IMAGE_ENV_VARS:
        value = os.environ.get(key, "").strip()
        if _looks_like_image_ref(value):
            return value
    return None


def _application_id_candidates() -> list[str]:
    ids: list[str] = []
    for key in (
        "CDSW_APP_ID",
        "CML_APPLICATION_ID",
        "CDSW_ENGINE_ID",
        "CML_ENGINE_ID",
    ):
        value = os.environ.get(key, "").strip()
        if value and value not in ids:
            ids.append(value)
    return ids


def runtime_identifier_from_cml_api() -> str | None:
    """Look up runtime_identifier for this application via CML API."""
    from cai.lib.cml_client import CMLClient

    client = CMLClient()
    for app_id in _application_id_candidates():
        try:
            app = client.get_application(app_id)
        except Exception:
            continue
        for key in ("runtime_identifier", "runtime", "kernel", "image_identifier"):
            value = str(app.metadata.get(key, "")).strip()
            if _looks_like_image_ref(value):
                return value

    # Match this demo application by script path when app id env vars differ.
    script_hint = "cai/amp/6_demo_ui/start_demo.py"
    for app in client.list_applications():
        script = str(app.metadata.get("script", ""))
        name = app.name or ""
        if script_hint in script or "Launchpad" in name or "Build UI" in name:
            for key in ("runtime_identifier", "runtime", "kernel", "image_identifier"):
                value = str(app.metadata.get(key, "")).strip()
                if _looks_like_image_ref(value):
                    return value
    return None


def capture_runtime_context(*, write_file: bool = True) -> dict[str, Any]:
    """
    Snapshot runtime-related env and resolved identifier for deploy diagnostics.

    Called at demo app startup so deploy can reuse the same image as the running app.
    """
    env_snapshot = {
        key: os.environ[key]
        for key in RUNTIME_IMAGE_ENV_VARS
        if os.environ.get(key)
    }
    for key in (
        "CDSW_APP_ID",
        "CML_APPLICATION_ID",
        "CDSW_ENGINE_ID",
        "ML_RUNTIME_EDITION",
        "ML_RUNTIME_FULL_VERSION",
        "ML_RUNTIME_SHORT_VERSION",
    ):
        if os.environ.get(key):
            env_snapshot[key] = os.environ[key]

    resolved = runtime_identifier_from_environ()
    source = "environment" if resolved else None
    if not resolved:
        try:
            resolved = runtime_identifier_from_cml_api()
            source = "cml_api" if resolved else source
        except Exception as exc:
            env_snapshot["cml_api_error"] = str(exc)

    payload: dict[str, Any] = {
        "runtime_identifier": resolved,
        "source": source,
        "env": env_snapshot,
    }
    if write_file:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        RUNTIME_CONTEXT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def get_runtime_identifier(*, refresh: bool = False) -> str:
    """
    Resolve docker image for create_application calls.

    Order: live environment → cached runtime_context.json → CML API.
    """
    if not refresh:
        live = runtime_identifier_from_environ()
        if live:
            return live

        if RUNTIME_CONTEXT_JSON.exists():
            cached = json.loads(RUNTIME_CONTEXT_JSON.read_text())
            cached_id = str(cached.get("runtime_identifier", "")).strip()
            if _looks_like_image_ref(cached_id):
                return cached_id

    context = capture_runtime_context()
    resolved = context.get("runtime_identifier")
    if isinstance(resolved, str) and _looks_like_image_ref(resolved):
        return resolved

    raise RuntimeError(
        "Could not resolve ML runtime image from the running application. "
        f"Checked env vars {', '.join(RUNTIME_IMAGE_ENV_VARS)} and CML API. "
        f"See {RUNTIME_CONTEXT_JSON} after starting the Launchpad application."
    )


def log_runtime_context() -> None:
    """Print runtime resolution details to application logs."""
    context = capture_runtime_context()
    print("Runtime context:", json.dumps(context, indent=2), flush=True)
