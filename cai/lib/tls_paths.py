"""Resolve TLS certificate bundle paths for CAI launchers."""

from __future__ import annotations

import os
from pathlib import Path


def default_ssl_root_cert_path() -> str:
    """Return a CA bundle path for verifying public TLS servers (e.g. NVCF)."""
    override = os.environ.get("CONTROLLER_NIM_SSL_ROOT_CERT", "").strip()
    if override:
        path = Path(override)
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"CONTROLLER_NIM_SSL_ROOT_CERT not found: {override}")

    for candidate in (
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/cert.pem",
    ):
        if Path(candidate).is_file():
            return candidate

    try:
        import certifi

        bundle = certifi.where()
        if Path(bundle).is_file():
            return bundle
    except ImportError:
        pass

    raise RuntimeError(
        "No CA certificate bundle found for NVCF TLS. "
        "Install ca-certificates or set CONTROLLER_NIM_SSL_ROOT_CERT."
    )
