"""Deployment mode: bundled Hugging Face GPU app vs serverless NVIDIA NVCF (1.6 path)."""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path

from cai.lib.paths import NIM_ENDPOINTS_JSON, PROJECT_ROOT

DEFAULT_SVD_NVCF_FUNCTION_ID = "847b6e53-0133-452d-ab85-d7acf3ace723"


class NIMDeployMode(str, Enum):
    BUNDLED = "BUNDLED"
    SERVERLESS = "SERVERLESS"


def normalize_nim_deploy_mode(raw: str | None = None) -> NIMDeployMode:
    if raw is None:
        raw = os.environ.get("NIM_DEPLOY_MODE") or os.environ.get("SVD_DEPLOY_MODE") or ""
    raw = raw.strip()
    if not raw:
        return NIMDeployMode.BUNDLED

    token = raw.upper().replace("-", "_").replace(" ", "_")
    bundled_aliases = {
        "BUNDLED",
        "BUNDLE",
        "GPU",
        "OPEN",
        "OPEN_WEIGHTS",
        "HF",
        "HUGGINGFACE",
        "LOCAL",
    }
    if token in bundled_aliases:
        return NIMDeployMode.BUNDLED
    if token in {"SERVERLESS", "NVCF", "CLOUD", "NIM"}:
        return NIMDeployMode.SERVERLESS
    raise ValueError(
        f"Invalid deploy mode {raw!r}. Use BUNDLED (Hugging Face in GPU app) or SERVERLESS (NVIDIA NVCF)."
    )


def get_nim_deploy_mode() -> NIMDeployMode:
    return normalize_nim_deploy_mode()


def is_bundled_mode() -> bool:
    return get_nim_deploy_mode() == NIMDeployMode.BUNDLED


def is_bundled_nim_mode() -> bool:
    return is_bundled_mode()


def is_serverless_nim_mode() -> bool:
    return get_nim_deploy_mode() == NIMDeployMode.SERVERLESS


def is_open_weights_mode() -> bool:
    return is_bundled_mode()


def deploy_mode_label() -> str:
    if is_serverless_nim_mode():
        return "serverless NVIDIA Synthetic Video Detector (NVCF gRPC)"
    return "bundled Hugging Face detector (GPU application)"


def skip_message(step_name: str) -> str:
    return f"Skipping '{step_name}' — deploy mode={get_nim_deploy_mode().value}."


def write_serverless_endpoints_json(path: Path | None = None) -> Path:
    target = path or NIM_ENDPOINTS_JSON
    host = os.environ.get("NVIDIA_SERVERLESS_GRPC_HOST", "grpc.nvcf.nvidia.com")
    port = int(os.environ.get("NVIDIA_SERVERLESS_GRPC_PORT", "443"))
    payload = {
        "deploy_mode": NIMDeployMode.SERVERLESS.value,
        "svd": {
            "source": "nvcf",
            "host": host,
            "grpc_port": port,
            "grpc_address": f"{host}:{port}",
            "function_id": os.environ.get("SVD_NVIDIA_FUNCTION_ID", DEFAULT_SVD_NVCF_FUNCTION_ID),
        },
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n")
    return target
