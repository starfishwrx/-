#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from feishu_doc import (
    FeishuDocSettings,
    FeishuDocError,
    _fetch_doc_markdown_content,
    _fetch_tenant_access_token,
    _list_blocks,
    publish_report_to_feishu_doc,
)
from generate_daily_report import detect_chart_image_paths_for_push


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验收 PC 日报：格式+完整性+飞书图文推送")
    parser.add_argument("--report-file", type=Path, required=True, help="PC report txt path")
    parser.add_argument("--date", type=str, required=True, help="Report date YYYY-MM-DD")
    parser.add_argument("--app-id", type=str, default=os.getenv("FEISHU_APP_ID", ""))
    parser.add_argument("--app-secret", type=str, default=os.getenv("FEISHU_APP_SECRET", ""))
    parser.add_argument("--folder-token", type=str, default=os.getenv("FEISHU_DOC_FOLDER_TOKEN", ""))
    parser.add_argument("--doc-url-prefix", type=str, default=os.getenv("FEISHU_DOC_URL_PREFIX", "https://www.feishu.cn/docx/"))
    parser.add_argument("--title-prefix", type=str, default="PC日报验收")
    parser.add_argument("--skip-push", action="store_true", help="Only validate local file")
    return parser.parse_args()


def _assert_format_and_completeness(text: str) -> None:
    must_have = [
        "游戏盒PC云游戏数据",
        "一、游戏盒PC云游戏相关数据日报",
        "[pc云游戏图片]",
        "二、云游戏活跃用户top(去重)",
        "备注：",
    ]
    for item in must_have:
        if item not in text:
            raise AssertionError(f"缺少模板关键内容: {item}")

    if not (text.index("[pc云游戏图片]") < text.index("二、云游戏活跃用户top(去重)") < text.index("备注：")):
        raise AssertionError("模板结构顺序错误，应为 图片 -> top -> 备注")

    m1 = re.search(r"1、游戏的新增用户数为：(\d+)，游戏的活跃用户数为：(\d+)。", text)
    if not m1:
        raise AssertionError("备注第1条格式不匹配")
    if int(m1.group(1)) <= 0 or int(m1.group(2)) <= 0:
        raise AssertionError("新增/活跃数据不完整")

    m2 = re.search(
        r"2、会员充值人数：(\d+)，PC首开会员人数：(\d+)，充值金额：([0-9,]+)元，环比上周同期(上升|下降|持平).*。",
        text,
    )
    if not m2:
        raise AssertionError("备注第2条格式不匹配")
    if "暂无同比数据" in text:
        raise AssertionError("备注第2条缺少充值金额上周同比数据")
    if int(m2.group(1)) <= 0 or int(m2.group(2)) <= 0:
        raise AssertionError("会员人数数据不完整")
    if int(m2.group(3).replace(",", "")) <= 0:
        raise AssertionError("会员充值金额不完整")


def _build_settings(args: argparse.Namespace) -> FeishuDocSettings:
    app_id = str(args.app_id or "").strip()
    app_secret = str(args.app_secret or "").strip()
    if not app_id or not app_secret:
        raise FeishuDocError("缺少飞书凭证：--app-id/--app-secret")
    return FeishuDocSettings(
        app_id=app_id,
        app_secret=app_secret,
        folder_token=str(args.folder_token or "").strip(),
        doc_url_prefix=str(args.doc_url_prefix or "").strip() or "https://www.feishu.cn/docx/",
        verify_content_after_publish=True,
        verify_content_lang="zh",
        auto_share_tenant_members=True,
        auto_share_mode="read",
        auto_share_strict=False,
    )


def _assert_feishu_text_image(settings: FeishuDocSettings, document_id: str) -> Dict[str, int]:
    token = _fetch_tenant_access_token(settings)
    blocks = _list_blocks(settings=settings, token=token, document_id=document_id)
    image_count = 0
    text_count = 0
    for block in blocks:
        block_type = int(block.get("block_type") or 0)
        if block_type == 27:
            image_count += 1
        elif block_type == 2:
            text_count += 1
    if image_count < 1:
        raise AssertionError("飞书文档缺少图片块，未达成图文结合")
    if text_count < 3:
        raise AssertionError("飞书文档文本块过少，疑似内容缺失")

    markdown = _fetch_doc_markdown_content(settings=settings, token=token, document_id=document_id)
    if "备注：" not in markdown or "1、游戏的新增用户数为：" not in markdown:
        raise AssertionError("飞书文档缺少关键备注文本")
    return {"image_count": image_count, "text_count": text_count, "markdown_length": len(markdown)}


def main() -> None:
    args = _parse_args()
    report_file = args.report_file.resolve()
    if not report_file.exists():
        raise FileNotFoundError(f"report file not found: {report_file}")
    report_text = report_file.read_text(encoding="utf-8")

    _assert_format_and_completeness(report_text)
    print("[PASS] 本地格式与数据完整性校验通过")

    chart_paths = detect_chart_image_paths_for_push(report_file, report_text)
    if "pc_cloud" not in chart_paths:
        raise AssertionError("未检测到 pc_cloud 图路径，图文推送不完整")
    print(f"[PASS] 检测到PC图片: {chart_paths['pc_cloud']}")

    if args.skip_push:
        return

    report_date = date.fromisoformat(args.date)
    settings = _build_settings(args)
    result = publish_report_to_feishu_doc(
        settings=settings,
        report_text=report_text,
        report_date=report_date,
        title_override="",
        title_prefix=args.title_prefix,
        report_base_dir=report_file.parent,
        chart_image_paths=chart_paths,
    )
    url = str(result.get("url") or "")
    doc_id = str(result.get("document_id") or "")
    if not doc_id:
        raise AssertionError("飞书推送未返回 document_id")
    print(f"[PASS] 飞书推送成功: {url}")

    check_settings = replace(settings, verify_content_after_publish=True)
    stats = _assert_feishu_text_image(check_settings, doc_id)
    print(
        "[PASS] 飞书图文校验通过: "
        f"image_blocks={stats['image_count']} text_blocks={stats['text_count']} markdown_length={stats['markdown_length']}"
    )


if __name__ == "__main__":
    main()
