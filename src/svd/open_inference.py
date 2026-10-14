"""Load HF presets and score videos (image-classifier or VideoMAE)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.svd.model_catalog import (
    ConsensusStrategy,
    ModelKind,
    preset_by_id,
    resolve_consensus_strategy,
    resolve_open_models,
)


@dataclass
class LoadedModel:
    kind: ModelKind
    hf_model_id: str
    preset_id: str | None
    processor: Any
    model: Any
    device: str


def _hf_token() -> str | None:
    import os

    token = os.environ.get("HF_TOKEN", "").strip()
    return token or None


def _synthetic_label_ids(id2label: dict[Any, Any]) -> set[int]:
    ids: set[int] = set()
    for idx, label in id2label.items():
        text = str(label).lower()
        if any(token in text for token in ("fake", "deep", "synthetic", "artificial", "ai")):
            ids.add(int(idx))
    return ids


def _load_one_model(
    *,
    hf_model_id: str,
    kind: ModelKind,
    preset_id: str | None,
    device: str,
    token: str | None,
) -> LoadedModel:
    if kind == "videomae":
        from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor

        processor = VideoMAEImageProcessor.from_pretrained(hf_model_id, token=token)
        model = VideoMAEForVideoClassification.from_pretrained(hf_model_id, token=token)
    else:
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        processor = AutoImageProcessor.from_pretrained(hf_model_id, token=token)
        model = AutoModelForImageClassification.from_pretrained(hf_model_id, token=token)

    model.to(device)
    model.eval()
    return LoadedModel(
        kind=kind,
        hf_model_id=hf_model_id,
        preset_id=preset_id,
        processor=processor,
        model=model,
        device=device,
    )


def load_open_model() -> LoadedModel:
    models = load_open_models()
    if not models:
        raise RuntimeError("No bundled Hugging Face models configured")
    return models[0]


def load_open_models() -> list[LoadedModel]:
    import torch

    specs = resolve_open_models()
    if not specs:
        raise RuntimeError("No bundled Hugging Face models configured")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    token = _hf_token()
    loaded: list[LoadedModel] = []
    for spec in specs:
        hf_model_id = str(spec.get("hf_model_id") or "").strip()
        kind = str(spec.get("kind") or "image").lower()
        if kind not in {"image", "videomae"}:
            kind = "image"
        preset_id = spec.get("preset_id")
        preset_id_str = str(preset_id) if preset_id else None
        if preset_id_str:
            preset = preset_by_id(preset_id_str)
            if preset:
                hf_model_id = str(preset.get("hf_model_id") or hf_model_id)
                kind = str(preset.get("kind") or kind)
        loaded.append(
            _load_one_model(
                hf_model_id=hf_model_id,
                kind=kind,  # type: ignore[arg-type]
                preset_id=preset_id_str,
                device=device,
                token=token,
            )
        )
    return loaded


def _logit_from_prob(prob: float) -> float:
    import torch

    p = max(1e-6, min(1.0 - 1e-6, prob))
    return float(torch.logit(torch.tensor(p)))


def _aggregate_method(kind: ModelKind, preset_id: str | None) -> str:
    if preset_id:
        preset = preset_by_id(preset_id)
        if preset and preset.get("aggregate"):
            return str(preset["aggregate"]).lower()
    if kind == "videomae":
        return "median"
    return "mean"


def _aggregate(
    clip_results: list[dict[str, float | int]],
    *,
    kind: ModelKind = "image",
    preset_id: str | None = None,
) -> dict[str, object]:
    if not clip_results:
        raise ValueError("No scores produced")
    scores = [float(c["score"]) for c in clip_results]
    method = _aggregate_method(kind, preset_id)
    if method == "median":
        sorted_scores = sorted(scores)
        mid = len(sorted_scores) // 2
        if len(sorted_scores) % 2:
            probability = sorted_scores[mid]
        else:
            probability = (sorted_scores[mid - 1] + sorted_scores[mid]) / 2.0
    else:
        probability = sum(scores) / len(scores)
    mean_logit = sum(float(c["logit"]) for c in clip_results) / len(clip_results)
    if 0.0 < probability < 1.0:
        mean_logit = _logit_from_prob(probability)
    csv_lines = ["clip_index,score,logit"]
    for row in clip_results:
        csv_lines.append(f"{row['index']},{row['score']:.6f},{row['logit']:.6f}")
    return {
        "probability": probability,
        "logit": mean_logit,
        "total_clips": len(clip_results),
        "csv_data": "\n".join(csv_lines) + "\n",
        "clip_results": clip_results,
    }


def _read_frame_at(cap, index: int):
    import cv2

    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    if not ok or frame is None:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def _score_image_model(loaded: LoadedModel, path: Path) -> dict[str, object]:
    import cv2
    import torch

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    sample_every = 15
    max_samples = 48
    clip_results: list[dict[str, float | int]] = []
    frame_idx = 0
    sampled = 0

    id2label = getattr(loaded.model.config, "id2label", {}) or {}
    fake_ids = _synthetic_label_ids(id2label)
    if not fake_ids and id2label:
        fake_ids = {max(int(k) for k in id2label)}

    while sampled < max_samples:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % sample_every != 0:
            frame_idx += 1
            continue
        frame_idx += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = loaded.processor(images=rgb, return_tensors="pt")
        inputs = {k: v.to(loaded.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = loaded.model(**inputs)
            probs = torch.softmax(out.logits, dim=-1)[0]
        if fake_ids:
            fake_prob = float(max(probs[i] for i in fake_ids if i < len(probs)))
        else:
            fake_prob = float(probs[-1])
        logit = _logit_from_prob(fake_prob)
        clip_results.append({"index": sampled, "logit": logit, "score": fake_prob})
        sampled += 1

    cap.release()
    return _aggregate(clip_results, kind="image", preset_id=loaded.preset_id)


def _score_videomae(loaded: LoadedModel, path: Path) -> dict[str, object]:
    import cv2
    import torch

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total < 2:
        cap.release()
        raise ValueError("Video too short for VideoMAE (need at least 2 frames)")

    num_frames = int(getattr(loaded.model.config, "num_frames", 16) or 16)
    max_windows = 16
    id2label = getattr(loaded.model.config, "id2label", {}) or {}
    fake_ids = _synthetic_label_ids(id2label) or {1}

    clip_results: list[dict[str, float | int]] = []
    window_count = min(max_windows, max(1, total // num_frames))

    for window in range(window_count):
        start = int(window * total / window_count)
        end = int((window + 1) * total / window_count)
        span = max(end - start, 1)
        indices = [start + int(i * span / num_frames) for i in range(num_frames)]
        frames = []
        for idx in indices:
            rgb = _read_frame_at(cap, min(idx, total - 1))
            if rgb is not None:
                frames.append(rgb)
        if len(frames) < num_frames:
            continue
        inputs = loaded.processor(list(frames), return_tensors="pt")
        inputs = {k: v.to(loaded.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = loaded.model(**inputs)
            probs = torch.softmax(out.logits, dim=-1)[0]
        fake_prob = float(max(probs[i] for i in fake_ids if i < len(probs)))
        logit = _logit_from_prob(fake_prob)
        clip_results.append({"index": window, "logit": logit, "score": fake_prob})

    cap.release()
    if not clip_results:
        raise ValueError("VideoMAE could not sample enough frames")
    return _aggregate(clip_results, kind="videomae", preset_id=loaded.preset_id)


def score_video(path: Path, loaded: LoadedModel) -> dict[str, object]:
    if loaded.kind == "videomae":
        return _score_videomae(loaded, path)
    return _score_image_model(loaded, path)


def _consensus_verdict(
    model_rows: list[dict[str, object]],
    *,
    strategy: ConsensusStrategy,
    threshold: float,
) -> tuple[bool, float]:
    probs = [float(row["probability"]) for row in model_rows]
    if not probs:
        return False, 0.0
    mean_prob = sum(probs) / len(probs)
    votes_fake = sum(1 for p in probs if p >= threshold)
    votes_real = len(probs) - votes_fake
    if strategy == "unanimous":
        is_synthetic = votes_fake == len(probs)
    elif strategy == "any":
        is_synthetic = votes_fake > 0
    elif strategy == "mean":
        is_synthetic = mean_prob >= threshold
    else:
        is_synthetic = votes_fake > votes_real or (
            votes_fake == votes_real and mean_prob >= threshold
        )
    return is_synthetic, mean_prob


def _merge_clip_results(results: list[dict[str, object]]) -> list[dict[str, float | int]]:
    if not results:
        return []
    clip_lists = [list(r.get("clip_results") or []) for r in results]
    min_len = min(len(clips) for clips in clip_lists if clips) if clip_lists else 0
    if min_len < 1:
        return list(clip_lists[0]) if clip_lists and clip_lists[0] else []
    merged: list[dict[str, float | int]] = []
    for idx in range(min_len):
        scores = [float(clips[idx]["score"]) for clips in clip_lists if len(clips) > idx]
        avg = sum(scores) / len(scores)
        merged.append({"index": idx, "score": avg, "logit": _logit_from_prob(avg)})
    return merged


def score_video_with_consensus(
    path: Path,
    models: list[LoadedModel],
    *,
    strategy: ConsensusStrategy | None = None,
    threshold: float = 0.05,
) -> dict[str, object]:
    if not models:
        raise ValueError("At least one model is required")
    strategy = strategy or resolve_consensus_strategy()
    per_model_payload: list[dict[str, object]] = []
    raw_results: list[dict[str, object]] = []
    for loaded in models:
        result = score_video(path, loaded)
        raw_results.append(result)
        prob = float(result.get("probability") or 0.0)
        per_model_payload.append(
            {
                "hf_model_id": loaded.hf_model_id,
                "preset_id": loaded.preset_id,
                "kind": loaded.kind,
                "probability": prob,
                "is_synthetic": prob >= threshold,
                "total_clips": int(result.get("total_clips") or 0),
            }
        )

    is_synthetic, mean_prob = _consensus_verdict(
        per_model_payload,
        strategy=strategy,
        threshold=threshold,
    )
    votes_fake = sum(1 for row in per_model_payload if row.get("is_synthetic"))
    clip_results = _merge_clip_results(raw_results)
    logit = _logit_from_prob(mean_prob)
    csv_lines = ["clip_index,score,logit"]
    for row in clip_results:
        csv_lines.append(f"{row['index']},{row['score']:.6f},{row['logit']:.6f}")
    return {
        "probability": mean_prob,
        "logit": logit,
        "total_clips": len(clip_results),
        "csv_data": "\n".join(csv_lines) + "\n",
        "clip_results": clip_results,
        "is_synthetic": is_synthetic,
        "consensus": {
            "strategy": strategy,
            "threshold": threshold,
            "votes_fake": votes_fake,
            "votes_real": len(per_model_payload) - votes_fake,
            "model_count": len(per_model_payload),
            "models": per_model_payload,
        },
    }
