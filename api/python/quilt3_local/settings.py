from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse

OBJECT_BACKEND_AWS = "aws"
OBJECT_BACKEND_FILESYSTEM = "filesystem"


def object_backend() -> str:
    return os.getenv("QUILT_LOCAL_OBJECT_BACKEND", OBJECT_BACKEND_AWS).strip().lower()


def filesystem_mode() -> bool:
    return object_backend() == OBJECT_BACKEND_FILESYSTEM


def data_dir() -> Path | None:
    value = os.getenv("QUILT_LOCAL_DATA_DIR")
    if not value:
        return None
    return Path(value).expanduser().resolve()


def default_region() -> str:
    return os.getenv("QUILT_LOCAL_DEFAULT_REGION", "us-east-1")


def local_origin() -> str:
    return os.getenv("QUILT_LOCAL_ORIGIN", "http://localhost:3000")


def _is_loopback_host(hostname: str | None) -> bool:
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    if hostname is None:
        return False
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _same_local_host(left: str | None, right: str | None) -> bool:
    if left == right:
        return True
    return _is_loopback_host(left) and _is_loopback_host(right)


def is_local_proxy_url(url: str) -> bool:
    parsed = urlparse(url, allow_fragments=False)
    if parsed.scheme not in {"http", "https"}:
        return False
    local = urlparse(local_origin(), allow_fragments=False)
    return (
        parsed.port == local.port
        and _same_local_host(parsed.hostname, local.hostname)
        and parsed.path.startswith("/__s3proxy/")
    )


def fake_credentials() -> dict:
    return {
        "AccessKeyId": "LOCALMODEACCESSKEY",
        "SecretAccessKey": "LOCALMODESECRETKEY",
        "SessionToken": "LOCALMODESESSIONTOKEN",
        "Expiration": None,
    }
