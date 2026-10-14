"""CAI application entry helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _script_path(relative_script: str) -> Path:
    project = Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))
    script = project / relative_script
    if not script.is_file():
        raise FileNotFoundError(f"Launcher script not found: {script}")
    return script


def run_bash_script(relative_script: str) -> int:
    """
    Run a bash launcher and block until it exits.

    CML applications execute Python entrypoints through the Jupyter kernel.
    ``os.execv`` replaces that kernel and CAI reports ``APPLICATION_FAILED`` even
    when the service script would otherwise run — use this helper instead.
    """
    return subprocess.call(["/bin/bash", str(_script_path(relative_script))])


def run_wrong_deploy_mode_message(service_label: str, *, expected: str) -> int:
    """Explain why this application slot should not run in the current deploy mode."""
    actual = os.environ.get("NIM_DEPLOY_MODE", "unknown")
    print(
        f"Skipping {service_label}: NIM_DEPLOY_MODE={actual!r} "
        f"(this application requires {expected}).",
        flush=True,
    )
    return run_serverless_nim_placeholder(service_label)


def run_serverless_nim_placeholder(service_label: str) -> int:
    """
    Hold CDSW_APP_PORT open for serverless mode without starting a GPU NIM.

    Used when ``NIM_DEPLOY_MODE=SERVERLESS`` so LipSync/ASD application slots
    stay healthy without bundled NIM processes.
    """
    project = Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))
    script = project / "cai" / "amp" / "4_services" / "run_cai_app_port.py"
    port = os.environ.get("CDSW_APP_PORT", "8100")
    print(
        f"NIM_DEPLOY_MODE=SERVERLESS — {service_label} GPU NIM not started; "
        f"holding CDSW_APP_PORT on 127.0.0.1:{port}",
        flush=True,
    )
    return subprocess.call(
        [sys.executable, str(script), "--port", str(port), "--service-label", service_label],
    )


def exec_bash_script(relative_script: str) -> None:
    """Deprecated: use ``run_bash_script`` from ``run_amp_entry`` instead."""
    raise SystemExit(run_bash_script(relative_script))


def exec_serverless_nim_placeholder(service_label: str) -> None:
    """Deprecated: use ``run_serverless_nim_placeholder`` from ``run_amp_entry`` instead."""
    raise SystemExit(run_serverless_nim_placeholder(service_label))
