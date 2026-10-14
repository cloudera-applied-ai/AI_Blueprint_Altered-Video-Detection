#!/usr/bin/env python3
"""Start the Synthetic Video Detector Launchpad (Next.js UI)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shutil import which

sys.path.insert(0, str(Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))))

from cai.lib.amp_runtime import run_amp_entry  # noqa: E402
from cai.lib.app_config import apply_persisted_config  # noqa: E402
from cai.lib.cai_common import apply_dotenv_to_os  # noqa: E402
from cai.lib.demo_ui import (  # noqa: E402
    DEMO_DIR,
    SERVER_JS,
    demo_ui_ready,
    missing_demo_ui_message,
)
from cai.lib.paths import ENDPOINTS_ENV, ensure_cai_dirs  # noqa: E402
from cai.lib.runtime_env import log_runtime_context  # noqa: E402
from cai.lib.service_env import load_config_defaults  # noqa: E402


def main() -> int:
    try:
        log_runtime_context()
        load_config_defaults()
        if ENDPOINTS_ENV.exists():
            apply_dotenv_to_os(ENDPOINTS_ENV)
        apply_persisted_config()
        ensure_cai_dirs()
    except Exception as exc:
        print(f"WARNING: startup configuration step failed: {exc}", flush=True)

    port = os.environ.get("CDSW_APP_PORT") or os.environ.get("PORT") or "8080"
    os.environ["PORT"] = str(port)
    os.environ.setdefault("NODE_ENV", "production")
    os.environ.setdefault("SVD_APP_ROLE", "launchpad")
    os.environ.setdefault("NEXT_PUBLIC_SVD_APP_ROLE", "launchpad")

    if not demo_ui_ready():
        print(missing_demo_ui_message(), flush=True)
        return 1

    print(f"Launchpad UI artifacts: {SERVER_JS}", flush=True)

    node = which("node") or "/usr/bin/node"
    if not Path(node).is_file():
        print(f"ERROR: node not found (tried {node})", flush=True)
        return 1

    os.chdir(DEMO_DIR)
    print(f"Starting Launchpad (deploy control): {node} {SERVER_JS} on 127.0.0.1:{port}", flush=True)
    return subprocess.call([node, str(SERVER_JS)])


run_amp_entry(main, __name__)
