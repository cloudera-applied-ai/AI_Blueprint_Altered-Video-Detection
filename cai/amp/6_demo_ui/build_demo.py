#!/usr/bin/env python3
"""Build Next.js UI in the CAI project workspace (AMP step 2)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))))

from cai.lib.amp_runtime import run_amp_entry  # noqa: E402
from cai.lib.demo_ui import (  # noqa: E402
    SERVER_JS,
    build_demo_ui,
    demo_sources_newer_than_dist,
    demo_ui_ready,
)


def main() -> int:
    force = bool(os.environ.get("FORCE_DEMO_BUILD", "").strip())

    if demo_ui_ready() and not force and not demo_sources_newer_than_dist():
        print(f"UI already built ({SERVER_JS}) — skipping npm build")
        print("Set FORCE_DEMO_BUILD=1 to rebuild after code changes.")
        return 0

    print("Building Next.js UI in project workspace ...", flush=True)
    try:
        if build_demo_ui():
            print(f"UI built ({SERVER_JS})")
            return 0
    except subprocess.CalledProcessError:
        return 1

    print(f"ERROR: build finished but {SERVER_JS} is missing")
    return 1


run_amp_entry(main, __name__)
