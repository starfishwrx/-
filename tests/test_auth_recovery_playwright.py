from __future__ import annotations

import unittest

from auth_recovery_playwright import (
    _choose_best_pc_bearer,
    _extract_chain,
    _extract_token_from_bearer,
    _looks_like_sms_request_url,
)


class AuthRecoveryHelperTests(unittest.TestCase):
    def test_extract_chain_and_token(self) -> None:
        bearer = "token=abc123&chain=545"
        self.assertEqual(_extract_chain(bearer), 545)
        self.assertEqual(_extract_token_from_bearer(bearer), "abc123")
        self.assertIsNone(_extract_chain("token=abc123"))
        self.assertEqual(_extract_token_from_bearer("chain=1"), "")

    def test_choose_best_pc_bearer_prefers_game_start_data(self) -> None:
        candidates = [
            {"url": "http://yapiadmin.4399.com/?m=game&ac=snapshotInfo", "bearer": "token=old&chain=0", "ts": 2},
            {"url": "http://yapiadmin.4399.com/?m=gameData&ac=gameStartData", "bearer": "token=good&chain=545", "ts": 1},
            {"url": "http://yapiadmin.4399.com/?m=game&ac=list", "bearer": "token=list&chain=544", "ts": 3},
        ]
        best = _choose_best_pc_bearer(candidates)
        assert best is not None
        self.assertEqual(best["bearer"], "token=good&chain=545")

    def test_detect_sms_request_url(self) -> None:
        self.assertTrue(_looks_like_sms_request_url("https://x.com/api/sendCode?mobile=1"))
        self.assertTrue(_looks_like_sms_request_url("https://x.com/user/sms/send"))
        self.assertFalse(_looks_like_sms_request_url("https://x.com/gameData/list"))


if __name__ == "__main__":
    unittest.main()
