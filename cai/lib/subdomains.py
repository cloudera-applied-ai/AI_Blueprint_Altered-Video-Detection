"""Project-scoped application subdomains (cluster-wide unique on CAI)."""

from __future__ import annotations

import os
import re


def _sanitize_subdomain(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]", "-", value.lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned[:63] or "svd"


def project_subdomain_suffix() -> str:
    """Stable short suffix from the CAI project id (e.g. kpq3 from klmc-hx9q-01l7-kpq3)."""
    pid = (os.environ.get("CDSW_PROJECT_ID") or os.environ.get("CML_PROJECT_ID") or "").strip()
    if not pid:
        return ""
    slug = pid.rsplit("-", 1)[-1].lower()
    slug = re.sub(r"[^a-z0-9]", "", slug)
    return slug[:12]


def unique_subdomain(base: str) -> str:
    """Return a cluster-unique subdomain for this project."""
    base = _sanitize_subdomain(base)
    suffix = project_subdomain_suffix()
    if suffix:
        return _sanitize_subdomain(f"{base}-{suffix}")
    return base
