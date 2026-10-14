"""HTTP client for OPEN-mode Hugging Face detector service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import requests

from src.svd.client import ClipResult, DetectionResult, _expit, classification_threshold


def open_server_base() -> str:
    explicit = os.environ.get("SVD_OPEN_SERVER", "").strip().rstrip("/")
    if explicit:
        return explicit
    port = os.environ.get("SVD_OPEN_PORT", "8090")
    return f"http://127.0.0.1:{port}"


def detect_video_open(
    video_path: str | Path,
    *,
    timeout_s: int = 600,
    on_progress: Callable[[dict[str, object]], None] | None = None,
) -> DetectionResult:
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    base = open_server_base()
    if on_progress:
        on_progress({"type": "phase", "phase": "connecting", "message": "Connecting to detector…"})
        on_progress({"type": "phase", "phase": "uploading", "message": "Sending video for analysis…"})

    with path.open("rb") as handle:
        response = requests.post(
            f"{base}/v1/detect",
            files={"file": (path.name, handle, "video/mp4")},
            timeout=timeout_s,
        )
    response.raise_for_status()
    payload = response.json()

    clip_results = [
        ClipResult(index=int(c["index"]), logit=float(c["logit"]))
        for c in payload.get("clip_results") or []
    ]
    if on_progress:
        on_progress({"type": "phase", "phase": "analyzing", "message": "Analyzing video clips…"})
        for clip in clip_results:
            on_progress(
                {
                    "type": "clip",
                    "index": clip.index,
                    "logit": clip.logit,
                    "score": round(_expit(clip.logit), 4),
                    "clips_done": clip.index + 1,
                }
            )
        on_progress(
            {
                "type": "phase",
                "phase": "finalizing",
                "message": "Summarizing results…",
                "total_clips": payload.get("total_clips", len(clip_results)),
            }
        )

    probability = float(payload.get("probability") or 0.0)
    logit = float(payload.get("logit") or 0.0)
    if not probability and logit:
        probability = _expit(logit)
    threshold = classification_threshold()
    consensus = payload.get("consensus")
    if isinstance(consensus, dict) and "is_synthetic" in payload:
        is_synthetic = bool(payload.get("is_synthetic"))
    elif isinstance(consensus, dict):
        votes_fake = int(consensus.get("votes_fake") or 0)
        votes_real = int(consensus.get("votes_real") or 0)
        is_synthetic = votes_fake > votes_real or (
            votes_fake == votes_real and probability >= threshold
        )
    else:
        is_synthetic = probability >= threshold
    score = probability
    return DetectionResult(
        probability=score,
        logit=logit,
        total_clips=int(payload.get("total_clips") or len(clip_results)),
        csv_data=str(payload.get("csv_data") or ""),
        clip_results=clip_results,
        is_synthetic=is_synthetic,
        synthetic_score_percent=round(score * 100, 1),
        consensus=consensus if isinstance(consensus, dict) else None,
    )
