"""Vision-relevant transcript frames are selected safely for Codex."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import _util  # noqa: F401
import ingest


class VisionFramePaths(unittest.TestCase):
    def test_only_tagged_existing_frames_inside_sibling_dir_are_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            transcript = root / "talk.md"
            frames = root / "talk-frames"
            frames.mkdir()
            first = frames / "one.jpg"
            second = frames / "two.png"
            untagged = frames / "ignored.jpg"
            outside = root / "outside.jpg"
            for path in (first, second, untagged, outside):
                path.write_bytes(b"image")
            transcript.write_text(
                "\n".join([
                    "## Visual content",
                    "### 🔍 t=00:01  `talk-frames/one.jpg`",
                    "### · t=00:02  `talk-frames/ignored.jpg`",
                    "### 🔍 t=00:03  `talk-frames/two.png`",
                    "### 🔍 t=00:04  `talk-frames/../outside.jpg`",
                    "### 🔍 t=00:05  `talk-frames/one.jpg`",
                ]),
                encoding="utf-8",
            )
            selected = ingest.vision_frame_paths(transcript)

        self.assertEqual(selected, [first.resolve(), second.resolve()])


if __name__ == "__main__":
    unittest.main()
