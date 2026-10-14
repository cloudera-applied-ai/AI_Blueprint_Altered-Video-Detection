"""Start local Hugging Face open-weights detector for OPEN deploy mode."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests

from cai.lib.app_config import AppConfig
from cai.lib.deploy_mode import NIMDeployMode
from cai.lib.nim_startup import mark_nim_startup_error, reset_nim_startup, tail_log, update_nim_startup
from cai.lib.paths import CONFIG_DIR
from cai.lib.open_port import resolve_open_model_port
from cai.lib.runtime_app import wire_open_runtime_endpoints

PROJECT_ROOT = Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))
MODEL_LOG = CONFIG_DIR / "svd_open_model.log"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _gpu_visible() -> bool:
    try:
        subprocess.run(["nvidia-smi", "-L"], capture_output=True, check=True, timeout=15)
        return True
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return False


def _wait_for_health(port: int, proc: subprocess.Popen, *, timeout_s: int = 3600) -> None:
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        code = proc.poll()
        if code is not None:
            lines = tail_log(MODEL_LOG, lines=8)
            hint = lines[-1] if lines else "see svd_open_model.log"
            raise RuntimeError(
                f"Open model server exited with code {code} before /health was ready ({hint})"
            )
        try:
            r = requests.get(f"{base}/health", timeout=5)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise TimeoutError(f"Open model server did not become healthy on {base}")


def _readiness_worker(port: int, proc: subprocess.Popen) -> None:
    try:
        update_nim_startup("model_loading", "Loading Hugging Face model (first start may take several minutes)")
        _wait_for_health(port, proc)
        wire_open_runtime_endpoints(port=port)
        update_nim_startup(
            "endpoints_published",
            f"Open model ready at 127.0.0.1:{port}",
            ready=True,
            checks={"endpoints_published": True, "model_server_ready": True},
        )
        _log(f"Open model server ready on port {port}")
    except Exception as exc:
        mark_nim_startup_error(str(exc))
        _log(f"Open model readiness failed: {exc}")


def _start_model_server(port: int) -> subprocess.Popen:
    MODEL_LOG.parent.mkdir(parents=True, exist_ok=True)
    MODEL_LOG.write_text("")
    env = os.environ.copy()
    env["SVD_OPEN_PORT"] = str(port)
    env.setdefault("PYTHONPATH", str(PROJECT_ROOT))
    cmd = [sys.executable, "-m", "src.svd.open_server"]
    _log(f"Starting open model server: {' '.join(cmd)} (log: {MODEL_LOG})")
    log_handle = MODEL_LOG.open("a")
    return subprocess.Popen(
        cmd,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(PROJECT_ROOT),
    )


def start_open_model_supervisor() -> None:
    reset_nim_startup(message="Open-weights runtime starting")
    update_nim_startup("starting", "Initializing open-weights runtime application")

    if not _gpu_visible():
        mark_nim_startup_error("GPU not visible (nvidia-smi failed)")
        raise RuntimeError("GPU not visible (nvidia-smi failed)")
    update_nim_startup("gpu_check", "GPU visible", checks={"gpu_visible": True})

    config = AppConfig.from_environ(mode=NIMDeployMode.BUNDLED)
    config.apply_to_environ()
    port = resolve_open_model_port()
    update_nim_startup(
        "config_applied",
        "Configuration applied",
        checks={"config_applied": True},
    )
    wire_open_runtime_endpoints(port=port)
    update_nim_startup(
        "endpoints_wired",
        f"Detection will use open model on 127.0.0.1:{port}",
        checks={"endpoints_wired": True},
    )

    proc = _start_model_server(port)
    update_nim_startup(
        "model_process_started",
        f"Open model server started (pid {proc.pid})",
        checks={"model_process_started": True},
    )
    thread = threading.Thread(
        target=_readiness_worker,
        args=(port, proc),
        daemon=True,
        name="svd-open-model-readiness",
    )
    thread.start()
