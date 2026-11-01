"""Codex image-attachment regression tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import _util  # noqa: F401
import agent_runner


class CodexImageArgs(unittest.TestCase):
    def setUp(self) -> None:
        self.saved_flags = agent_runner._CODEX_EXEC_FLAGS
        agent_runner._CODEX_EXEC_FLAGS = {"--image", "--sandbox"}

    def tearDown(self) -> None:
        agent_runner._CODEX_EXEC_FLAGS = self.saved_flags

    def test_images_are_attached_once_in_source_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "one.jpg"
            second = Path(tmp) / "two.png"
            first.write_bytes(b"jpg")
            second.write_bytes(b"png")
            argv = agent_runner._append_image_args(
                ["codex", "exec", "-"], "codex", [first, second, first]
            )
        self.assertEqual(argv[-3], "--image")
        self.assertEqual(argv[-2:], [str(first.resolve()), str(second.resolve())])

    def test_missing_cli_image_support_fails_loudly(self) -> None:
        agent_runner._CODEX_EXEC_FLAGS = {"--sandbox"}
        with self.assertRaisesRegex(RuntimeError, "does not advertise --image"):
            agent_runner._append_image_args(
                ["codex", "exec", "-"], "codex", ["frame.jpg"]
            )

    def test_claude_keeps_using_read_tool(self) -> None:
        original = ["claude", "-p"]
        self.assertIs(
            agent_runner._append_image_args(original, "claude-code", ["x.jpg"]),
            original,
        )

    def test_grok_keeps_using_read_tool(self) -> None:
        """Grok's read_file returns image PIXELS, not just bytes (verified
        against a real capture frame on 1.0.3), so it reads frames lazily
        off disk like Claude. Attaching them upfront is Codex-only — doing
        it here would front-load a 60-frame deep capture into context."""
        original = ["grok", "--prompt-file", "/tmp/p.md"]
        self.assertIs(
            agent_runner._append_image_args(original, "grok", ["x.jpg"]),
            original,
        )


if __name__ == "__main__":
    unittest.main()
