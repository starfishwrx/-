from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse, urlunparse


HOST_LINE_RE = re.compile(r"^\s*'([^']+)':\s*([0-9.]+)\s*$")


@lru_cache(maxsize=8)
def load_hosts_map(yaml_path: str) -> dict[str, str]:
    path = Path(yaml_path).expanduser()
    if not yaml_path or not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = HOST_LINE_RE.match(line)
        if not m:
            continue
        out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def rewrite_url_with_hosts_map(url: str, hosts_map: dict[str, str]) -> Tuple[str, str | None]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return url, None
    mapped_ip = hosts_map.get(host)
    if not mapped_ip:
        return url, None
    if parsed.scheme != "http":
        return url, None

    original_host_header = parsed.netloc
    if parsed.port:
        netloc = f"{mapped_ip}:{parsed.port}"
    else:
        netloc = mapped_ip
    rewritten = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return rewritten, original_host_header
