from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from feishu_doc import (
    FeishuDocSettings,
    _api_request,
    _upload_image_token_for_block,
)


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class FeishuRetryTests(unittest.TestCase):
    @patch("feishu_doc._retry_sleep", return_value=None)
    def test_api_request_retry_on_ssl_error(self, _sleep_mock: object) -> None:
        seq = [
            requests.exceptions.SSLError("eof"),
            _FakeResponse({"code": 0, "data": {"ok": True}}),
        ]
        with patch("feishu_doc.requests.request", side_effect=seq) as req_mock:
            data = _api_request(
                method="GET",
                url="https://open.feishu.cn/open-apis/test",
                timeout=10,
            )
        self.assertEqual(data.get("ok"), True)
        self.assertEqual(req_mock.call_count, 2)

    @patch("feishu_doc._retry_sleep", return_value=None)
    def test_api_request_retry_on_retryable_code(self, _sleep_mock: object) -> None:
        seq = [
            _FakeResponse({"code": 1061045, "msg": "can retry"}),
            _FakeResponse({"code": 0, "data": {"ok": 1}}),
        ]
        with patch("feishu_doc.requests.request", side_effect=seq) as req_mock:
            data = _api_request(
                method="POST",
                url="https://open.feishu.cn/open-apis/test",
                timeout=10,
                json_body={"x": 1},
            )
        self.assertEqual(data.get("ok"), 1)
        self.assertEqual(req_mock.call_count, 2)

    @patch("feishu_doc._retry_sleep", return_value=None)
    def test_upload_media_retry_on_ssl_error(self, _sleep_mock: object) -> None:
        settings = FeishuDocSettings(app_id="a", app_secret="b", timeout=10)
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "a.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
            seq = [
                requests.exceptions.SSLError("eof"),
                _FakeResponse({"code": 0, "data": {"file_token": "ftok"}}),
            ]
            with patch("feishu_doc.requests.post", side_effect=seq) as post_mock:
                token = _upload_image_token_for_block(
                    settings=settings,
                    token="tenant",
                    image_path=image_path,
                    image_block_id="blk",
                    document_id="doc",
                )
        self.assertEqual(token, "ftok")
        self.assertEqual(post_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
