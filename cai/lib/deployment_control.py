"""Deploy and manage all-in-one SVD applications from the Launchpad."""

from __future__ import annotations

import time
from typing import Any

from cai.lib.app_config import (
    AppConfig,
    LaunchpadConfig,
    load_launchpad_config,
    save_mode_config,
)
from cai.lib.build_progress import (
    finish_build_progress,
    is_build_in_progress,
    read_build_progress,
    reconcile_stale_build,
    set_step,
    start_build_progress,
)
from cai.lib.cml_client import ApplicationInfo, CMLClient
from cai.lib.deploy_mode import NIMDeployMode, normalize_nim_deploy_mode
from cai.lib.nim_startup import read_nim_startup
from cai.lib.paths import CONFIG_DIR, ensure_cai_dirs
from cai.lib.subdomains import unique_subdomain

SERVICE_SPECS: dict[str, dict[str, Any]] = {
    "serverless": {
        "name": "Synthetic Video Detector (Serverless)",
        "subdomain_base": "svd-serverless",
        "script": "cai/amp/5_apps/launch_serverless_app.py",
        "cpu": 2,
        "memory": 8,
        "gpu": 0,
        "mode": NIMDeployMode.SERVERLESS.value,
    },
    "bundled": {
        "name": "Synthetic Video Detector (Bundled)",
        "subdomain_base": "svd-bundled",
        "script": "cai/amp/5_apps/launch_bundled_app.py",
        "cpu": 4,
        "memory": 32,
        "gpu": 1,
        "mode": NIMDeployMode.BUNDLED.value,
    },
}

MODE_TO_SPEC_KEY = {
    NIMDeployMode.SERVERLESS.value: "serverless",
    NIMDeployMode.BUNDLED.value: "bundled",
}


def _spec_key_for_mode(mode: str) -> str:
    normalized = normalize_nim_deploy_mode(mode).value
    key = MODE_TO_SPEC_KEY.get(normalized)
    if not key:
        raise ValueError(f"Unsupported deploy mode: {mode}")
    return key


def deploy_plan(mode: str) -> list[dict[str, str]]:
    label = "Serverless" if mode == NIMDeployMode.SERVERLESS.value else "Bundled"
    steps = [
        {"id": "validate", "label": f"Validate {label} configuration"},
        {"id": "save", "label": "Save configuration"},
        {"id": "deploy", "label": f"Deploy {label} application"},
    ]
    if mode == NIMDeployMode.BUNDLED.value:
        steps.append({"id": "model", "label": "Wait for bundled model server to become ready"})
    steps.append({"id": "ready", "label": "Deployment ready"})
    return steps


RUNNING_APP_STATUSES = frozenset({"RUNNING", "APPLICATION_RUNNING"})
FAILED_APP_STATUSES = frozenset(
    {"APPLICATION_FAILED", "FAILED", "STOPPED", "APPLICATION_STOPPED", "ERROR", "APPLICATION_ERROR"}
)


def _normalize_app_status(status: str | None) -> str:
    return (status or "").upper()


def _is_app_running(status: str | None) -> bool:
    return _normalize_app_status(status) in RUNNING_APP_STATUSES


def _is_app_failed(status: str | None) -> bool:
    normalized = _normalize_app_status(status)
    return normalized in FAILED_APP_STATUSES or "FAIL" in normalized


def _find_app(apps: list[ApplicationInfo], name: str) -> ApplicationInfo | None:
    for app in apps:
        if app.name == name:
            return app
    return None


def _wait_for_app_removed(client: CMLClient, name: str, *, timeout_s: int = 180) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _find_app(client.list_applications(), name) is None:
            return
        time.sleep(3)
    raise TimeoutError(f"Timed out waiting for application {name!r} to be deleted")


def _ensure_application(
    client: CMLClient,
    spec_key: str,
    config: AppConfig,
    apps: list[ApplicationInfo],
    *,
    recreate: bool = True,
) -> dict[str, Any]:
    spec = SERVICE_SPECS[spec_key]
    existing = _find_app(apps, spec["name"])
    env = config.app_environment()
    if int(spec.get("gpu", 0)) > 0:
        env.setdefault("NVIDIA_DRIVER_CAPABILITIES", "all")

    if existing and recreate:
        client.delete_application(existing.id)
        _wait_for_app_removed(client, spec["name"])
        apps = client.list_applications()
        existing = None

    if existing and _is_app_running(existing.status):
        return {"key": spec_key, "name": spec["name"], "application": existing.metadata, "created": False}

    subdomain = unique_subdomain(spec["subdomain_base"])
    created = client.create_application(
        name=spec["name"],
        script=spec["script"],
        subdomain=subdomain,
        cpu=int(spec["cpu"]),
        memory=int(spec["memory"]),
        gpu=int(spec.get("gpu", 0)),
        environment=env,
    )
    return {"key": spec_key, "name": spec["name"], "application": created.metadata, "created": True}


def _wait_for_service_running(spec_key: str, *, timeout_s: int = 900) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = list_deployment_status()
        svc = status.get("deployments", {}).get(spec_key, {})
        app_status = svc.get("application", {}).get("status", "not started")
        if _is_app_failed(app_status):
            raise RuntimeError(f"{svc.get('name', spec_key)} failed ({app_status})")
        if _is_app_running(app_status):
            return
        time.sleep(10)
    raise TimeoutError(f"Timed out waiting for {spec_key} application to reach RUNNING")


def _wait_for_model_ready(timeout_s: int = 3600) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        startup = read_nim_startup() or {}
        if startup.get("ready"):
            return startup
        time.sleep(10)
    raise TimeoutError("Timed out waiting for bundled model server (nim_startup.json)")


def deploy_application(mode: str, config: AppConfig) -> dict[str, Any]:
    """Deploy (or redeploy) an all-in-one SVD application for the given mode."""
    ensure_cai_dirs()
    spec_key = _spec_key_for_mode(mode)
    client = CMLClient()
    if spec_key == "bundled":
        client.configure_project_resources(shared_memory_limit_mb=8192)

    steps = deploy_plan(normalize_nim_deploy_mode(mode).value)
    start_build_progress(mode, steps)
    try:
        set_step("validate", "running", message="Validating configuration")
        validation = config.validate_for_deploy()
        if not validation["valid"]:
            raise RuntimeError("; ".join(validation["errors"]))
        set_step("validate", "done")

        set_step("save", "running", message="Saving configuration")
        save_mode_config(mode, config)
        set_step("save", "done")

        set_step("deploy", "running", message="Creating application")
        apps = client.list_applications()
        result = _ensure_application(client, spec_key, config, apps, recreate=True)
        _wait_for_service_running(spec_key)
        set_step("deploy", "done", detail=result["name"])

        if spec_key == "bundled":
            set_step("model", "running", message="Waiting for bundled model server")
            _wait_for_model_ready()
            set_step("model", "done")

        set_step("ready", "running")
        set_step("ready", "done")
        finish_build_progress(True, f"{SERVICE_SPECS[spec_key]['name']} deployed.")
        return {"success": True, "mode": mode, "application": result}
    except Exception as exc:
        finish_build_progress(False, str(exc))
        raise


def build_pipeline(config: AppConfig) -> dict[str, Any]:
    return deploy_application(config.nim_deploy_mode, config)


def _deployment_entry(spec_key: str, app: ApplicationInfo | None) -> dict[str, Any]:
    spec = SERVICE_SPECS[spec_key]
    app_meta = app.metadata if app else None
    app_status = (app_meta or {}).get("status", "")
    endpoints_ready = False
    if spec_key == "serverless":
        endpoints_ready = _is_app_running(app_status)
    elif spec_key == "bundled":
        nim_startup = read_nim_startup() or {}
        endpoints_ready = bool(nim_startup.get("ready")) and _is_app_running(app_status)

    entry: dict[str, Any] = {
        "key": spec_key,
        "name": spec["name"],
        "mode": spec["mode"],
        "application": app_meta,
        "app_running": _is_app_running(app_status),
        "app_failed": _is_app_failed(app_status),
        "ready": endpoints_ready and _is_app_running(app_status),
        "subdomain": (app_meta or {}).get("subdomain"),
    }
    if spec_key == "bundled":
        entry["model_startup"] = read_nim_startup()
        entry["nim_startup"] = entry["model_startup"]
    return entry


def list_deployment_status() -> dict[str, Any]:
    ensure_cai_dirs()
    launchpad = load_launchpad_config()
    deployments: dict[str, Any] = {}
    deploy_active = False
    any_failed = False
    try:
        client = CMLClient()
        apps = client.list_applications()
        for spec_key in SERVICE_SPECS:
            app = _find_app(apps, SERVICE_SPECS[spec_key]["name"])
            entry = _deployment_entry(spec_key, app)
            deployments[spec_key] = entry
            if entry["app_failed"]:
                any_failed = True
            if app and not entry["app_running"] and not entry["app_failed"]:
                deploy_active = True
    except Exception as exc:
        deployments["error"] = str(exc)

    build = reconcile_stale_build(
        pipeline_failed=any_failed,
        failed_services=[
            {"name": entry["name"], "status": entry["application"].get("status", "unknown")}
            for entry in deployments.values()
            if isinstance(entry, dict) and entry.get("app_failed") and entry.get("application")
        ],
        any_deployed_apps=any(
            isinstance(entry, dict) and entry.get("application") for entry in deployments.values()
        ),
    ) or read_build_progress()
    build_in_progress = is_build_in_progress()
    if build_in_progress:
        deploy_active = True

    active_mode = (build or {}).get("mode")
    serverless_ready = deployments.get("serverless", {}).get("ready", False)
    bundled_ready = deployments.get("bundled", {}).get("ready", False)

    return {
        "config": launchpad.public_dict() if launchpad else None,
        "config_error": None,
        "secrets_set": launchpad.secrets_set() if launchpad else {},
        "deployments": deployments,
        "services": deployments,
        "nim_deploy_mode": active_mode,
        "pipeline_ready": serverless_ready or bundled_ready,
        "serverless_ready": serverless_ready,
        "bundled_ready": bundled_ready,
        "open_ready": bundled_ready,
        "pipeline_failed": any_failed,
        "endpoints_ready": bundled_ready or serverless_ready,
        "build_in_progress": build_in_progress,
        "build": build,
        "deploy_active": deploy_active,
        "mode_summary": {
            "headline": "Launchpad — deploy Bundled (GPU + Hugging Face) or Serverless (NVIDIA NVCF) applications.",
            "detail": "Each generated app URL runs Detect and Demo with settings baked in at deploy time.",
        },
        "nim_startup": read_nim_startup(),
    }
