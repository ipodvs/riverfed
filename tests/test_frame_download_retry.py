"""Frame downloads retry with a fresh YouTube media URL after HTTP 403."""
from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import _util  # noqa: F401
import convert


class FrameDownloadRetry(unittest.TestCase):
    def test_transient_failures_recreate_youtubedl_and_recover(self) -> None:
        class FakeYDL:
            options: list[dict] = []

            def __init__(self, options):
                self.options.append(options)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def extract_info(self, _url, download=True):
                if len(self.options) < 3:
                    raise RuntimeError("HTTP Error 403: Forbidden")
                filename = self.options[-1]["outtmpl"].replace("%(ext)s", "mp4")
                Path(filename).write_bytes(b"video")
                return {"_filename": filename}

            def prepare_filename(self, info):
                return info["_filename"]

        fake_module = types.SimpleNamespace(YoutubeDL=FakeYDL)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"yt_dlp": fake_module}):
                with patch("convert.warn") as warning:
                    path = convert._download_video_for_frames(
                        "https://youtube.test/watch?v=abc", Path(tmp)
                    )

            self.assertIsNotNone(path)
            self.assertTrue(path.is_file())

        self.assertEqual(len(FakeYDL.options), 3)
        self.assertEqual(warning.call_count, 2)
        self.assertTrue(all(o["retries"] == 10 for o in FakeYDL.options))


if __name__ == "__main__":
    unittest.main()
