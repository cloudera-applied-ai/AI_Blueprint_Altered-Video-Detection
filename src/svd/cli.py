#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""CLI for Synthetic Video Detector inference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for image_root in ("/opt/synthetic-video-detector",):
    sys.path[:] = [p for p in sys.path if not p.startswith(image_root)]
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

from src.svd.client import _expit, classification_threshold, detect_video  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect synthetic/AI-generated video content")
    parser.add_argument("--video-input", required=True, help="Path to H.264 MP4 input")
    parser.add_argument("--output-json", default="", help="Optional JSON output path")
    parser.add_argument("--save-csv", default="", help="Optional CSV output path")
    parser.add_argument(
        "--progress-jsonl",
        action="store_true",
        help="Emit progress events as JSON lines on stdout (for Launchpad UI streaming)",
    )
    args = parser.parse_args()

    def emit_progress(event: dict[str, object]) -> None:
        print(json.dumps(event), flush=True)

    result = detect_video(
        args.video_input,
        on_progress=emit_progress if args.progress_jsonl else None,
    )
    clip_series = [
        {"index": clip.index, "logit": clip.logit, "score": round(_expit(clip.logit), 4)}
        for clip in result.clip_results
    ]
    payload = {
        "probability": result.probability,
        "logit": result.logit,
        "synthetic_score_percent": result.synthetic_score_percent,
        "is_synthetic": result.is_synthetic,
        "total_clips": result.total_clips,
        "threshold": classification_threshold(),
        "clip_series": clip_series,
        "csv_data": result.csv_data,
    }
    if result.consensus:
        payload["consensus"] = result.consensus
    if args.progress_jsonl:
        print(json.dumps({"type": "result", **payload}), flush=True)
    else:
        print(json.dumps(payload, indent=2))

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(payload, indent=2) + "\n")
    if args.save_csv and result.csv_data:
        Path(args.save_csv).write_text(result.csv_data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
