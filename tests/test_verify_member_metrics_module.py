from __future__ import annotations

import unittest

from scripts.verify_member_metrics_module import _validate_member_notes


class VerifyMemberMetricsModuleTests(unittest.TestCase):
    def test_validate_member_notes_pass(self) -> None:
        notes = {
            "member_pay_rate": "0.42%",
            "member_recharge_amount": 10910,
            "member_recharge_week_ratio": "-53.76%",
            "member_open_count": 893,
            "member_valid_count": 34720,
        }
        _validate_member_notes(notes, allow_missing_valid_count=False)

    def test_validate_member_notes_fail_on_missing_amount(self) -> None:
        notes = {
            "member_pay_rate": "0.42%",
            "member_recharge_amount": 0,
            "member_recharge_week_ratio": "-53.76%",
            "member_open_count": 893,
            "member_valid_count": 34720,
        }
        with self.assertRaises(AssertionError):
            _validate_member_notes(notes, allow_missing_valid_count=False)

    def test_validate_member_notes_fail_on_bad_rate(self) -> None:
        notes = {
            "member_pay_rate": "暂未获取",
            "member_recharge_amount": 10910,
            "member_recharge_week_ratio": "-53.76%",
            "member_open_count": 893,
            "member_valid_count": 34720,
        }
        with self.assertRaises(AssertionError):
            _validate_member_notes(notes, allow_missing_valid_count=False)


if __name__ == "__main__":
    unittest.main()
