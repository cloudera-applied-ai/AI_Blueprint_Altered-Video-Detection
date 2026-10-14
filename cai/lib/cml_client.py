"""Minimal CML API v2 client for CAI application lifecycle."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from cai.lib.runtime_env import get_runtime_identifier


@dataclass
class ApplicationInfo:
    id: str
    name: str
    status: str
    subdomain: str | None
    metadata: dict[str, Any]


def cml_host() -> str:
    host = (os.environ.get("CML_HOST") or "").strip()
    if host:
        return host.rstrip("/")
    domain = (os.environ.get("CDSW_DOMAIN") or "").strip()
    if domain:
        return f"https://{domain}"
    project_url = (os.environ.get("CDSW_PROJECT_URL") or "").strip().rstrip("/")
    if project_url and "/api/v2/" in project_url:
        return project_url.split("/api/v2/")[0]
    raise RuntimeError("Set CML_HOST, CDSW_DOMAIN, or CDSW_PROJECT_URL")


def project_id() -> str:
    pid = os.environ.get("CDSW_PROJECT_ID") or os.environ.get("CML_PROJECT_ID")
    if not pid:
        raise RuntimeError("CDSW_PROJECT_ID / CML_PROJECT_ID not set")
    return pid


def api_key() -> str:
    key = os.environ.get("CDSW_APIV2_KEY") or os.environ.get("CML_API_KEY")
    if not key:
        raise RuntimeError("CDSW_APIV2_KEY / CML_API_KEY not set")
    return key


class CMLClient:
    """REST client for /api/v2/projects/{id}/applications."""

    def __init__(self, *, host: str | None = None, key: str | None = None) -> None:
        self.host = (host or cml_host()).rstrip("/")
        self.base_url = f"{self.host}/api/v2"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {key or api_key()}",
                "Content-Type": "application/json",
            }
        )

    def list_applications(self, project: str | None = None) -> list[ApplicationInfo]:
        pid = project or project_id()
        url = f"{self.base_url}/projects/{pid}/applications"
        apps: list[ApplicationInfo] = []
        page_token = ""
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            for item in data.get("applications", []):
                apps.append(
                    ApplicationInfo(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        status=item.get("status", "unknown"),
                        subdomain=item.get("subdomain"),
                        metadata=item,
                    )
                )
            page_token = data.get("next_page_token") or ""
            if not page_token:
                break
        return apps

    def create_application(
        self,
        *,
        name: str,
        script: str,
        subdomain: str,
        cpu: int,
        memory: int,
        gpu: int = 0,
        environment: dict[str, str] | None = None,
        project: str | None = None,
        runtime: str | None = None,
    ) -> ApplicationInfo:
        pid = project or project_id()
        url = f"{self.base_url}/projects/{pid}/applications"
        payload: dict[str, Any] = {
            "name": name,
            "script": script,
            "cpu": cpu,
            "memory": memory,
            "runtime_identifier": runtime or self.resolve_runtime(),
            "subdomain": subdomain,
            "bypass_authentication": True,
        }
        if gpu > 0:
            payload["nvidia_gpu"] = gpu
        if environment:
            payload["environment"] = environment
        response = self.session.post(url, json=payload, timeout=120)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Failed to create application {name!r} (HTTP {response.status_code}): {response.text}"
            )
        data = response.json()
        return ApplicationInfo(
            id=data.get("id", ""),
            name=data.get("name", name),
            status=data.get("status", "unknown"),
            subdomain=data.get("subdomain", subdomain),
            metadata=data,
        )

    def resolve_runtime(self) -> str:
        return get_runtime_identifier()

    def configure_project_resources(
        self,
        *,
        shared_memory_limit_mb: int = 8192,
        project: str | None = None,
    ) -> bool:
        """Ensure project engines get enough /dev/shm for Triton NIMs (default 8192 MB)."""
        pid = project or project_id()
        url = f"{self.base_url}/projects/{pid}"
        response = self.session.patch(
            url,
            json={"shared_memory_limit": shared_memory_limit_mb},
            timeout=60,
        )
        return response.status_code in {200, 202}

    def get_application(self, app_id: str, project: str | None = None) -> ApplicationInfo:
        pid = project or project_id()
        url = f"{self.base_url}/projects/{pid}/applications/{app_id}"
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        return ApplicationInfo(
            id=data.get("id", app_id),
            name=data.get("name", ""),
            status=data.get("status", "unknown"),
            subdomain=data.get("subdomain"),
            metadata=data,
        )

    def restart_application(self, app_id: str, project: str | None = None) -> bool:
        pid = project or project_id()
        url = f"{self.base_url}/projects/{pid}/applications/{app_id}:restart"
        response = self.session.post(url, timeout=60)
        return response.status_code in {200, 202, 204}

    def delete_application(self, app_id: str, project: str | None = None) -> bool:
        pid = project or project_id()
        url = f"{self.base_url}/projects/{pid}/applications/{app_id}"
        response = self.session.delete(url, timeout=120)
        return response.status_code in {200, 204, 404}
