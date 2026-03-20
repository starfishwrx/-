from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_RUNTIME_AUTH_FILENAME = "runtime_auth.yaml"


def resolve_runtime_auth_path(config_path: Path | str, explicit_path: Path | str | None = None) -> Path:
    if explicit_path is not None and str(explicit_path).strip():
        return Path(explicit_path).expanduser().resolve()
    return Path(config_path).expanduser().resolve().parent / DEFAULT_RUNTIME_AUTH_FILENAME


def load_runtime_auth(path: Path | str) -> Dict[str, Any]:
    auth_path = Path(path)
    if not auth_path.exists():
        return {}
    try:
        data = yaml.safe_load(auth_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def save_runtime_auth(path: Path | str, payload: Dict[str, Any]) -> Path:
    auth_path = Path(path)
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return auth_path


def normalize_870_session_cookie(raw_value: str) -> str:
    text = str(raw_value or "").strip()
    if not text:
        raise ValueError("PHPSESSID 不能为空。")

    if text.lower().startswith("cookie:"):
        text = text.split(":", 1)[1].strip()

    if ";" in text:
        for part in text.split(";"):
            item = part.strip()
            if item.startswith("PHPSESSID="):
                value = item.split("=", 1)[1].strip()
                if value:
                    return f"PHPSESSID={value}"
        raise ValueError("未在 Cookie 字符串中找到 PHPSESSID。")

    if text.startswith("PHPSESSID="):
        value = text.split("=", 1)[1].strip()
        if not value:
            raise ValueError("PHPSESSID 不能为空。")
        return f"PHPSESSID={value}"

    if "=" not in text:
        return f"PHPSESSID={text}"

    raise ValueError("请输入 PHPSESSID 值、PHPSESSID=... 或包含 PHPSESSID 的完整 Cookie 字符串。")


def get_runtime_session_cookie(path: Path | str) -> str:
    payload = load_runtime_auth(path)
    value = str(payload.get("session_cookie") or "").strip()
    return value


def save_runtime_session_cookie(path: Path | str, raw_value: str) -> Path:
    cookie = normalize_870_session_cookie(raw_value)
    payload = load_runtime_auth(path)
    payload["session_cookie"] = cookie
    return save_runtime_auth(path, payload)
