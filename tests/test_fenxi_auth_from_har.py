from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fenxi_auth_from_har import refresh_fenxi_auth_from_hars


class FenxiAuthFromHarTests(unittest.TestCase):
    def test_refresh_only_updates_fenxi_and_preserves_other_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extra_auth = root / "extra_auth.json"
            har_path = root / "fenxi.har"

            existing = {
                "fenxi": {"cookies": {"e_token": "old"}, "headers": {}, "token": ""},
                "505": {"cookies": {"a": "b"}, "headers": {"X-Access-Token": "m_token"}, "token": "m_token"},
                "pc_web": {"cookies": {"Admin-Token": "abc"}, "headers": {"Bearer": "token=abc&chain=545"}, "token": ""},
                "meta": {"source": "old"},
            }
            extra_auth.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

            har_data = {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "url": "https://fenxi.4399dev.com/event-analysis-server/app_auth/getModuleSwitch?mediaId=x",
                                "headers": [
                                    {"name": "mediaids", "value": "media-eb40cb50d15a49a9"},
                                    {"name": "topic", "value": "gamebox_event"},
                                ],
                                "cookies": [
                                    {"name": "e_token", "value": "new_token_value"},
                                    {"name": "JSESSIONID", "value": "new_js"},
                                ],
                            },
                            "response": {"headers": []},
                        }
                    ]
                }
            }
            har_path.write_text(json.dumps(har_data, ensure_ascii=False), encoding="utf-8")

            result = refresh_fenxi_auth_from_hars(
                fenxi_hars=[har_path],
                extra_auth_file=extra_auth,
                output=extra_auth,
            )

            saved = json.loads(extra_auth.read_text(encoding="utf-8"))
            self.assertEqual(saved["fenxi"]["cookies"]["e_token"], "new_token_value")
            self.assertEqual(saved["505"]["token"], "m_token")
            self.assertEqual(saved["pc_web"]["headers"]["Bearer"], "token=abc&chain=545")
            self.assertEqual(result["fenxi_present"], True)


if __name__ == "__main__":
    unittest.main()
