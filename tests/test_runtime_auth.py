from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from generate_daily_report import resolve_cookie
from runtime_auth import (
    get_runtime_session_cookie,
    normalize_870_session_cookie,
    resolve_runtime_auth_path,
    save_runtime_session_cookie,
)


class RuntimeAuthTests(unittest.TestCase):
    def test_normalize_870_cookie_accepts_multiple_input_shapes(self) -> None:
        self.assertEqual(normalize_870_session_cookie("abc123"), "PHPSESSID=abc123")
        self.assertEqual(normalize_870_session_cookie("PHPSESSID=abc123"), "PHPSESSID=abc123")
        self.assertEqual(
            normalize_870_session_cookie("foo=1; PHPSESSID=abc123; bar=2"),
            "PHPSESSID=abc123",
        )

    def test_normalize_870_cookie_rejects_missing_phpsessid_from_cookie_header(self) -> None:
        with self.assertRaises(ValueError):
            normalize_870_session_cookie("foo=1; bar=2")

    def test_save_runtime_session_cookie_persists_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("base_url: http://example.com\n", encoding="utf-8")
            runtime_auth_path = resolve_runtime_auth_path(config_path)
            save_runtime_session_cookie(runtime_auth_path, "abc123")
            self.assertEqual(get_runtime_session_cookie(runtime_auth_path), "PHPSESSID=abc123")

    def test_resolve_cookie_prefers_runtime_auth_over_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("base_url: http://example.com\n", encoding="utf-8")
            runtime_auth_path = resolve_runtime_auth_path(config_path)
            save_runtime_session_cookie(runtime_auth_path, "runtime_value")

            with mock.patch.dict(os.environ, {}, clear=True):
                cookie = resolve_cookie(None, {"session_cookie": "PHPSESSID=config_value"}, config_path)

            self.assertEqual(cookie, "PHPSESSID=runtime_value")

    def test_resolve_cookie_prefers_env_over_runtime_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("base_url: http://example.com\n", encoding="utf-8")
            runtime_auth_path = resolve_runtime_auth_path(config_path)
            save_runtime_session_cookie(runtime_auth_path, "runtime_value")

            with mock.patch.dict(os.environ, {"REPORT_PHPSESSID": "PHPSESSID=env_value"}, clear=True):
                cookie = resolve_cookie(None, {"session_cookie": "PHPSESSID=config_value"}, config_path)

            self.assertEqual(cookie, "PHPSESSID=env_value")

    def test_resolve_cookie_prefers_cli_over_all(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("base_url: http://example.com\n", encoding="utf-8")
            runtime_auth_path = resolve_runtime_auth_path(config_path)
            save_runtime_session_cookie(runtime_auth_path, "runtime_value")

            with mock.patch.dict(os.environ, {"REPORT_PHPSESSID": "PHPSESSID=env_value"}, clear=True):
                cookie = resolve_cookie("PHPSESSID=cli_value", {"session_cookie": "PHPSESSID=config_value"}, config_path)

            self.assertEqual(cookie, "PHPSESSID=cli_value")


if __name__ == "__main__":
    unittest.main()
