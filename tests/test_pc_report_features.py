from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
import re

from generate_daily_report import (
    TargetResult,
    detect_chart_image_paths_for_push,
    render_pc_report,
)
from pc_web_metrics_service import PCWebMetricsService, PCWebSettings


class PCReportTemplateTests(unittest.TestCase):
    def test_render_pc_report_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            target = TargetResult(key="pc_cloud", label="PC云游戏")
            target.concurrency.formatted_peak_value = "5137"
            target.concurrency.peak_time_label = "15点"
            target.queue.formatted_peak_value = "146"
            target.queue.peak_time_label = "16点"
            target.queue_summary = "于10点-23点有排队。"

            pc_web_metrics = {
                "notes": {
                    "new_users": {"value": 7601, "day_ratio": "+1.00%", "week_ratio": "-2.00%"},
                    "active_users": {"value": 47195, "day_ratio": "+0.50%", "week_ratio": "+2.00%"},
                    "member_total_amount": {"value": 1800, "day_ratio": "-18.14%", "week_ratio": "N/A"},
                    "member_total_orders": {"value": 184, "day_ratio": "-4.66%", "week_ratio": "N/A"},
                    "member_first_amount": {"value": 486, "day_ratio": "+4.74%", "week_ratio": "N/A"},
                    "member_first_count": {"value": 63, "day_ratio": "+8.62%", "week_ratio": "N/A"},
                    "member_summary": {
                        "recharge_count": 184,
                        "first_count": 63,
                        "recharge_amount": 1800,
                        "recharge_amount_formatted": "1,800",
                        "week_trend_text": "上升31.98%",
                    },
                },
                "top_games": [
                    {"name": "蛋仔派对", "active_users": 11295},
                    {"name": "崩坏:星穹铁道", "active_users": 6955},
                ],
                "warnings": [],
            }

            report_path = render_pc_report(
                template_dir=Path("templates"),
                template_name="pc_report_template.j2",
                output_dir=output_dir,
                date_cn="2026年2月23日",
                target=target,
                pc_web_metrics=pc_web_metrics,
            )
            text = report_path.read_text(encoding="utf-8")

            self.assertIn("2026年2月23日游戏盒PC云游戏数据", text)
            self.assertIn("备注：", text)
            self.assertIn("1、游戏的新增用户数为：7601，游戏的活跃用户数为：47195。", text)
            self.assertIn("2、会员充值人数：184，PC首开会员人数：63，充值金额：1,800元，环比上周同期上升31.98%。", text)
            self.assertIn("二、云游戏活跃用户top(去重)", text)

            # 验证结构顺序：图片 -> top -> 备注
            self.assertLess(text.index("[pc云游戏图片]"), text.index("二、云游戏活跃用户top(去重)"))
            self.assertLess(text.index("二、云游戏活跃用户top(去重)"), text.index("备注："))

            # 验证关键数字字段可解析
            m1 = re.search(r"1、游戏的新增用户数为：(\d+)，游戏的活跃用户数为：(\d+)。", text)
            self.assertIsNotNone(m1)
            self.assertGreater(int(m1.group(1)), 0)
            self.assertGreater(int(m1.group(2)), 0)

            m2 = re.search(
                r"2、会员充值人数：(\d+)，PC首开会员人数：(\d+)，充值金额：([0-9,]+)元，环比上周同期(上升|下降|持平).*。",
                text,
            )
            self.assertIsNotNone(m2)
            self.assertGreater(int(m2.group(1)), 0)
            self.assertGreater(int(m2.group(2)), 0)
            self.assertNotIn("暂无同比数据", text)


class PCPushImageDetectTests(unittest.TestCase):
    def test_detect_pc_chart_image_for_push(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / "charts").mkdir(parents=True, exist_ok=True)
            (base / "charts" / "pc_cloud.png").write_bytes(b"fakepng")
            report_file = base / "2026223_pc_report.txt"
            report_text = "标题\n[pc云游戏图片]\n"
            report_file.write_text(report_text, encoding="utf-8")

            detected = detect_chart_image_paths_for_push(report_file, report_text)
            self.assertEqual(detected.get("pc_cloud"), "charts/pc_cloud.png")


class PCMemberMetricExtractTests(unittest.TestCase):
    def test_extract_member_notes(self) -> None:
        service = PCWebMetricsService(
            PCWebSettings(
                base_url="http://yapiadmin.4399.com",
                web_origin="http://yadmin.4399.com",
                request_timeout=30,
                query_proxy_url="",
                hosts_yaml_path="",
            )
        )

        total_data = {
            "data": {
                "data": [
                    {"g0dxf_e30fj1": "20260216", "d0kojttvygqw": "1500", "4r8uh91ns_sx": "160"},
                    {"g0dxf_e30fj1": "20260222", "d0kojttvygqw": "2200", "4r8uh91ns_sx": "193"},
                    {"g0dxf_e30fj1": "20260223", "d0kojttvygqw": "1800", "4r8uh91ns_sx": "184"},
                ]
            }
        }
        first_data = {
            "data": {
                "data": [
                    {"chciprojlqw0": "20260216", "v7qf1aulb414": "450", "g8vcu9mh4r56": "50"},
                    {"chciprojlqw0": "20260222", "v7qf1aulb414": "464", "g8vcu9mh4r56": "58"},
                    {"chciprojlqw0": "20260223", "v7qf1aulb414": "486", "g8vcu9mh4r56": "63"},
                ]
            }
        }

        notes = service._extract_member_notes(
            total_data=total_data,
            first_data=first_data,
            query_date=date.fromisoformat("2026-02-23"),
        )

        self.assertEqual(notes["member_total_amount"]["value"], 1800)
        self.assertEqual(notes["member_total_orders"]["value"], 184)
        self.assertEqual(notes["member_first_amount"]["value"], 486)
        self.assertEqual(notes["member_first_count"]["value"], 63)
        self.assertEqual(notes["member_total_amount"]["day_ratio"], "-18.18%")
        self.assertEqual(notes["member_first_count"]["day_ratio"], "+8.62%")
        self.assertIn("member_summary", notes)
        self.assertEqual(notes["member_summary"]["recharge_amount_formatted"], "1,800")
        self.assertEqual(notes["member_summary"]["week_trend_text"], "上升20.00%")

    def test_extract_single_value_match_target_day(self) -> None:
        service = PCWebMetricsService(
            PCWebSettings(
                base_url="http://yapiadmin.4399.com",
                web_origin="http://yadmin.4399.com",
                request_timeout=30,
                query_proxy_url="",
                hosts_yaml_path="",
            )
        )
        payload = {
            "data": {
                "data": [
                    {"g0dxf_e30fj1": "2026-02-17", "d0kojttvygqw": "2800"},
                    {"g0dxf_e30fj1": "2026-02-16", "d0kojttvygqw": "2267"},
                ]
            }
        }
        matched = service._extract_single_value(
            payload,
            "d0kojttvygqw",
            date_field="g0dxf_e30fj1",
            target_day_key="20260216",
        )
        self.assertEqual(matched, 2267)

    def test_extract_member_notes_with_prev_week_override(self) -> None:
        service = PCWebMetricsService(
            PCWebSettings(
                base_url="http://yapiadmin.4399.com",
                web_origin="http://yadmin.4399.com",
                request_timeout=30,
                query_proxy_url="",
                hosts_yaml_path="",
            )
        )
        total_data = {
            "data": {
                "data": [
                    {"g0dxf_e30fj1": "2026-02-23", "d0kojttvygqw": "2992", "4r8uh91ns_sx": "262"},
                    {"g0dxf_e30fj1": "2026-02-22", "d0kojttvygqw": "3000", "4r8uh91ns_sx": "280"},
                ]
            }
        }
        first_data = {
            "data": {
                "data": [
                    {"chciprojlqw0": "2026-02-23", "v7qf1aulb414": "900", "g8vcu9mh4r56": "76"},
                    {"chciprojlqw0": "2026-02-22", "v7qf1aulb414": "850", "g8vcu9mh4r56": "70"},
                ]
            }
        }
        notes = service._extract_member_notes(
            total_data=total_data,
            first_data=first_data,
            query_date=date.fromisoformat("2026-02-23"),
            total_amount_today_override=2992,
            total_amount_prev_week_override=2267,
        )
        self.assertEqual(notes["member_summary"]["week_trend_text"], "上升31.98%")

    def test_extract_member_notes_with_trend_component_override(self) -> None:
        service = PCWebMetricsService(
            PCWebSettings(
                base_url="http://yapiadmin.4399.com",
                web_origin="http://yadmin.4399.com",
                request_timeout=30,
                query_proxy_url="",
                hosts_yaml_path="",
            )
        )
        total_data = {
            "data": {
                "data": [
                    {"g0dxf_e30fj1": "2026-02-23", "d0kojttvygqw": "0", "4r8uh91ns_sx": "262"},
                    {"g0dxf_e30fj1": "2026-02-22", "d0kojttvygqw": "0", "4r8uh91ns_sx": "280"},
                ]
            }
        }
        first_data = {
            "data": {
                "data": [
                    {"chciprojlqw0": "2026-02-23", "v7qf1aulb414": "900", "g8vcu9mh4r56": "76"},
                ]
            }
        }
        trend_data = {
            "data": {
                "data": [
                    {"2a9u57i279ba": "2,992", "6zlb6zfwezv0": "2,267", "avq_ehkl4hqy": "31.98%"},
                ]
            }
        }
        notes = service._extract_member_notes(
            total_data=total_data,
            first_data=first_data,
            query_date=date.fromisoformat("2026-02-23"),
            trend_summary_override=service._extract_trend_summary(trend_data),
        )
        self.assertEqual(notes["member_summary"]["recharge_amount"], 2992)
        self.assertEqual(notes["member_summary"]["week_trend_text"], "上升31.98%")


class PCWebAuthFailureMessageTests(unittest.TestCase):
    def test_login_failure_message_with_missing_bearer_hint(self) -> None:
        service = PCWebMetricsService(
            PCWebSettings(
                base_url="http://yapiadmin.4399.com",
                web_origin="http://yadmin.4399.com",
                request_timeout=30,
                query_proxy_url="",
                hosts_yaml_path="",
            )
        )
        msg = service._format_pc_web_failure_message(
            -100,
            "请先登录",
            {"headers": {"Origin": "http://yadmin.4399.com"}},
        )
        self.assertIn("未提取到 Bearer 请求头", msg)

    def test_login_failure_message_without_hint_when_bearer_exists(self) -> None:
        service = PCWebMetricsService(
            PCWebSettings(
                base_url="http://yapiadmin.4399.com",
                web_origin="http://yadmin.4399.com",
                request_timeout=30,
                query_proxy_url="",
                hosts_yaml_path="",
            )
        )
        msg = service._format_pc_web_failure_message(
            -100,
            "请先登录",
            {"headers": {"Bearer": "token=abc"}},
        )
        self.assertEqual(msg, "PC网页端接口失败 status=-100, msg=请先登录")


if __name__ == "__main__":
    unittest.main()
