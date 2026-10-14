"""Application configuration entered via the Launchpad and persisted on disk."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cai.lib.cai_common import write_dotenv_file
from cai.lib.deploy_mode import DEFAULT_SVD_NVCF_FUNCTION_ID, NIMDeployMode, normalize_nim_deploy_mode
from cai.lib.paths import CONFIG_DIR

DEPLOYMENT_CONFIG_JSON = CONFIG_DIR / "deployment_config.json"
APP_ENVIRONMENT_ENV = CONFIG_DIR / "app_environment.env"

SECRET_KEYS: frozenset[str] = frozenset({"ngc_api_key", "hf_token"})

MAX_BUNDLED_OPEN_MODELS = 6
VALID_OPEN_CONSENSUS = frozenset({"majority", "unanimous", "any", "mean"})

_ENV_MAP: dict[str, str] = {
    "nim_deploy_mode": "NIM_DEPLOY_MODE",
    "ngc_api_key": "NGC_API_KEY",
    "hf_token": "HF_TOKEN",
    "svd_hf_model_id": "SVD_HF_MODEL_ID",
    "svd_open_model_preset": "SVD_OPEN_MODEL_PRESET",
    "svd_open_model_kind": "SVD_OPEN_MODEL_KIND",
    "svd_open_port": "SVD_OPEN_PORT",
    "svd_open_consensus": "SVD_OPEN_CONSENSUS",
    "svd_nvidia_function_id": "SVD_NVIDIA_FUNCTION_ID",
    "nvidia_serverless_grpc_host": "NVIDIA_SERVERLESS_GRPC_HOST",
    "nvidia_serverless_grpc_port": "NVIDIA_SERVERLESS_GRPC_PORT",
    "detection_threshold": "SVD_DETECTION_THRESHOLD",
}


@dataclass
class AppConfig:
    nim_deploy_mode: str = "BUNDLED"
    ngc_api_key: str = ""
    hf_token: str = ""
    svd_hf_model_id: str = "eftt/VideoMae-ffc23-deepfake-detector"
    svd_open_model_preset: str = "videomae-ffc23"
    svd_open_model_kind: str = "videomae"
    svd_open_port: str = "8090"
    svd_nvidia_function_id: str = DEFAULT_SVD_NVCF_FUNCTION_ID
    nvidia_serverless_grpc_host: str = "grpc.nvcf.nvidia.com"
    nvidia_serverless_grpc_port: str = "443"
    detection_threshold: str = "0.05"
    svd_open_models: list[dict[str, Any]] = field(default_factory=list)
    svd_open_consensus: str = "majority"

    @classmethod
    def from_environ(cls, *, mode: str | NIMDeployMode | None = None) -> AppConfig:
        """Build config from CML application environment (standalone runtime apps)."""
        resolved_mode = normalize_nim_deploy_mode(
            mode.value if isinstance(mode, NIMDeployMode) else (mode or os.environ.get("NIM_DEPLOY_MODE", "BUNDLED"))
        ).value
        return cls(
            nim_deploy_mode=resolved_mode,
            ngc_api_key=str(os.environ.get("NGC_API_KEY", "")),
            hf_token=str(os.environ.get("HF_TOKEN", "")),
            svd_hf_model_id=str(
                os.environ.get("SVD_HF_MODEL_ID", "eftt/VideoMae-ffc23-deepfake-detector")
            ),
            svd_open_model_preset=str(os.environ.get("SVD_OPEN_MODEL_PRESET", "videomae-ffc23")),
            svd_open_model_kind=str(os.environ.get("SVD_OPEN_MODEL_KIND", "videomae")),
            svd_open_port=str(os.environ.get("SVD_OPEN_PORT", "8090")),
            svd_nvidia_function_id=str(
                os.environ.get("SVD_NVIDIA_FUNCTION_ID") or DEFAULT_SVD_NVCF_FUNCTION_ID
            ),
            nvidia_serverless_grpc_host=str(
                os.environ.get("NVIDIA_SERVERLESS_GRPC_HOST", "grpc.nvcf.nvidia.com")
            ),
            nvidia_serverless_grpc_port=str(os.environ.get("NVIDIA_SERVERLESS_GRPC_PORT", "443")),
            detection_threshold=str(os.environ.get("SVD_DETECTION_THRESHOLD", "0.05")),
            svd_open_models=_open_models_from_environ(),
            svd_open_consensus=_normalize_consensus(str(os.environ.get("SVD_OPEN_CONSENSUS", "majority"))),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        mode = normalize_nim_deploy_mode(str(data.get("nim_deploy_mode", "BUNDLED"))).value
        config = cls(
            nim_deploy_mode=mode,
            ngc_api_key=str(data.get("ngc_api_key", "")),
            hf_token=str(data.get("hf_token", "")),
            svd_hf_model_id=str(
                data.get("svd_hf_model_id", "eftt/VideoMae-ffc23-deepfake-detector")
            ),
            svd_open_model_preset=str(data.get("svd_open_model_preset", "videomae-ffc23")),
            svd_open_model_kind=str(data.get("svd_open_model_kind", "videomae")),
            svd_open_port=str(data.get("svd_open_port", "8090")),
            svd_nvidia_function_id=str(
                data.get("svd_nvidia_function_id") or DEFAULT_SVD_NVCF_FUNCTION_ID
            ),
            nvidia_serverless_grpc_host=str(
                data.get("nvidia_serverless_grpc_host", "grpc.nvcf.nvidia.com")
            ),
            nvidia_serverless_grpc_port=str(data.get("nvidia_serverless_grpc_port", "443")),
            detection_threshold=str(data.get("detection_threshold", "0.05")),
            svd_open_models=_normalize_open_models(data),
            svd_open_consensus=_normalize_consensus(str(data.get("svd_open_consensus", "majority"))),
        )
        return _sync_primary_open_model_fields(config)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nim_deploy_mode": self.nim_deploy_mode,
            "ngc_api_key": self.ngc_api_key,
            "svd_nvidia_function_id": self.svd_nvidia_function_id,
            "nvidia_serverless_grpc_host": self.nvidia_serverless_grpc_host,
            "nvidia_serverless_grpc_port": self.nvidia_serverless_grpc_port,
            "hf_token": self.hf_token,
            "svd_hf_model_id": self.svd_hf_model_id,
            "svd_open_model_preset": self.svd_open_model_preset,
            "svd_open_model_kind": self.svd_open_model_kind,
            "svd_open_port": self.svd_open_port,
            "detection_threshold": self.detection_threshold,
            "svd_open_models": self.svd_open_models,
            "svd_open_consensus": self.svd_open_consensus,
        }

    @classmethod
    def merge_update(cls, existing: AppConfig | None, patch: dict[str, Any]) -> AppConfig:
        merged = existing.to_dict() if existing else {}
        for key, value in patch.items():
            if key in SECRET_KEYS and not str(value or "").strip():
                continue
            merged[key] = value
        return cls.from_dict(merged)

    @classmethod
    def for_mode(cls, mode: str | NIMDeployMode, data: dict[str, Any]) -> AppConfig:
        normalized = normalize_nim_deploy_mode(
            mode.value if isinstance(mode, NIMDeployMode) else mode
        ).value
        payload = {**data, "nim_deploy_mode": normalized}
        return cls.from_dict(payload)

    def secrets_set(self) -> dict[str, bool]:
        return {"ngc_api_key": bool(self.ngc_api_key), "hf_token": bool(self.hf_token)}

    def public_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        for key in SECRET_KEYS:
            data.pop(key, None)
        return data

    def as_process_env(self) -> dict[str, str]:
        env: dict[str, str] = {}
        payload = self.to_dict()
        for json_key, env_key in _ENV_MAP.items():
            value = payload.get(json_key)
            if value is None or value == "":
                continue
            env[env_key] = str(value)
        if self.svd_open_models:
            env["SVD_OPEN_MODELS_JSON"] = json.dumps(self.svd_open_models)
        return env

    def apply_to_environ(self) -> dict[str, str]:
        env = self.as_process_env()
        os.environ.update(env)
        return env

    def app_environment(self) -> dict[str, str]:
        """Env vars baked into a generated standalone CML application."""
        env = self.as_process_env()
        env["TASK_TYPE"] = "START_APPLICATION"
        env["SVD_APP_ROLE"] = "runtime"
        env["NEXT_PUBLIC_SVD_APP_ROLE"] = "runtime"
        env["NIM_DEPLOY_MODE"] = self.nim_deploy_mode
        env["NEXT_PUBLIC_NIM_DEPLOY_MODE"] = self.nim_deploy_mode
        return env

    def validate_for_deploy(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        mode = normalize_nim_deploy_mode(self.nim_deploy_mode).value

        if mode not in {NIMDeployMode.BUNDLED.value, NIMDeployMode.SERVERLESS.value}:
            errors.append(f"Invalid deployment mode: {self.nim_deploy_mode}")

        if mode == NIMDeployMode.SERVERLESS.value:
            if not self.ngc_api_key.strip():
                errors.append("NGC API key is required for serverless deployment.")
            if not self.svd_nvidia_function_id.strip():
                errors.append("NVCF function ID is required for serverless deployment.")
            warnings.append(
                "Serverless deployment uses the NVIDIA Cloud Functions API — evaluation use only."
            )
        else:
            models = self.svd_open_models or _legacy_single_open_model(self)
            if not models:
                errors.append("Select at least one Hugging Face model for bundled deployment.")
            elif len(models) > MAX_BUNDLED_OPEN_MODELS:
                errors.append(
                    f"At most {MAX_BUNDLED_OPEN_MODELS} bundled models are supported per deployment."
                )
            for idx, spec in enumerate(models, start=1):
                if not str(spec.get("hf_model_id") or "").strip():
                    errors.append(f"Bundled model #{idx} is missing a Hugging Face model ID.")
                kind = str(spec.get("kind") or "").lower()
                if kind not in {"image", "videomae"}:
                    errors.append(
                        f"Bundled model #{idx} must use kind 'image' or 'videomae'."
                    )
            if self.svd_open_consensus not in VALID_OPEN_CONSENSUS:
                errors.append(
                    "Invalid consensus strategy. Use majority, unanimous, any, or mean."
                )
            if len(models) > 1:
                warnings.append(
                    f"Bundled runtime loads {len(models)} models; consensus uses '{self.svd_open_consensus}'."
                )
            warnings.append(
                "First start downloads the selected Hugging Face weights into the project cache; allow several minutes on cold boot."
            )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def validate_for_build(self) -> dict[str, Any]:
        return self.validate_for_deploy()


@dataclass
class LaunchpadConfig:
    """Per-mode configuration saved from the Launchpad deploy sections."""

    serverless: AppConfig = field(default_factory=lambda: AppConfig.for_mode("SERVERLESS", {}))
    bundled: AppConfig = field(default_factory=lambda: AppConfig.for_mode("BUNDLED", {}))

    @classmethod
    def from_storage(cls, data: dict[str, Any]) -> LaunchpadConfig:
        if "serverless" in data or "open" in data or "bundled" in data:
            serverless_raw = data.get("serverless") if isinstance(data.get("serverless"), dict) else {}
            bundled_raw = data.get("bundled") if isinstance(data.get("bundled"), dict) else {}
            if not bundled_raw and isinstance(data.get("open"), dict):
                bundled_raw = data.get("open")
            return cls(
                serverless=AppConfig.for_mode("SERVERLESS", serverless_raw),
                bundled=AppConfig.for_mode("BUNDLED", bundled_raw),
            )
        legacy = AppConfig.from_dict(data)
        if legacy.nim_deploy_mode == NIMDeployMode.SERVERLESS.value:
            return cls(serverless=legacy, bundled=AppConfig.for_mode("BUNDLED", {}))
        return cls(serverless=AppConfig.for_mode("SERVERLESS", {}), bundled=legacy)

    def to_storage(self) -> dict[str, Any]:
        return {
            "serverless": self.serverless.to_dict(),
            "bundled": self.bundled.to_dict(),
        }

    def config_for(self, mode: str | NIMDeployMode) -> AppConfig:
        normalized = normalize_nim_deploy_mode(
            mode.value if isinstance(mode, NIMDeployMode) else mode
        )
        if normalized == NIMDeployMode.SERVERLESS:
            return self.serverless
        return self.bundled

    def merge_mode(self, mode: str | NIMDeployMode, patch: dict[str, Any]) -> LaunchpadConfig:
        current = self.config_for(mode)
        updated = AppConfig.merge_update(current, {**patch, "nim_deploy_mode": current.nim_deploy_mode})
        if normalize_nim_deploy_mode(mode) == NIMDeployMode.SERVERLESS:
            return LaunchpadConfig(serverless=updated, bundled=self.bundled)
        return LaunchpadConfig(serverless=self.serverless, bundled=updated)

    def public_dict(self) -> dict[str, Any]:
        return {
            "serverless": self.serverless.public_dict(),
            "bundled": self.bundled.public_dict(),
        }

    def secrets_set(self) -> dict[str, dict[str, bool]]:
        return {
            "serverless": self.serverless.secrets_set(),
            "bundled": self.bundled.secrets_set(),
        }


def _normalize_consensus(raw: str) -> str:
    token = raw.strip().lower()
    return token if token in VALID_OPEN_CONSENSUS else "majority"


def _normalize_open_models(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("svd_open_models")
    if isinstance(raw, list) and raw:
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            hf_id = str(item.get("hf_model_id") or "").strip()
            if not hf_id or hf_id in seen:
                continue
            seen.add(hf_id)
            kind = str(item.get("kind") or "image").lower()
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
        if out:
            return out
    legacy = _legacy_single_open_model_from_dict(data)
    return [legacy] if legacy else []


def _legacy_single_open_model_from_dict(data: dict[str, Any]) -> dict[str, Any] | None:
    hf_id = str(data.get("svd_hf_model_id") or "").strip()
    if not hf_id:
        return None
    kind = str(data.get("svd_open_model_kind") or "image").lower()
    if kind not in {"image", "videomae"}:
        kind = "image"
    entry: dict[str, Any] = {"hf_model_id": hf_id, "kind": kind}
    preset_id = str(data.get("svd_open_model_preset") or "").strip()
    if preset_id:
        entry["preset_id"] = preset_id
    return entry


def _legacy_single_open_model(config: AppConfig) -> list[dict[str, Any]]:
    if config.svd_open_models:
        return config.svd_open_models
    row = _legacy_single_open_model_from_dict(config.to_dict())
    return [row] if row else []


def _sync_primary_open_model_fields(config: AppConfig) -> AppConfig:
    if not config.svd_open_models:
        return config
    primary = config.svd_open_models[0]
    hf_id = str(primary.get("hf_model_id") or "").strip()
    if hf_id:
        config.svd_hf_model_id = hf_id
    kind = str(primary.get("kind") or "").strip()
    if kind in {"image", "videomae"}:
        config.svd_open_model_kind = kind
    preset_id = str(primary.get("preset_id") or "").strip()
    if preset_id:
        config.svd_open_model_preset = preset_id
    return config


def _open_models_from_environ() -> list[dict[str, Any]]:
    raw = os.environ.get("SVD_OPEN_MODELS_JSON", "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return _normalize_open_models({"svd_open_models": data})


def validate_merged_config(
    patch: dict[str, Any] | None = None,
    *,
    mode: str | None = None,
) -> dict[str, Any]:
    launchpad = load_launchpad_config()
    if launchpad is None and not patch:
        return {"valid": False, "errors": ["Save configuration before deploying."], "warnings": []}
    if mode:
        config = launchpad.config_for(mode) if launchpad else AppConfig.for_mode(mode, patch or {})
        if patch:
            config = AppConfig.merge_update(config, patch)
        return config.validate_for_deploy()
    config = launchpad.config_for("BUNDLED") if launchpad else None
    if config is None:
        return {"valid": False, "errors": ["Save configuration before deploying."], "warnings": []}
    return config.validate_for_deploy()


def load_launchpad_config() -> LaunchpadConfig | None:
    if not DEPLOYMENT_CONFIG_JSON.exists():
        return None
    raw = DEPLOYMENT_CONFIG_JSON.read_text().strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return LaunchpadConfig.from_storage(data)


def load_app_config() -> AppConfig | None:
    """Return bundled config if set, else serverless — for backward-compatible call sites."""
    launchpad = load_launchpad_config()
    if launchpad is None:
        return None
    if launchpad.bundled.svd_hf_model_id:
        return launchpad.bundled
    if launchpad.serverless.ngc_api_key:
        return launchpad.serverless
    return launchpad.bundled


def load_mode_config(mode: str | NIMDeployMode) -> AppConfig | None:
    launchpad = load_launchpad_config()
    if launchpad is None:
        return None
    return launchpad.config_for(mode)


def deployment_config_load_error() -> str | None:
    if not DEPLOYMENT_CONFIG_JSON.exists():
        return None
    raw = DEPLOYMENT_CONFIG_JSON.read_text().strip()
    if not raw:
        return f"{DEPLOYMENT_CONFIG_JSON.name} is empty — save configuration first."
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return f"{DEPLOYMENT_CONFIG_JSON.name} is invalid JSON ({exc.msg})."
    if not isinstance(data, dict):
        return f"{DEPLOYMENT_CONFIG_JSON.name} must be a JSON object."
    return None


def save_launchpad_config(launchpad: LaunchpadConfig) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = DEPLOYMENT_CONFIG_JSON.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(launchpad.to_storage(), indent=2) + "\n")
    tmp_path.replace(DEPLOYMENT_CONFIG_JSON)
    return DEPLOYMENT_CONFIG_JSON


def save_mode_config(mode: str | NIMDeployMode, config: AppConfig) -> Path:
    launchpad = load_launchpad_config() or LaunchpadConfig()
    normalized = normalize_nim_deploy_mode(
        mode.value if isinstance(mode, NIMDeployMode) else mode
    )
    if normalized == NIMDeployMode.SERVERLESS:
        launchpad = LaunchpadConfig(serverless=config, bundled=launchpad.bundled)
    else:
        launchpad = LaunchpadConfig(serverless=launchpad.serverless, bundled=config)
    path = save_launchpad_config(launchpad)
    config.apply_to_environ()
    write_dotenv_file(APP_ENVIRONMENT_ENV, config.as_process_env())
    return path


def save_app_config(config: AppConfig) -> Path:
    return save_mode_config(config.nim_deploy_mode, config)


def apply_persisted_config(*, mode: str | NIMDeployMode | None = None) -> AppConfig | None:
    if mode is not None:
        config = load_mode_config(mode)
    else:
        role = os.environ.get("NIM_DEPLOY_MODE") or os.environ.get("SVD_DEPLOY_MODE")
        config = load_mode_config(role) if role else load_app_config()
    if config is None:
        return None
    config.apply_to_environ()
    return config
