"""Shared helpers for all-in-one SVD runtime applications (serverless or open weights)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shutil import which

from cai.lib.cai_common import apply_dotenv_to_os
from cai.lib.demo_ui import DEMO_DIR, SERVER_JS, demo_ui_ready, missing_demo_ui_message
from cai.lib.open_port import DEFAULT_OPEN_MODEL_PORT, resolve_open_model_port
from cai.lib.paths import ENDPOINTS_ENV, ensure_cai_dirs


def _local_grpc_host(server: str) -> bool:
    host = server.split(":")[0].strip().lower() if server else ""
    return host in {"127.0.0.1", "localhost", "0.0.0.0"}


def start_runtime_ui() -> int:
    """Start the Next.js detection UI on CDSW_APP_PORT (foreground)."""
    ensure_cai_dirs()
    baked_mode = os.environ.get("NIM_DEPLOY_MODE", "BUNDLED")
    baked_server = os.environ.get("SVD_SERVER", "")
    if ENDPOINTS_ENV.is_file():
        apply_dotenv_to_os(ENDPOINTS_ENV)
    os.environ["NIM_DEPLOY_MODE"] = baked_mode
    if baked_mode.upper() in {"BUNDLED", "OPEN", "OPEN_WEIGHTS"}:
        open_port = resolve_open_model_port()
        os.environ.setdefault("SVD_OPEN_SERVER", f"http://127.0.0.1:{open_port}")

    port = os.environ.get("CDSW_APP_PORT") or os.environ.get("PORT") or "8080"
    os.environ["PORT"] = str(port)
    os.environ.setdefault("NODE_ENV", "production")
    os.environ.setdefault("SVD_APP_ROLE", "runtime")
    os.environ.setdefault("NEXT_PUBLIC_SVD_APP_ROLE", "runtime")
    mode = os.environ.get("NIM_DEPLOY_MODE", "OPEN")
    os.environ.setdefault("NEXT_PUBLIC_NIM_DEPLOY_MODE", mode)

    if not demo_ui_ready():
        print(missing_demo_ui_message(), flush=True)
        return 1

    node = which("node") or "/usr/bin/node"
    if not Path(node).is_file():
        print(f"ERROR: node not found (tried {node})", flush=True)
        return 1

    os.chdir(DEMO_DIR)
    print(f"Starting SVD runtime UI: {node} {SERVER_JS} on 127.0.0.1:{port}", flush=True)
    return subprocess.call([node, str(SERVER_JS)])


def wire_open_runtime_endpoints(*, port: int = DEFAULT_OPEN_MODEL_PORT) -> None:
    """Write local runtime endpoints for open-weights model server in this pod."""
    from cai.lib.cai_common import write_dotenv_file
    from cai.lib.deploy_mode import NIMDeployMode

    write_dotenv_file(
        ENDPOINTS_ENV,
        {
            "SVD_OPEN_SERVER": f"http://127.0.0.1:{port}",
            "SVD_OPEN_PORT": str(port),
            "NIM_DEPLOY_MODE": NIMDeployMode.BUNDLED.value,
            "SVD_SSL_MODE": "DISABLED",
        },
    )


def wire_bundled_runtime_endpoints(*, grpc_port: int = 8001) -> None:
    wire_open_runtime_endpoints(port=resolve_open_model_port())


def wire_serverless_runtime_endpoints(config) -> None:
    """Write local runtime endpoints for serverless NVCF in this pod."""
    from cai.lib.cai_common import write_dotenv_file
    from cai.lib.deploy_mode import NIMDeployMode, write_serverless_endpoints_json

    write_serverless_endpoints_json()
    write_dotenv_file(
        ENDPOINTS_ENV,
        {
            "SVD_SERVER": f"{config.nvidia_serverless_grpc_host}:{config.nvidia_serverless_grpc_port}",
            "NIM_DEPLOY_MODE": NIMDeployMode.SERVERLESS.value,
            "SVD_SSL_MODE": "TLS",
        },
    )
