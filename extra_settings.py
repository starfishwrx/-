from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExtraSettings:
    timezone: str
    request_timeout: int
    query_proxy_url: str
    hosts_yaml_path: str
    query_debug_log_path: Path
    fenxi_base: str
    manage_base: str
