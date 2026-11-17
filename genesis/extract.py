"""Read-only export adapter. It never invokes ServiceNow write operations."""
import json
import os
from urllib.parse import urlsplit

import httpx

from .model import Snapshot


def extract(url: str, *, token: str | None = None, username: str | None = None,
            password: str | None = None, transport=None) -> Snapshot:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not (parsed.hostname or "").endswith(".service-now.com")
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or not parsed.path.startswith("/api/") or parsed.query or parsed.fragment):
        raise ValueError("Use an HTTPS *.service-now.com /api/ export endpoint without query or credentials")
    if token and (username or password):
        raise ValueError("Choose bearer token OR basic authentication")
    if not token and not (username and password):
        raise ValueError("Set SN_TOKEN or both SN_USERNAME and SN_PASSWORD")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(transport=transport, timeout=20, follow_redirects=False, trust_env=False) as client:
            with client.stream("GET", url, headers=headers,
                               auth=(username, password) if not token else None) as response:
                if response.status_code != 200:
                    raise ValueError(f"Export failed (HTTP {response.status_code}); check instance access and API configuration")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 65536:
                        raise ValueError("Export exceeded 64 KiB limit")
        payload = json.loads(data)
        if isinstance(payload, dict) and "result" in payload:
            payload = payload["result"]
        snapshot = Snapshot.model_validate(payload)
        if snapshot.source.kind != "servicenow_export":
            raise ValueError("Expected a ServiceNow export, not an offline fixture")
        return snapshot
    except httpx.HTTPError as exc:
        raise ValueError("ServiceNow export connection failed; check instance availability and TLS") from None


def from_environment() -> Snapshot:
    return extract(os.environ.get("SN_EXPORT_URL", ""), token=os.getenv("SN_TOKEN"),
                   username=os.getenv("SN_USERNAME"), password=os.getenv("SN_PASSWORD"))
