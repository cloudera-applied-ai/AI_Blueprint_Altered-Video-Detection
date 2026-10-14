"""Resolve the in-pod Hugging Face model server port (must not collide with the UI port)."""

from __future__ import annotations

import os

DEFAULT_OPEN_MODEL_PORT = 8090


def resolve_open_model_port() -> int:
    """Return SVD_OPEN_PORT, avoiding CDSW_APP_PORT / PORT used by the Next.js runtime UI."""
    app_raw = (os.environ.get("CDSW_APP_PORT") or os.environ.get("PORT") or "").strip()
    app_port: int | None = int(app_raw) if app_raw.isdigit() else None

    raw = (os.environ.get("SVD_OPEN_PORT") or "").strip()
    port = int(raw) if raw.isdigit() else DEFAULT_OPEN_MODEL_PORT

    if app_port is not None and port == app_port:
        port = DEFAULT_OPEN_MODEL_PORT if app_port != DEFAULT_OPEN_MODEL_PORT else app_port + 1

    os.environ["SVD_OPEN_PORT"] = str(port)
    return port
