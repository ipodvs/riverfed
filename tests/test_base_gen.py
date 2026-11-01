"""Obsidian Bases generation — every shipped template renders, and the
ledger's ownership policy protects hand edits.

The ledger matters because obsidian_pass runs after EVERY ingest: an
always-regenerate policy would silently destroy a view tweak made in the
Obsidian GUI hours earlier.
"""
import tempfile
import unittest
from pathlib import Path

import _util  # noqa: F401  (path bootstrap)
import base_gen
import model_registry as M


class _FakeVault:
    """Minimal stand-in for _wikis.Vault — the surface generate_bases uses."""

    def __init__(self, root: Path, slug: str = "testvault"):
        self.root = root
        self.slug = slug
        root.mkdir(parents=True, exist_ok=True)

    @property
    def state_dir(self) -> Path:
        return self.root / ".state"

    def display_name(self) -> str:
        return "Test Vault"


def _make_model(template: str, name: str = "demo") -> M.KnowledgeModel:
    d = Path(tempfile.mkdtemp())
    (d / "model.md").write_text(
        "---\nname: T\nfolders:\n"
        "  sources: { kind: source, capture: true }\n"
        "  concepts: { kind: concept, promote_after: 3 }\n"
        "  topics: { kind: topic, promote_after: 2 }\n"
        f"bases:\n  {name}: {{ title: Demo }}\n---\n",
        encoding="utf-8")
    (d / "bases").mkdir()
    (d / "bases" / f"{name}.base").write_text(template, encoding="utf-8")
    return M.load_model(d)


SIMPLE = ("views:\n  - type: table\n    name: T\n"
          "    filters:\n      and:\n        - 'sources.length < "
          "{concept_promote_after}'\n    order:\n      - file.name\n")


class ShippedTemplates(unittest.TestCase):
    def test_every_declared_base_renders_and_validates(self):
        models = M.list_models()
        self.assertTrue(models, "no models loaded")
        checked = 0
        for m in models:
            for bname in m.bases:
                with self.subTest(model=m.id, base=bname):
                    text = base_gen.render_base(m, bname)
                    base_gen.check_rendered(text)
                    self.assertNotIn("{", text,
                                     "unresolved placeholder or stray brace")
                    checked += 1
        self.assertGreater(checked, 0, "no shipped model declares a base")

    def test_thresholds_come_from_the_manifest(self):
        m = M.load_model(M.MODELS_DIR / "karpathy-wiki")
        text = base_gen.render_base(m, "promotion-health")
        # concepts promote on the 3rd source; the view must say so.
        self.assertIn('if(file.inFolder("concepts"), 3, 2)', text)
        m.folders["concepts"]["promote_after"] = 5
        self.assertIn('if(file.inFolder("concepts"), 5, 2)',
                      base_gen.render_base(m, "promotion-health"))


class CheckRendered(unittest.TestCase):
    def test_rejects_unknown_top_level_key(self):
        with self.assertRaises(ValueError):
            base_gen.check_rendered("viwes:\n  - type: table\n")

    def test_requires_views(self):
        with self.assertRaises(ValueError):
            base_gen.check_rendered("filters:\n  and:\n    - 'a == 1'\n")

    def test_rejects_tab_indentation(self):
        with self.assertRaises(ValueError):
            base_gen.check_rendered("views:\n\t- type: table\n")

    def test_accepts_a_full_base(self):
        base_gen.check_rendered(
            "filters:\n  and:\n    - 'x'\nformulas:\n  a: 'b'\n"
            "properties:\n  a:\n    displayName: A\n"
            "views:\n  - type: table\n    name: V\n")


class LedgerPolicy(unittest.TestCase):
    def setUp(self):
        self.vault = _FakeVault(Path(tempfile.mkdtemp()) / "v")
        self.model = _make_model(SIMPLE)
        self.path = self.vault.root / "demo.base"

    def _run(self, force=False):
        return base_gen.generate_bases(self.vault, self.model, force=force)

    def test_first_run_writes(self):
        self.assertEqual(self._run(), [("demo", base_gen.WROTE, "created")])
        self.assertTrue(self.path.exists())

    def test_second_run_is_unchanged(self):
        self._run()
        self.assertEqual(self._run(), [("demo", base_gen.UNCHANGED, "")])

    def test_manifest_change_regenerates_our_file(self):
        self._run()
        self.model.folders["concepts"]["promote_after"] = 9
        self.assertEqual(self._run(), [("demo", base_gen.WROTE, "updated")])
        self.assertIn("sources.length < 9", self.path.read_text())

    def test_user_edit_is_never_clobbered(self):
        self._run()
        self.path.write_text("views:\n  - type: table\n    name: MINE\n",
                             encoding="utf-8")
        self.model.folders["concepts"]["promote_after"] = 9
        self.assertEqual(self._run(),
                         [("demo", base_gen.SKIPPED,
                           "edited outside the pipeline")])
        self.assertIn("MINE", self.path.read_text())

    def test_force_reclaims_a_user_edited_file(self):
        self._run()
        self.path.write_text("views:\n  - type: table\n    name: MINE\n",
                             encoding="utf-8")
        self.assertEqual(self._run(force=True),
                         [("demo", base_gen.WROTE, "forced")])
        self.assertNotIn("MINE", self.path.read_text())

    def test_identical_file_without_ledger_is_adopted(self):
        # Second machine: .state/ is gitignored, so the file arrives via git
        # with no ledger entry. Identical content must adopt, not skip.
        self._run()
        (self.vault.state_dir / base_gen.LEDGER_NAME).unlink()
        self.assertEqual(self._run(), [("demo", base_gen.UNCHANGED, "")])

    def test_writes_lf_even_though_yaml_is_multiline(self):
        self._run()
        self.assertNotIn(b"\r\n", self.path.read_bytes())

    def test_broken_template_degrades_and_does_not_raise(self):
        bad = _make_model("views:\n  - name: '{nonexistent_placeholder}'\n")
        results = base_gen.generate_bases(self.vault, bad)
        self.assertEqual(results[0][1], base_gen.FAILED)


class ManifestValidation(unittest.TestCase):
    def _model_with_bases(self, bases_yaml: str) -> Path:
        d = Path(tempfile.mkdtemp())
        (d / "model.md").write_text(
            "---\nname: T\nfolders:\n  sources: { kind: source }\n"
            f"bases:\n{bases_yaml}\n---\n", encoding="utf-8")
        return d

    def test_rejects_unsafe_base_name(self):
        with self.assertRaises(ValueError) as cm:
            M.load_model(self._model_with_bases("  ../escaped: { title: X }"))
        self.assertIn("invalid base name", str(cm.exception))

    def test_rejects_block_list_bases(self):
        # The manifest dialect has no block lists; a habitual `- name` list
        # must fail loudly instead of silently emitting nothing.
        with self.assertRaises(ValueError) as cm:
            M.load_model(self._model_with_bases("  - promotion-health"))
        self.assertIn("must be a mapping", str(cm.exception))

    def test_model_without_bases_is_fine(self):
        d = Path(tempfile.mkdtemp())
        (d / "model.md").write_text(
            "---\nname: T\nfolders:\n  sources: { kind: source }\n---\n",
            encoding="utf-8")
        self.assertEqual(M.load_model(d).bases, {})

    def test_valid_base_names(self):
        for good in ["promotion-health", "capture_log", "a1"]:
            self.assertTrue(M.valid_base_name(good), good)
        for bad in ["../x", "a/b", "", "A", ".hidden"]:
            self.assertFalse(M.valid_base_name(bad), bad)


if __name__ == "__main__":
    unittest.main()
