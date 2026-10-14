"""Helpers for the Next.js Launchpad UI."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from shutil import which

from cai.lib.paths import PROJECT_ROOT

DEMO_DIR = PROJECT_ROOT / "client" / "demos"
SERVER_JS = DEMO_DIR / "dist" / "server.js"
NEXT_DIR = DEMO_DIR / ".next"


def _is_local_build_artifact(path: Path) -> bool:
    """True when dist/.next is a real project build, not a runtime symlink."""
    return path.exists() and not path.is_symlink()


def demo_ui_ready() -> bool:
    return _is_local_build_artifact(SERVER_JS) and _is_local_build_artifact(NEXT_DIR)


def demo_sources_newer_than_dist() -> bool:
    """True when Launchpad app sources changed after the last next build."""
    if not _is_local_build_artifact(SERVER_JS):
        return True
    dist_mtime = SERVER_JS.stat().st_mtime
    app_dir = DEMO_DIR / "app"
    if not app_dir.is_dir():
        return False
    for path in app_dir.rglob("*"):
        if path.is_file() and path.stat().st_mtime > dist_mtime:
            return True
    return False


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def clean_demo_build_artifacts() -> None:
    """Remove dist/ and .next/ before a fresh npm build."""
    for name in ("dist", ".next"):
        target = DEMO_DIR / name
        if target.exists() or target.is_symlink():
            print(f"Removing UI artifact: {target}", flush=True)
            _remove_path(target)


def build_demo_ui(*, clean: bool = True) -> bool:
    """Run npm install/ci + next build in the project demo directory."""
    if not which("npm"):
        print("ERROR: npm not found — SyntheticVideoDetector runtime includes Node.js", flush=True)
        return False

    if clean:
        clean_demo_build_artifacts()

    os.chdir(DEMO_DIR)
    lock = DEMO_DIR / "package-lock.json"
    install = ["npm", "ci"] if lock.is_file() else ["npm", "install"]
    for cmd in (install, ["npm", "run", "build"]):
        print("Running:", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)
    return demo_ui_ready()


def missing_demo_ui_message() -> str:
    parts = [
        f"ERROR: UI not built — missing launch artifacts under {DEMO_DIR}",
        f"  dist/server.js: {'ok' if _is_local_build_artifact(SERVER_JS) else 'MISSING'}",
        f"  .next/: {'ok' if _is_local_build_artifact(NEXT_DIR) else 'MISSING'}",
        f"  npm: {which('npm') or 'MISSING'}",
    ]
    parts.append("Run AMP step 'Build UI' before starting the Launchpad.")
    return "\n".join(parts)
