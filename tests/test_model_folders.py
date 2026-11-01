"""Issue #1 — model folder names are validated as safe single path components,
in both the API-write path and load_model (manual manifests)."""
import tempfile
import unittest
from pathlib import Path

import _util  # noqa: F401  (path bootstrap)
import model_registry as M


class ValidFolderName(unittest.TestCase):
    def test_rejects_traversal_and_separators(self):
        for bad in ["../escaped", "/abs", "a/b", "a\\b", "..", ".", ""]:
            self.assertFalse(M.valid_folder_name(bad), bad)

    def test_rejects_reserved(self):
        for bad in ["output", "scripts", ".state", "index", "SCHEMA", "log"]:
            self.assertFalse(M.valid_folder_name(bad), bad)

    def test_accepts_valid_names(self):
        for good in ["sources", "project_notes", "runbooks", "a-b", "topics"]:
            self.assertTrue(M.valid_folder_name(good), good)


class LoadModelRejectsUnsafe(unittest.TestCase):
    def _model(self, folders_yaml: str) -> Path:
        d = Path(tempfile.mkdtemp())
        (d / "model.md").write_text(
            f"---\nname: T\nfolders:\n{folders_yaml}\n---\n", encoding="utf-8")
        return d

    def test_escaped_folder_raises(self):
        d = self._model("  ../escaped: { kind: source, capture: true }")
        with self.assertRaises(ValueError) as cm:
            M.load_model(d)
        self.assertIn("invalid folder name", str(cm.exception))

    def test_absolute_folder_raises(self):
        d = self._model("  /etc: { kind: source }")
        with self.assertRaises(ValueError):
            M.load_model(d)

    def test_valid_folders_load(self):
        d = self._model("  sources: { kind: source, capture: true }\n"
                        "  project_notes: { kind: note }")
        m = M.load_model(d)
        self.assertEqual(list(m.folders), ["sources", "project_notes"])


if __name__ == "__main__":
    unittest.main()
