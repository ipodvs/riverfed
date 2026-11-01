"""Source-readiness data exposed to the Add and ingest workflow."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import _util  # noqa: F401
import ingest
import pending


def converted_source(
    *,
    title: str,
    source: str = "https://www.youtube.com/watch?v=abcdefghijk",
    duration: str = "20:00",
    transcript_words: int = 0,
) -> str:
    body = (
        "---\n"
        f'source: "{source}"\n'
        'type: "youtube"\n'
        'converted_at: "2026-07-27T12:00:00Z"\n'
        f'title: "{title}"\n'
        "---\n\n"
        f"# {title}\n\n"
        "## Metadata\n\n"
        f"- **Duration:** {duration}\n\n"
        "## Description\n\nA description.\n"
    )
    if transcript_words:
        body += (
            "\n## Transcript (auto-generated, en)\n\n"
            + ("spoken " * transcript_words)
        )
    return body


class PendingDiagnostics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / "vault"
        output = root / "output"
        (root / "sources").mkdir(parents=True)
        output.mkdir()
        self.vault = SimpleNamespace(root=root, output=output)
        self.model = SimpleNamespace(capture_folder=lambda: "sources")

    def test_missing_transcript_is_exposed_as_blocked(self):
        path = self.vault.output / "failed.md"
        path.write_text(
            converted_source(title="Failed source"),
            encoding="utf-8",
        )

        payload = pending.pending_payload(self.vault, self.model)

        self.assertEqual(payload["ready_count"], 0)
        self.assertEqual(payload["blocked_count"], 1)
        item = payload["pending"][0]
        self.assertEqual(item["source_type"], "youtube")
        self.assertEqual(item["readiness"]["code"], "missing_transcript")
        self.assertIn("Retry", item["readiness"]["problem"])

    def test_ready_revision_supersedes_failed_capture_without_deleting_it(self):
        failed = self.vault.output / "source.md"
        ready = self.vault.output / "source-2.md"
        failed.write_text(
            converted_source(title="Source"),
            encoding="utf-8",
        )
        ready.write_text(
            converted_source(title="Source", transcript_words=2000),
            encoding="utf-8",
        )

        payload = pending.pending_payload(self.vault, self.model)

        self.assertTrue(failed.exists())
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["ready_count"], 1)
        self.assertEqual(payload["blocked_count"], 0)
        self.assertEqual(payload["pending"][0]["filename"], "source-2.md")
        self.assertEqual(
            payload["pending"][0]["readiness"]["provenance"],
            "automatic captions",
        )
        self.assertEqual(
            [ready],
            ingest.pending_transcripts(self.vault, self.model),
        )


if __name__ == "__main__":
    unittest.main()
