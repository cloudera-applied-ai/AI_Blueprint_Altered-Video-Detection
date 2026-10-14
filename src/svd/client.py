"""Unified detection client: open-weights (HTTP) or optional cloud gRPC."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

DATA_CHUNK_SIZE = 2 * 1024 * 1024
CLASSIFICATION_THRESHOLD = 0.05


def classification_threshold() -> float:
    raw = os.environ.get("SVD_DETECTION_THRESHOLD", "").strip()
    if not raw:
        return CLASSIFICATION_THRESHOLD
    try:
        value = float(raw)
    except ValueError:
        return CLASSIFICATION_THRESHOLD
    return max(0.0, min(1.0, value))


@dataclass
class ClipResult:
    index: int
    logit: float


@dataclass
class DetectionResult:
    probability: float
    logit: float
    total_clips: int
    csv_data: str
    clip_results: list[ClipResult]
    is_synthetic: bool
    synthetic_score_percent: float
    consensus: dict[str, Any] | None = None


def _expit(logit: float) -> float:
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    exp_logit = math.exp(logit)
    return exp_logit / (1.0 + exp_logit)


def _deploy_mode() -> str:
    mode = (
        os.environ.get("SVD_DEPLOY_MODE")
        or os.environ.get("NIM_DEPLOY_MODE")
        or "BUNDLED"
    ).strip().upper()
    if mode in {"BUNDLED", "BUNDLE", "GPU", "HF", "HUGGINGFACE", "OPEN_WEIGHTS", "OPEN"}:
        return "BUNDLED"
    return mode


def detect_video(
    video_path: str | Path,
    *,
    timeout_s: int = 600,
    on_progress: Callable[[dict[str, object]], None] | None = None,
) -> DetectionResult:
    """Analyze an MP4 and return clip-level scores plus an aggregate synthetic probability."""
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    if path.suffix.lower() != ".mp4":
        raise ValueError("Detector supports MP4 input only")

    mode = _deploy_mode()
    if mode == "BUNDLED":
        from src.svd.open_detect import detect_video_open

        return detect_video_open(path, timeout_s=timeout_s, on_progress=on_progress)

    if mode == "SERVERLESS":
        try:
            from src.svd.serverless_detect import detect_video_serverless
        except ImportError as exc:
            raise RuntimeError(
                "Serverless detection requires the serverless Python extra (grpcio). "
                "Use the SyntheticVideoDetector runtime image or uv sync --extra serverless."
            ) from exc
        return detect_video_serverless(path, timeout_s=timeout_s, on_progress=on_progress)

    raise RuntimeError(f"Unsupported deploy mode: {mode}")


__all__ = [
    "CLASSIFICATION_THRESHOLD",
    "ClipResult",
    "DetectionResult",
    "DATA_CHUNK_SIZE",
    "detect_video",
    "_expit",
]
