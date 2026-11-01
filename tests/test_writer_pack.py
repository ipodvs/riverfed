from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import _util  # noqa: F401
import writer_pack


class FakeModel:
    id = "karpathy-wiki"
    folders = ("sources", "topics", "concepts", "policies")
    links = {
        "source-topics": {"from": "source", "to": "topic", "field": "topics"},
        "source-concepts": {"from": "source", "to": "concept", "field": "concepts"},
    }

    @staticmethod
    def kind(folder: str) -> str:
        return {"sources": "source", "topics": "topic", "concepts": "concept", "policies": "policy"}[folder]


class WriterKnowledgePack(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="riverfed-writer-pack-"))
        for folder in FakeModel.folders:
            (self.root / folder).mkdir()
        (self.root / "index.md").write_text("---\nname: Volume II Research\nowner: Example Studio\n---\n# Volume II Research\n\nWorking research for the second volume.\n", encoding="utf-8")
        (self.root / "sources" / "archive.md").write_text(
            "---\nslug: archive\ntitle: Archive testimony\nchannel: Example archive\nurl: https://example.com/archive\npublished: 2026-08-20\ntopics: [succession]\n---\n# Archive testimony\n\n## TL;DR\nA contested account of succession.\n",
            encoding="utf-8",
        )
        (self.root / "topics" / "succession.md").write_text(
            "---\nslug: succession\nlast_updated: 2026-08-22\ntags: [empire, legitimacy]\n---\n# Succession and legitimacy\n\n## What it is\nAuthority becomes real through competing stories.\n\n## Why it matters\nIt can generate political pressure for Volume II.\n\nSee [[archive]].\n",
            encoding="utf-8",
        )
        (self.root / "policies" / "evidence.md").write_text(
            "---\nslug: evidence\nwriter_lane: craft\n---\n# Separate evidence from invention\n\nKeep the boundary visible.\n",
            encoding="utf-8",
        )
        self.vault = SimpleNamespace(slug="volume-two", root=self.root, display_name=lambda: "Volume II Research")

    def test_pack_preserves_body_provenance_relationships_and_lanes(self) -> None:
        pack = writer_pack.build_pack(self.vault, FakeModel())
        self.assertEqual(pack["schema"], "enge.knowledge-pack")
        self.assertEqual(pack["library"], {"owner": "Example Studio", "visibility": "private", "lanes": ["craft", "research"]})
        self.assertEqual(len(pack["digest"]), 64)
        topic = next(item for item in pack["items"] if item["title"] == "Succession and legitimacy")
        self.assertEqual(topic["lane"], "research")
        self.assertIn("political pressure", topic["whyItMatters"])
        self.assertEqual(topic["sourceRefs"][0]["url"], "https://example.com/archive")
        self.assertTrue(any(rel["type"] == "wiki-link" for rel in topic["relationships"]))
        policy = next(item for item in pack["items"] if item["kind"] == "policy")
        self.assertEqual(policy["lane"], "craft")
        json.dumps(pack)

    def test_pack_digest_is_stable_for_unchanged_pages(self) -> None:
        first = writer_pack.build_pack(self.vault, FakeModel())
        second = writer_pack.build_pack(self.vault, FakeModel())
        self.assertEqual(first["digest"], second["digest"])


if __name__ == "__main__":
    unittest.main()
