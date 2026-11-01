"""Issue #4 — obsidian_pass derives relationship tags from the model manifest,
not a hardcoded topics/entities pair. Also covers issue #3 end-to-end: a
block-list relationship field survives the normalizer as an inline value with
no stale block left behind."""
import shutil
import unittest

import _util
import obsidian_pass as O
from _wikis import scaffold_vault
from model_registry import load_model_for_vault


def _relation_fields(model):
    return {f: [s["field"] for s in model.links.values()
                if s.get("from") == model.kind(f) and s.get("field")]
            for f in model.folders}


def _run_pass(vault, page):
    model = load_model_for_vault(vault)
    O.process_file(page, O.build_slug_index(vault.root), vault.root,
                   set(model.folders), _relation_fields(model))
    return O.split_frontmatter(page.read_text())[0]


class RelationTags(unittest.TestCase):
    def setUp(self):
        home = _util.fresh_vault_home()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)

    def test_sop_source_tags_from_manifest_fields(self):
        v, err = scaffold_vault("ops", "Ops", "2026-07-18",
                                model="sops-to-skills")
        self.assertIsNotNone(v, err)
        page = v.root / "sources" / "onboarding.md"
        page.write_text(
            "---\nslug: onboarding\ntitle: Onboarding\n"
            "procedures: [setup-laptop]\n"
            "policies:\n  - data-handling\n  - access-control\n"
            "runbooks: [locked-out]\n---\n# Onboarding\n\nText.\n")
        tags = _run_pass(v, page)["tags"]
        for want in ["setup-laptop", "data-handling", "access-control",
                     "locked-out", "wiki/sources"]:
            self.assertIn(want, tags)

    def test_karpathy_source_backward_compatible(self):
        v, err = scaffold_vault("karp", "Karp", "2026-07-18",
                                model="karpathy-wiki")
        self.assertIsNotNone(v, err)
        page = v.root / "sources" / "talk.md"
        page.write_text("---\nslug: talk\ntitle: Talk\ntopics: [rl]\n"
                        "entities: [pytorch]\n---\n# Talk\n\nx.\n")
        tags = _run_pass(v, page)["tags"]
        self.assertIn("rl", tags)
        self.assertIn("pytorch", tags)
        self.assertIn("wiki/sources", tags)

    def test_block_list_normalized_without_stale_lines(self):
        v, err = scaffold_vault("ops2", "Ops2", "2026-07-18",
                                model="sops-to-skills")
        self.assertIsNotNone(v, err)
        page = v.root / "sources" / "n.md"
        page.write_text("---\nslug: n\ntitle: N\n"
                        "policies:\n  - data-handling\n  - access-control\n"
                        "---\n# N\n\nx.\n")
        _run_pass(v, page)
        raw = page.read_text()
        self.assertIn("policies: [data-handling, access-control]", raw)
        self.assertNotIn("- data-handling", raw)

    def test_manually_supplied_tags_not_clobbered(self):
        v, err = scaffold_vault("karp2", "Karp2", "2026-07-18",
                                model="karpathy-wiki")
        self.assertIsNotNone(v, err)
        page = v.root / "sources" / "t.md"
        page.write_text("---\nslug: t\ntitle: T\ntopics: [rl]\n"
                        "tags: [manual-tag]\n---\n# T\n\nx.\n")
        tags = _run_pass(v, page)["tags"]
        self.assertIn("manual-tag", tags)
        self.assertIn("rl", tags)


if __name__ == "__main__":
    unittest.main()
