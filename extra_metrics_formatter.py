from __future__ import annotations

from typing import Any, Dict, List


def _fmt_num(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{int(round(value)):,}"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "暂未获取"
        try:
            return f"{int(round(float(text.replace(',', '')))):,}"
        except ValueError:
            return text
    return "暂未获取"


def _trend_ratio_text(ratio: str) -> str:
    text = ratio.strip()
    if not text:
        return "暂未获取"
    if text.startswith("+"):
        return f"上涨{text[1:]}"
    if text.startswith("-"):
        return f"下降{text[1:]}"
    return text


def _trend_delta_text(delta: Any) -> str:
    try:
        iv = int(delta)
    except (TypeError, ValueError):
        return "暂未获取"
    if iv > 0:
        return f"上涨{iv:,}元"
    if iv < 0:
        return f"下降{abs(iv):,}元"
    return "持平0元"


def render_extra_metrics_block(extra_metrics: Dict[str, Any]) -> str:
    notes = extra_metrics.get("notes", {}) if isinstance(extra_metrics, dict) else {}
    top_games = extra_metrics.get("top_games", []) if isinstance(extra_metrics, dict) else []
    warnings = extra_metrics.get("warnings", []) if isinstance(extra_metrics, dict) else []
    payment_images = extra_metrics.get("payment_images", {}) if isinstance(extra_metrics, dict) else {}

    lines: List[str] = []
    lines.append("备注：")

    new_users = notes.get("new_users", {})
    active_users = notes.get("active_users", {})
    if new_users:
        lines.append(
            "1、新增用户为：%s，与昨日同期环比%s，与上周同期对比%s。"
            % (
                _fmt_num(new_users.get("value")),
                _trend_ratio_text(str(new_users.get("day_ratio") or "")),
                _trend_ratio_text(str(new_users.get("week_ratio") or "")),
            )
        )
    else:
        lines.append("1、新增用户：暂未获取。")

    if active_users:
        lines.append(
            "2、活跃用户为：%s，与昨日同期环比%s，与上周同期对比%s。"
            % (
                _fmt_num(active_users.get("value")),
                _trend_ratio_text(str(active_users.get("day_ratio") or "")),
                _trend_ratio_text(str(active_users.get("week_ratio") or "")),
            )
        )
    else:
        lines.append("2、活跃用户：暂未获取。")

    lines.append("3、会员充值明细：")
    lines.append(
        "①、会员付费率为：%s，会员充值总金额为：%s元，与上周同期对比%s。"
        % (
            str(notes.get("member_pay_rate") or "暂未获取"),
            _fmt_num(notes.get("member_recharge_amount")),
            _trend_ratio_text(str(notes.get("member_recharge_week_ratio") or "")),
        )
    )
    lines.append(
        "②、今日云玩会员开通人数为：%s人，有效期内会员数为：%s人。"
        % (
            _fmt_num(notes.get("member_open_count")),
            _fmt_num(notes.get("member_valid_count")),
        )
    )

    lines.append("4、充值明细：")
    lines.append(
        "①、页游充值（工作web+厦门夜游）为：%s元，与上周同期对比%s。"
        % (
            _fmt_num(notes.get("web_night_recharge")),
            _trend_delta_text(notes.get("web_night_recharge_week_delta")),
        )
    )
    lines.append(
        "②、手游充值为：%s元，与上周同期对比%s。"
        % (
            _fmt_num(notes.get("mobile_recharge")),
            _trend_delta_text(notes.get("mobile_recharge_week_delta")),
        )
    )

    if warnings:
        lines.append("备注：部分外部接口未取到数据 -> %s" % "；".join(str(w) for w in warnings))

    if top_games:
        lines.append("—————————————————————")
        lines.append("二、云游戏活跃用户top(去重)")
        lines.append("")
        lines.append("| 游戏 | 活跃用户数 |")
        lines.append("| :---: | :---: |")
        for item in top_games:
            lines.append("| %s | %s |" % (str(item.get("name") or "-"), _fmt_num(item.get("active_users"))))

    if isinstance(payment_images, dict) and payment_images:
        lines.append("")
        lines.append("具体：")
        page_img = str(payment_images.get("page") or "").strip()
        mobile_img = str(payment_images.get("mobile") or "").strip()
        if page_img:
            lines.append(f"页游付费表图片：{page_img}")
        if mobile_img:
            lines.append(f"手游付费表图片：{mobile_img}")

    return "\n".join(lines)
