#!/usr/bin/env python3
"""All-in-one Bundled SVD application: Hugging Face model server + Detect UI in one GPU pod."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))))

from cai.lib.amp_runtime import run_amp_entry  # noqa: E402
from cai.lib.open_model_supervisor import start_open_model_supervisor  # noqa: E402
from cai.lib.paths import ensure_cai_dirs  # noqa: E402
from cai.lib.runtime_app import start_runtime_ui  # noqa: E402
from cai.lib.runtime_env import log_runtime_context  # noqa: E402
from cai.lib.service_env import load_config_defaults  # noqa: E402


def main() -> int:
    log_runtime_context()
    load_config_defaults()
    ensure_cai_dirs()

    os.environ.setdefault("NIM_DEPLOY_MODE", "BUNDLED")
    os.environ.setdefault("SVD_DEPLOY_MODE", "BUNDLED")
    os.environ.setdefault("SVD_APP_ROLE", "runtime")
    os.environ.setdefault("NEXT_PUBLIC_SVD_APP_ROLE", "runtime")

    start_open_model_supervisor()
    return start_runtime_ui()


run_amp_entry(main, __name__)
