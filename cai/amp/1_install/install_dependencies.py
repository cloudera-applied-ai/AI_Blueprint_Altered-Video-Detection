#!/usr/bin/env python3
"""AMP session: install deps for Launchpad, Bundled HF, and Serverless NVCF paths."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shutil import which

sys.path.insert(0, str(Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))))

from cai.lib.amp_runtime import run_amp_entry  # noqa: E402
from cai.lib.paths import PROJECT_ROOT  # noqa: E402


def main() -> int:
    os.chdir(PROJECT_ROOT)
    print(f"Installing into runtime Python: {sys.executable}")
    extra_arg = ".[open,serverless,test]"
    if which("uv"):
        subprocess.run(
            ["uv", "pip", "install", "--python", sys.executable, "-e", extra_arg],
            check=True,
        )
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", extra_arg], check=True)

    subprocess.run(["bash", "protos/generate_protos.sh"], check=True)
    from src.svd.patch_grpc_stub import ensure_grpc_stub  # noqa: WPS433

    ensure_grpc_stub()
    print("Dependencies and NVCF protobuf stubs ready (Bundled + Serverless).")
    return 0


run_amp_entry(main, __name__)
