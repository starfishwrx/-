from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from browser_auth_refresh import (
    _extract_cookie_value_from_sqlite,
    build_pc_bearer,
    parse_chain_from_bearer,
)


class BrowserAuthRefreshTests(unittest.TestCase):
    def test_parse_chain_from_bearer(self) -> None:
        self.assertEqual(parse_chain_from_bearer("token=abc&chain=545"), 545)
        self.assertEqual(parse_chain_from_bearer("chain=1&token=abc"), 1)
        self.assertIsNone(parse_chain_from_bearer("token=abc"))
        self.assertIsNone(parse_chain_from_bearer(""))

    def test_build_pc_bearer(self) -> None:
        self.assertEqual(build_pc_bearer("abcd", 545), "token=abcd&chain=545")
        with self.assertRaises(ValueError):
            build_pc_bearer("", 1)

    def test_extract_cookie_value_from_sqlite_handles_plain_and_encrypted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "Cookies"
            conn = sqlite3.connect(str(db))
            try:
                conn.execute(
                    """
                    CREATE TABLE cookies (
                        host_key TEXT,
                        name TEXT,
                        value TEXT,
                        encrypted_value BLOB,
                        last_access_utc INTEGER
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO cookies(host_key,name,value,encrypted_value,last_access_utc) VALUES(?,?,?,?,?)",
                    ("yadmin.4399.com", "Admin-Token", "", b"encrypted", 200),
                )
                conn.execute(
                    "INSERT INTO cookies(host_key,name,value,encrypted_value,last_access_utc) VALUES(?,?,?,?,?)",
                    ("yapiadmin.4399.com", "Admin-Token", "plain_token", b"", 300),
                )
                conn.commit()
            finally:
                conn.close()

            token, encrypted_only = _extract_cookie_value_from_sqlite(
                db,
                cookie_name="Admin-Token",
                target_domains=("yadmin.4399.com", "yapiadmin.4399.com"),
            )
            self.assertEqual(token, "plain_token")
            self.assertFalse(encrypted_only)


if __name__ == "__main__":
    unittest.main()
