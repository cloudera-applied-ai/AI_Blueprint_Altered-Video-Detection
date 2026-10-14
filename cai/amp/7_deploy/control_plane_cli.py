#!/usr/bin/env python3
"""CLI for the Launchpad deployment control plane."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ.get("CDSW_PROJECT_DIR", "/home/cdsw"))))

from cai.lib.app_config import (  # noqa: E402
    AppConfig,
    load_launchpad_config,
    save_mode_config,
    validate_merged_config,
)
from cai.lib.build_progress import is_build_in_progress  # noqa: E402
from cai.lib.deployment_control import deploy_application, list_deployment_status  # noqa: E402
from cai.lib.deploy_mode import NIMDeployMode, normalize_nim_deploy_mode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="SVD Launchpad control plane")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    save_parser = sub.add_parser("save-config")
    save_parser.add_argument("--config-json", required=True)
    save_parser.add_argument("--mode", choices=["SERVERLESS", "OPEN", "BUNDLED"], required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--config-json", default="")
    validate_parser.add_argument("--mode", choices=["SERVERLESS", "OPEN", "BUNDLED"], required=True)
    deploy_parser = sub.add_parser("deploy")
    deploy_parser.add_argument("--mode", choices=["SERVERLESS", "OPEN", "BUNDLED"], required=True)
    sub.add_parser("build")
    args = parser.parse_args()

    if args.command == "status":
        print(json.dumps(list_deployment_status(), indent=2))
        return 0

    mode = normalize_nim_deploy_mode(getattr(args, "mode", None)).value if hasattr(args, "mode") else None

    if args.command == "save-config":
        data = json.loads(args.config_json)
        launchpad = load_launchpad_config()
        base = launchpad.config_for(mode) if launchpad else AppConfig.for_mode(mode, {})
        config = AppConfig.merge_update(base, {**data, "nim_deploy_mode": mode})
        path = save_mode_config(mode, config)
        print(json.dumps({"saved": str(path), "config": config.public_dict(), "mode": mode}, indent=2))
        return 0

    if args.command == "validate":
        patch = json.loads(args.config_json) if args.config_json else None
        result = validate_merged_config(patch, mode=mode)
        print(json.dumps(result, indent=2))
        return 0 if result.get("valid") else 1

    if args.command in {"deploy", "build"}:
        if is_build_in_progress():
            print(json.dumps({"error": "Deployment already in progress"}), file=sys.stderr)
            return 1
        deploy_mode = mode
        if args.command == "build":
            from cai.lib.app_config import load_app_config

            legacy = load_app_config()
            if legacy is None:
                print(json.dumps({"error": "Save configuration first"}), file=sys.stderr)
                return 1
            deploy_mode = legacy.nim_deploy_mode
        else:
            deploy_mode = args.mode
        launchpad = load_launchpad_config()
        if launchpad is None:
            print(json.dumps({"error": "Save configuration first"}), file=sys.stderr)
            return 1
        config = launchpad.config_for(deploy_mode)
        validation = config.validate_for_deploy()
        if not validation["valid"]:
            print(json.dumps({"error": "; ".join(validation["errors"])}), file=sys.stderr)
            return 1
        result = deploy_application(deploy_mode, config)
        print(json.dumps(result, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
