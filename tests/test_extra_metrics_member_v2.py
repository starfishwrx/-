from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from extra_metrics_service import ExtraMetricsService, ExtraSettings


class ExtraMetricsMemberV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ExtraMetricsService(
            ExtraSettings(
                timezone="Asia/Shanghai",
                request_timeout=20,
                query_proxy_url="",
                hosts_yaml_path="hosts_505.yaml",
                query_debug_log_path=Path("/tmp/extra_metrics_member_v2_debug.log"),
                fenxi_base="https://fenxi.4399dev.com",
                manage_base="http://manage.5054399.com",
            )
        )

    def test_extract_member_notes_v2_prefers_first_count(self) -> None:
        daily_payload = {
            "data": {
                "data": [
                    {"zjpfdm75018i": "20260226", "bq2uvv3owhlk": "900.00", "g41xqw2bbrw9": "40"},
                    {"zjpfdm75018i": "20260304", "bq2uvv3owhlk": "1,145.00", "g41xqw2bbrw9": "55"},
                ]
            }
        }
        count_payload = {
            "data": {
                "data": [
                    {"fxlo87pe_bxk": "20260303", "_kcr7vzxji88{1}": "36,003", "z_ftqnrrb2si{1}": "506"}
                ]
            }
        }
        notes = self.service._extract_member_notes_v2(
            member_daily_payload=daily_payload,
            member_count_payload=count_payload,
            query_date=date(2026, 3, 4),
            active_users_value=47177,
        )
        self.assertEqual(notes.get("member_recharge_amount"), 1145)
        self.assertEqual(notes.get("member_open_count"), 506)
        self.assertEqual(notes.get("member_valid_count"), 36003)
        self.assertEqual(notes.get("member_recharge_week_ratio"), "+27.22%")
        self.assertEqual(notes.get("member_pay_rate"), "0.12%")

    def test_find_date_row_by_field_fallback_latest_le(self) -> None:
        rows = [
            {"fxlo87pe_bxk": "20260301", "_kcr7vzxji88{1}": "300"},
            {"fxlo87pe_bxk": "20260303", "_kcr7vzxji88{1}": "360"},
        ]
        row = self.service._find_date_row_by_field(rows, field_id="fxlo87pe_bxk", target_day_key="20260304")
        self.assertEqual(str(row.get("fxlo87pe_bxk")), "20260303")


if __name__ == "__main__":
    unittest.main()
