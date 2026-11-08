import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import updater


class _Response(io.BytesIO):
    def __init__(self, body=b"", status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class UpdateDownloadTests(unittest.TestCase):
    def test_check_uses_the_release_api_asset_url_not_the_browser_cdn_url(self):
        release = {
            "tag_name": "v9.0.0",
            "html_url": "https://github.com/example/release",
            "assets": [{
                "name": "SmuggyConverter-macos-arm64-v9.0.0.zip",
                "url": "https://api.github.com/repos/example/releases/assets/123",
                "browser_download_url": "https://github.com/example/releases/download/v9.0.0/app.zip",
                "size": 123,
            }],
        }
        with patch.object(updater, "app_root", return_value=Path("/Applications/SmuggyConverter.app")), \
             patch.object(updater, "_sweep"), \
             patch.object(updater.sys, "platform", "darwin"), \
             patch.object(updater.urllib.request, "urlopen", return_value=_Response(json.dumps(release).encode())):
            info = updater.check()

        self.assertEqual(info["url"], "https://api.github.com/repos/example/releases/assets/123")

    def test_fetch_sends_octet_stream_accept_header_to_the_release_api(self):
        response = _Response(b"ok", headers={"Content-Length": "2"})
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            updater.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            self.assertTrue(updater._fetch("https://api.github.com/assets/123", Path(tmp) / "update.zip", 0, None, None))

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Accept"), "application/octet-stream")


if __name__ == "__main__":
    unittest.main()
