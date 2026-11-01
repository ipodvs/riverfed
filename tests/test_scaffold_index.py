"""Issue #2 — a new vault's index.md matches the selected knowledge model, and
issue #5 — scaffolded source pages resolve source_file under the vault output.

Every test here is hermetic: vault homes go to throwaway temp dirs, and the
custom-model case isolates the model registry behind a temp models root so it
never reads — let alone deletes — the real, gitignored models/custom/.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import _util
import model_registry as M
from _wikis import scaffold_vault


def _headings(idx_text: str) -> list[str]:
    return [ln.strip() for ln in idx_text.splitlines() if ln.startswith("## ")]


class ScaffoldIndex(unittest.TestCase):
    def setUp(self):
        home = _util.fresh_vault_home()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)

    def _scaffold(self, slug, model):
        v, err = scaffold_vault(slug, slug.title(), "2026-07-18", model=model)
        self.assertIsNotNone(v, err)
        return v

    def test_karpathy_sections(self):
        v = self._scaffold("kb-karp", "karpathy-wiki")
        idx = v.index.read_text()
        hs = _headings(idx)
        for want in ["Sources", "Topics", "Entities", "Concepts"]:
            self.assertTrue(any(h.startswith(f"## {want}") for h in hs), hs)
        self.assertIn("model: karpathy-wiki", idx)

    def test_para_sections_with_inbox(self):
        v = self._scaffold("kb-para", "second-brain")
        hs = _headings(v.index.read_text())
        for want in ["Inbox", "Projects", "Areas", "Resources", "Archives"]:
            self.assertTrue(any(h.startswith(f"## {want}") for h in hs), hs)

    def test_sop_sections_with_inbox(self):
        v = self._scaffold("kb-sop", "sops-to-skills")
        hs = _headings(v.index.read_text())
        for want in ["Inbox", "Procedures", "Policies", "Runbooks"]:
            self.assertTrue(any(h.startswith(f"## {want}") for h in hs), hs)


class CustomModelFallback(unittest.TestCase):
    """The manifest-generated index fallback for models that ship no
    index-template.md. Runs entirely inside a temp models root — the real
    models/custom/ is never touched (regression guard for issue #6)."""

    def setUp(self):
        home = _util.fresh_vault_home()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        # Redirect model resolution at a throwaway models tree. resolve_model_dir
        # reads model_registry.PROJECT_DIR live, so patching the module globals
        # (and restoring them) fully isolates this test from the user's models/.
        self.tmp = Path(tempfile.mkdtemp(prefix="riverfed-test-models-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "models").mkdir()
        self._saved = (M.PROJECT_DIR, M.MODELS_DIR)
        self.addCleanup(self._restore)
        M.PROJECT_DIR = self.tmp
        M.MODELS_DIR = self.tmp / "models"

    def _restore(self):
        M.PROJECT_DIR, M.MODELS_DIR = self._saved

    def _write_model(self, mid: str, folders: str):
        d = M.MODELS_DIR / "custom" / mid
        d.mkdir(parents=True)
        (d / "model.md").write_text(f"---\nname: {mid}\nfolders:\n{folders}\n---\n")
        (d / "SCHEMA.md").write_text("# SCHEMA\n")
        return d

    def test_custom_model_falls_back_to_manifest_generated_index(self):
        self._write_model("zz-test-scaffold",
                          "  inbox: { kind: source, capture: true }\n"
                          "  widgets: { kind: widget }")
        # A sentinel sibling custom model that must survive the whole test —
        # proves no cleanup ever reaches models/custom/ as a whole.
        sentinel = self._write_model("keepme",
                                     "  inbox: { kind: source, capture: true }")

        v, err = scaffold_vault("kb-custom", "Custom", "2026-07-18",
                                model="zz-test-scaffold")
        self.assertIsNotNone(v, err)
        hs = _headings(v.index.read_text())
        self.assertTrue(any(h.startswith("## Inbox") for h in hs), hs)
        self.assertTrue(any(h.startswith("## Widgets") for h in hs), hs)
        self.assertTrue((sentinel / "model.md").exists(),
                        "sibling custom model must not be deleted by the test")


class SourceFilePathResolves(unittest.TestCase):
    def setUp(self):
        home = _util.fresh_vault_home()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)

    def test_relative_source_file_lands_in_vault_output(self):
        # Issue #5: `../output/<name>` from a sources/ page must resolve to
        # <vault>/output/<name>, not one level above the vault.
        v, err = scaffold_vault("paths", "Paths", "2026-07-18",
                                model="karpathy-wiki")
        self.assertIsNotNone(v, err)
        page = v.sources / "example.md"
        resolved = (page.parent / "../output/example.md").resolve()
        self.assertEqual(resolved, (v.output / "example.md").resolve())


if __name__ == "__main__":
    unittest.main()
