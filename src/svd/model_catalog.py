"""Curated Hugging Face open-weights presets for Launchpad."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

ModelKind = Literal["image", "videomae"]
ConsensusStrategy = Literal["majority", "unanimous", "any", "mean"]

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "cai" / "config" / "open_model_catalog.json"


def _catalog_path() -> Path:
    override = os.environ.get("SVD_OPEN_MODEL_CATALOG")
    if override:
        return Path(override)
    return _CATALOG_PATH


def load_catalog() -> dict[str, Any]:
    path = _catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"Open model catalog not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_presets() -> list[dict[str, Any]]:
    data = load_catalog()
    presets = data.get("presets") or []
    return [p for p in presets if isinstance(p, dict) and p.get("id")]


def default_preset_id() -> str:
    data = load_catalog()
    return str(data.get("default_preset_id") or "videomae-ffc23")


def preset_by_id(preset_id: str) -> dict[str, Any] | None:
    for preset in list_presets():
        if preset.get("id") == preset_id:
            return preset
    return None


def preset_for_hf_model(hf_model_id: str) -> dict[str, Any] | None:
    needle = hf_model_id.strip()
    for preset in list_presets():
        if preset.get("hf_model_id") == needle:
            return preset
    return None


def _parse_models_json(raw: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        hf_id = str(item.get("hf_model_id") or "").strip()
        if not hf_id:
            continue
        kind = str(item.get("kind") or "image").strip().lower()
        if kind not in {"image", "videomae"}:
            kind = "image"
        entry: dict[str, Any] = {"hf_model_id": hf_id, "kind": kind}
        preset_id = str(item.get("preset_id") or "").strip()
        if preset_id:
            entry["preset_id"] = preset_id
        label = str(item.get("label") or "").strip()
        if label:
            entry["label"] = label
        out.append(entry)
    return out


def resolve_open_models() -> list[dict[str, Any]]:
    """Return ordered Hugging Face model specs for bundled (open-weights) inference."""
    env_json = os.environ.get("SVD_OPEN_MODELS_JSON", "").strip()
    if env_json:
        parsed = _parse_models_json(env_json)
        if parsed:
            return parsed

    preset_id = os.environ.get("SVD_OPEN_MODEL_PRESET", "").strip() or None
    hf_id = os.environ.get("SVD_HF_MODEL_ID", "").strip()
    kind_raw = os.environ.get("SVD_OPEN_MODEL_KIND", "").strip().lower()

    if preset_id:
        preset = preset_by_id(preset_id)
        if preset:
            hf_id = str(preset.get("hf_model_id") or hf_id)
            kind_raw = str(preset.get("kind") or kind_raw)

    if not hf_id:
        preset = preset_by_id(default_preset_id())
        if preset:
            preset_id = str(preset.get("id"))
            hf_id = str(preset.get("hf_model_id"))
            kind_raw = str(preset.get("kind") or "image")

    if not preset_id and hf_id:
        matched = preset_for_hf_model(hf_id)
        if matched:
            preset_id = str(matched.get("id"))

    if kind_raw not in {"image", "videomae"}:
        matched = preset_for_hf_model(hf_id)
        kind_raw = str(matched.get("kind") if matched else "image")

    spec: dict[str, Any] = {"hf_model_id": hf_id, "kind": kind_raw}
    if preset_id:
        spec["preset_id"] = preset_id
    return [spec]


def resolve_consensus_strategy() -> ConsensusStrategy:
    raw = os.environ.get("SVD_OPEN_CONSENSUS", "majority").strip().lower()
    if raw in {"majority", "unanimous", "any", "mean"}:
        return raw  # type: ignore[return-value]
    return "majority"


def resolve_open_model_config() -> tuple[str, ModelKind, str | None]:
    """Return (hf_model_id, kind, preset_id) for the primary bundled model."""
    specs = resolve_open_models()
    primary = specs[0]
    hf_id = str(primary.get("hf_model_id") or "")
    kind_raw = str(primary.get("kind") or "image")
    preset_id = primary.get("preset_id")
    return hf_id, kind_raw, str(preset_id) if preset_id else None  # type: ignore[return-value]
