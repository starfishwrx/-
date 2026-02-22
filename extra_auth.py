from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote

TOKEN_RE = re.compile(r"access_token=([^&\"'\s<>]+)")


def _extract_token(text: str) -> Optional[str]:
    if not text:
        return None
    match = TOKEN_RE.search(unquote(text))
    if match:
        return match.group(1)
    return None


def _parse_cookie_header(value: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for segment in value.split(";"):
        part = segment.strip()
        if not part or "=" not in part:
            continue
        name, raw_val = part.split("=", 1)
        key = name.strip()
        if key:
            out[key] = raw_val.strip()
    return out


def _collect_auth_data(har_paths: Iterable[Path], platform: str) -> Dict[str, Any]:
    cookies: Dict[str, str] = {}
    headers: Dict[str, str] = {}
    token_candidates: List[str] = []
    bootstrap_candidates: List[str] = []

    for path in har_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("log", {}).get("entries", []):
            req = entry.get("request", {})
            req_url = str(req.get("url") or "")
            req_headers = {str(h.get("name", "")): str(h.get("value", "")) for h in req.get("headers", [])}
            req_headers_lower = {k.lower(): v for k, v in req_headers.items()}

            for item in req.get("cookies", []):
                name = str(item.get("name") or "").strip()
                value = str(item.get("value") or "").strip()
                if name and value:
                    cookies[name] = value

            cookie_header = req_headers.get("Cookie") or req_headers.get("cookie")
            if cookie_header:
                cookies.update(_parse_cookie_header(cookie_header))

            header_token = (
                req_headers.get("X-Access-Token")
                or req_headers.get("x-access-token")
                or req_headers_lower.get("x-access-token")
            )
            if header_token:
                token_candidates.append(header_token.strip())

            if platform == "fenxi":
                if "event-analysis-server" in req_url:
                    if req_headers.get("mediaids"):
                        headers["mediaids"] = req_headers["mediaids"]
                    if req_headers.get("topic"):
                        headers["topic"] = req_headers["topic"]
                    if req_headers.get("Mediaids") and "mediaids" not in headers:
                        headers["mediaids"] = req_headers["Mediaids"]
                    if req_headers.get("Topic") and "topic" not in headers:
                        headers["topic"] = req_headers["Topic"]

                token = _extract_token(req_url)
                if token:
                    token_candidates.append(token)
                    bootstrap_candidates.append(req_url)

            if platform == "505":
                token = _extract_token(req_url)
                if token:
                    token_candidates.append(token)
                    bootstrap_candidates.append(req_url)

            for hdr in entry.get("response", {}).get("headers", []):
                if str(hdr.get("name", "")).lower() != "location":
                    continue
                loc = str(hdr.get("value") or "")
                token = _extract_token(loc)
                if token:
                    token_candidates.append(token)
                    bootstrap_candidates.append(loc)

    platform_hint = "qz4399doc" if platform == "fenxi" else "manage505"
    token = ""
    for cand in token_candidates:
        if platform_hint in cand:
            token = cand
            break
    if not token and token_candidates:
        token = token_candidates[0]

    bootstrap_url = ""
    for cand in bootstrap_candidates:
        if token and token in cand:
            bootstrap_url = cand
            break
    if not bootstrap_url and bootstrap_candidates:
        bootstrap_url = bootstrap_candidates[0]

    if token and bootstrap_url:
        bootstrap_url = bootstrap_url.replace(token, "{access_token}")

    out_headers = dict(headers)
    if token:
        out_headers.setdefault("X-Access-Token", token)

    return {
        "cookies": cookies,
        "headers": out_headers,
        "token": token,
        "bootstrap_url_template": bootstrap_url,
    }


def build_extra_auth_file(
    fenxi_hars: Iterable[Path],
    manage_hars: Iterable[Path],
    output_path: Path,
) -> Path:
    fenxi_paths = [Path(p) for p in fenxi_hars]
    manage_paths = [Path(p) for p in manage_hars]
    payload = {
        "fenxi": _collect_auth_data(fenxi_paths, "fenxi"),
        "505": _collect_auth_data(manage_paths, "505"),
        "meta": {
            "fenxi_hars": [str(p) for p in fenxi_paths],
            "manage_hars": [str(p) for p in manage_paths],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def load_extra_auth(path: Path) -> Dict[str, Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Any]] = {}
    for key in ("fenxi", "505"):
        raw = data.get(key) or {}
        token = str(raw.get("token") or "").strip()
        template = str(raw.get("bootstrap_url_template") or "").strip()
        bootstrap_url = template
        if token and template and "{access_token}" in template:
            bootstrap_url = template.replace("{access_token}", token)

        headers = raw.get("headers") if isinstance(raw.get("headers"), dict) else {}
        cookies = raw.get("cookies") if isinstance(raw.get("cookies"), dict) else {}

        clean_headers = {}
        for hk, hv in headers.items():
            if isinstance(hk, str) and isinstance(hv, str):
                clean_headers[hk] = hv

        clean_cookies = {}
        for ck, cv in cookies.items():
            if isinstance(ck, str) and isinstance(cv, str):
                clean_cookies[ck] = cv

        if token and "X-Access-Token" not in clean_headers:
            clean_headers["X-Access-Token"] = token

        out[key] = {
            "cookies": clean_cookies,
            "headers": clean_headers,
            "bootstrap_url": bootstrap_url,
            "token": token,
        }
    return out


def load_extra_auth_meta(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("meta")
    if isinstance(meta, dict):
        return meta
    return {}
