from __future__ import annotations

import argparse
import base64
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from extra_auth import _collect_auth_data, inspect_fenxi_token, load_extra_auth
from generate_daily_report import diagnose_fenxi_token, preflight_870_auth, select_870_preflight_query


def _jwt_token(iat: int, exp: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"iat": iat, "exp": exp, "uid": "1"}

    def _b64(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    return f"{_b64(header)}.{_b64(payload)}.sig"


class ExtraAuthExtractTests(unittest.TestCase):
    def test_pc_web_extract_bearer_prefer_game_start_and_sync_admin_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            har_path = Path(temp_dir) / "pc.har"
            har_data = {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "url": "http://yadmin.4399.com/page",
                                "headers": [
                                    {"name": "Bearer", "value": "token=old&chain=0"},
                                    {"name": "Origin", "value": "http://yadmin.4399.com"},
                                    {"name": "Referer", "value": "http://yadmin.4399.com/"},
                                ],
                                "cookies": [],
                            },
                            "response": {"headers": []},
                        },
                        {
                            "request": {
                                "url": "http://yapiadmin.4399.com/?m=gameData&ac=gameStartData",
                                "headers": [
                                    {"name": "Bearer", "value": "token=new&chain=545"},
                                    {"name": "Authorization", "value": "Bearer abc.def"},
                                    {"name": "Origin", "value": "http://yadmin.4399.com"},
                                    {"name": "Referer", "value": "http://yadmin.4399.com/"},
                                    {"name": "X-Requested-With", "value": "XMLHttpRequest"},
                                ],
                                "cookies": [{"name": "Admin-Token", "value": "old"}],
                            },
                            "response": {"headers": []},
                        },
                        {
                            "request": {
                                "url": "http://yapiadmin.4399.com/?m=game&ac=snapshotInfo",
                                "headers": [
                                    {"name": "Bearer", "value": "token=late&chain=0"},
                                ],
                                "cookies": [],
                            },
                            "response": {"headers": []},
                        },
                    ]
                }
            }
            har_path.write_text(json.dumps(har_data, ensure_ascii=False), encoding="utf-8")
            auth = _collect_auth_data([har_path], "pc_web")

            headers = auth.get("headers") or {}
            self.assertEqual(headers.get("Bearer"), "token=new&chain=545")
            self.assertEqual(headers.get("Authorization"), "Bearer abc.def")
            self.assertEqual(headers.get("Origin"), "http://yadmin.4399.com")
            self.assertNotIn("X-Access-Token", headers)
            cookies = auth.get("cookies") or {}
            self.assertEqual(cookies.get("Admin-Token"), "new")

    def test_load_extra_auth_pc_web_not_infer_x_access_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            auth_path = Path(temp_dir) / "extra_auth.json"
            data = {
                "fenxi": {"token": "fenxi-token", "headers": {}, "cookies": {}},
                "505": {"token": "m-token", "headers": {}, "cookies": {}},
                "pc_web": {"token": "pc-token", "headers": {"Bearer": "token=abc"}, "cookies": {}},
            }
            auth_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            loaded = load_extra_auth(auth_path)
            self.assertEqual(loaded["fenxi"]["headers"].get("X-Access-Token"), "fenxi-token")
            self.assertEqual(loaded["505"]["headers"].get("X-Access-Token"), "m-token")
            self.assertNotIn("X-Access-Token", loaded["pc_web"]["headers"])
            self.assertEqual(loaded["pc_web"]["headers"].get("Bearer"), "token=abc")


class FenxiTokenDiagTests(unittest.TestCase):
    def test_inspect_fenxi_token_states(self) -> None:
        now = datetime(2026, 2, 24, 8, 0, 0, tzinfo=timezone.utc)
        now_ts = int(now.timestamp())

        valid_auth = {"cookies": {"e_token": _jwt_token(iat=now_ts - 3600, exp=now_ts + 8 * 3600)}}
        near_exp_auth = {"cookies": {"e_token": _jwt_token(iat=now_ts - 3600, exp=now_ts + 30 * 60)}}
        expired_auth = {"cookies": {"e_token": _jwt_token(iat=now_ts - 7200, exp=now_ts - 60)}}

        valid = inspect_fenxi_token(valid_auth, warn_threshold_hours=6, now_utc=now)
        near_exp = inspect_fenxi_token(near_exp_auth, warn_threshold_hours=6, now_utc=now)
        expired = inspect_fenxi_token(expired_auth, warn_threshold_hours=6, now_utc=now)

        self.assertTrue(valid["usable"])
        self.assertFalse(valid["expired"])
        self.assertFalse(valid["about_to_expire"])

        self.assertFalse(near_exp["usable"])
        self.assertTrue(near_exp["about_to_expire"])
        self.assertIn("低于阈值", near_exp["reason"])

        self.assertFalse(expired["usable"])
        self.assertTrue(expired["expired"])
        self.assertIn("已过期", expired["reason"])

    def test_diagnose_fenxi_token_message_contains_exp(self) -> None:
        now = datetime.now(timezone.utc)
        now_ts = int(now.timestamp())
        auth = {
            "fenxi": {
                "cookies": {
                    "e_token": _jwt_token(iat=now_ts - 600, exp=now_ts + int(timedelta(hours=9).total_seconds()))
                }
            }
        }
        diag = diagnose_fenxi_token(auth, timezone_name="Asia/Shanghai", warn_threshold_hours=6)
        self.assertTrue(diag["usable"])
        self.assertIn("exp=", diag["message"])


class AuthPreflight870Tests(unittest.TestCase):
    def test_select_870_preflight_query_picks_first_ordered_query(self) -> None:
        config = {
            "targets": {
                "total": {"label": "总", "queries": [{"params": {"game_type": 0}}]},
                "mobile": {"label": "手游", "queries": [{"params": {"game_type": 1}}]},
            },
            "report_section_order": ["mobile", "total"],
        }
        key, target_cfg, query = select_870_preflight_query(config)
        self.assertEqual(key, "mobile")
        self.assertEqual(target_cfg["label"], "手游")
        self.assertEqual(query["params"]["game_type"], 1)

    def test_preflight_870_auth_success_uses_first_query_params(self) -> None:
        args = argparse.Namespace(
            cookie=None,
            proxy_mode=None,
            http_proxy=None,
            https_proxy=None,
            network_hosts_yaml=None,
        )
        config = {
            "base_url": "http://admin.example.com/api",
            "session_cookie": "PHPSESSID=test",
            "timeout": 30,
            "default_http_method": "post",
            "auto_query_params": {"add_date_begin": {"format": "%Y-%m-%d", "offset_days": 0}},
            "network": {"proxy_mode": "direct"},
            "targets": {
                "total": {"label": "总", "queries": [{"params": {"game_type": 0}}]},
            },
        }
        with mock.patch("generate_daily_report.fetch_json", return_value={"ok": True}) as mocked_fetch:
            result = preflight_870_auth(config, args, datetime(2026, 3, 7).date())
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "870登录态可用: 总")
        mocked_fetch.assert_called_once()
        _, base_url, params, timeout, method = mocked_fetch.call_args.args
        self.assertEqual(base_url, "http://admin.example.com/api")
        self.assertEqual(params["game_type"], 0)
        self.assertEqual(params["add_date_begin"], "2026-03-07")
        self.assertEqual(timeout, 30)
        self.assertEqual(method, "post")

    def test_preflight_870_auth_reports_cookie_failure(self) -> None:
        args = argparse.Namespace(
            cookie=None,
            proxy_mode=None,
            http_proxy=None,
            https_proxy=None,
            network_hosts_yaml=None,
        )
        config = {
            "base_url": "http://admin.example.com/api",
            "timeout": 30,
            "network": {"proxy_mode": "direct"},
            "targets": {
                "total": {"label": "总", "queries": [{"params": {"game_type": 0}}]},
            },
        }
        result = preflight_870_auth(config, args, datetime(2026, 3, 7).date())
        self.assertFalse(result["ok"])
        self.assertIn("Session cookie missing", result["message"])


if __name__ == "__main__":
    unittest.main()
