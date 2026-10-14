#!/usr/bin/env python3
"""All-in-one Serverless SVD application: NVCF endpoints + detection UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))))

from cai.lib.amp_runtime import run_amp_entry  # noqa: E402
from cai.lib.app_config import AppConfig  # noqa: E402
from cai.lib.deploy_mode import NIMDeployMode  # noqa: E402
from cai.lib.paths import ensure_cai_dirs  # noqa: E402
from cai.lib.runtime_app import start_runtime_ui, wire_serverless_runtime_endpoints  # noqa: E402
from cai.lib.runtime_env import log_runtime_context  # noqa: E402
from cai.lib.service_env import load_config_defaults  # noqa: E402


def main() -> int:
    log_runtime_context()
    load_config_defaults()
    ensure_cai_dirs()
    os.environ["NIM_DEPLOY_MODE"] = NIMDeployMode.SERVERLESS.value

    config = AppConfig.from_environ(mode=NIMDeployMode.SERVERLESS)
    config.apply_to_environ()
    if not config.ngc_api_key.strip():
        print("ERROR: NGC_API_KEY is empty", flush=True)
        return 1

    wire_serverless_runtime_endpoints(config)
    print("Serverless runtime endpoints configured.", flush=True)
    return start_runtime_ui()


run_amp_entry(main, __name__)
