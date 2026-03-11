from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pc_auth_from_har import refresh_pc_auth_from_hars


class PCAuthFromHarTests(unittest.TestCase):
    def test_refresh_only_updates_pc_and_preserves_other_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extra_auth = root / "extra_auth.json"
            har_path = root / "pc.har"

            existing = {
                "fenxi": {"cookies": {"e_token": "fenxi_token"}, "headers": {"mediaids": "x"}, "token": ""},
                "505": {"cookies": {"PHPSESSID": "abc"}, "headers": {}, "token": ""},
                "pc_web": {"cookies": {"Admin-Token": "old"}, "headers": {"Bearer": "token=old&chain=545"}, "token": ""},
                "meta": {"source": "old"},
            }
            extra_auth.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

            har_data = {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "url": "http://yapiadmin.4399.com/?m=gameData&ac=gameStartData",
                                "headers": [
                                    {"name": "Origin", "value": "http://yadmin.4399.com"},
                                    {"name": "Referer", "value": "http://yadmin.4399.com/"},
                                    {"name": "Bearer", "value": "token=new_value&chain=545"},
                                ],
                                "cookies": [{"name": "Admin-Token", "value": "new_value"}],
                            },
                            "response": {"headers": []},
                        }
                    ]
                }
            }
            har_path.write_text(json.dumps(har_data, ensure_ascii=False), encoding="utf-8")

            result = refresh_pc_auth_from_hars(
                pc_hars=[har_path],
                extra_auth_file=extra_auth,
                output=extra_auth,
            )

            saved = json.loads(extra_auth.read_text(encoding="utf-8"))
            self.assertEqual(saved["pc_web"]["cookies"]["Admin-Token"], "new_value")
            self.assertEqual(saved["pc_web"]["headers"]["Bearer"], "token=new_value&chain=545")
            self.assertEqual(saved["fenxi"]["cookies"]["e_token"], "fenxi_token")
            self.assertEqual(saved["505"]["cookies"]["PHPSESSID"], "abc")
            self.assertTrue(result["pc_has_bearer"])


if __name__ == "__main__":
    unittest.main()
