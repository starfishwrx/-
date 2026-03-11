#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extra_metrics_service import ExtraMetricsService, ExtraSettings
from generate_daily_report import load_extra_auth


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验会员模块数据是否完整可用（缺失即失败）")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="config yaml path")
    parser.add_argument("--extra-auth-file", type=Path, default=Path("extra_auth.json"), help="extra_auth.json path")
    parser.add_argument("--date", type=str, required=True, help="query date, format YYYY-MM-DD")
    parser.add_argument(
        "--allow-missing-valid-count",
        action="store_true",
        help="允许有效期内会员数缺失（默认不允许）",
    )
    return parser.parse_args()


def _load_settings(config_path: Path) -> ExtraSettings:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    extra_cfg = cfg.get("extra_metrics") or {}
    return ExtraSettings(
        timezone=str(extra_cfg.get("timezone", "Asia/Shanghai")),
        request_timeout=int(extra_cfg.get("request_timeout", 30)),
        query_proxy_url=str(extra_cfg.get("query_proxy_url", "")).strip(),
        hosts_yaml_path=str(extra_cfg.get("hosts_yaml_path", "")).strip(),
        query_debug_log_path=(PROJECT_ROOT / "output" / "query_debug_member_verify.jsonl"),
        fenxi_base=str(extra_cfg.get("fenxi_base", "https://fenxi.4399dev.com")).strip(),
        manage_base=str(extra_cfg.get("manage_base", "http://manage.5054399.com")).strip(),
    )


def _to_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        raw = value.replace(",", "").replace("%", "").strip()
        if not raw:
            return 0
        try:
            return int(float(raw))
        except ValueError:
            return 0
    return 0


def _is_percent(text: str) -> bool:
    s = str(text or "").strip().replace("％", "%")
    return bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?%", s))


def _validate_member_notes(notes: dict[str, Any], allow_missing_valid_count: bool) -> None:
    pay_rate = str(notes.get("member_pay_rate") or "").strip()
    recharge_amount = _to_int(notes.get("member_recharge_amount"))
    recharge_week_ratio = str(notes.get("member_recharge_week_ratio") or "").strip().replace("％", "%")
    open_count = _to_int(notes.get("member_open_count"))
    valid_count = _to_int(notes.get("member_valid_count"))

    if not _is_percent(pay_rate):
        raise AssertionError(f"member_pay_rate 格式错误: {pay_rate!r}")
    if recharge_amount <= 0:
        raise AssertionError(f"member_recharge_amount 无效: {recharge_amount}")
    if (not _is_percent(recharge_week_ratio)) and (recharge_week_ratio.upper() != "N/A"):
        raise AssertionError(f"member_recharge_week_ratio 格式错误: {recharge_week_ratio!r}")
    if open_count <= 0:
        raise AssertionError(f"member_open_count 无效: {open_count}")
    if (not allow_missing_valid_count) and valid_count <= 0:
        raise AssertionError(f"member_valid_count 无效: {valid_count}")


async def _run_check(settings: ExtraSettings, query_date: date, fenxi_auth: dict[str, Any]) -> dict[str, Any]:
    service = ExtraMetricsService(settings)
    data = await service._fetch_fenxi_metrics(query_date=query_date, auth=fenxi_auth)
    notes = data.get("notes") or {}
    if not isinstance(notes, dict):
        raise AssertionError("会员模块 notes 结构异常")
    return notes


def main() -> None:
    args = _parse_args()
    if not args.config.exists():
        raise FileNotFoundError(f"配置文件不存在: {args.config}")
    if not args.extra_auth_file.exists():
        raise FileNotFoundError(f"认证文件不存在: {args.extra_auth_file}")

    query_date = date.fromisoformat(str(args.date).strip())
    settings = _load_settings(args.config)
    extra_auth = load_extra_auth(args.extra_auth_file)
    fenxi_auth = extra_auth.get("fenxi")
    if not fenxi_auth:
        raise RuntimeError("extra_auth.json 缺少 fenxi 登录态")

    notes = asyncio.run(_run_check(settings, query_date, fenxi_auth))
    _validate_member_notes(notes, allow_missing_valid_count=bool(args.allow_missing_valid_count))

    print(
        json.dumps(
            {
                "ok": True,
                "date": query_date.isoformat(),
                "member_pay_rate": notes.get("member_pay_rate"),
                "member_recharge_amount": notes.get("member_recharge_amount"),
                "member_recharge_week_ratio": notes.get("member_recharge_week_ratio"),
                "member_open_count": notes.get("member_open_count"),
                "member_valid_count": notes.get("member_valid_count"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
