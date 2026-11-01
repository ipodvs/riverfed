"""anydoc-first office document conversion (convert.py).

Exercises the office-format tier: anydoc (firecrawl-anydoc) is tried first
for docx/pptx/xlsx/odt/rtf/epub, markitdown remains the fallback. Guards the
four properties the feature promises: document structure survives anydoc,
a missing/failing anydoc degrades silently to markitdown, --converter
markitdown bypasses anydoc entirely, and an explicit --converter anydoc
hard-fails instead of silently falling back.

Structure-preservation tests are gated on the optional deps being installed
(CI runs no pip installs); the tier-logic tests run everywhere by patching
the anydoc helper.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import convert  # noqa: E402

ANYDOC_AVAILABLE = importlib.util.find_spec("anydoc") is not None
MARKITDOWN_AVAILABLE = importlib.util.find_spec("markitdown") is not None
DOCX_AVAILABLE = importlib.util.find_spec("docx") is not None
PPTX_AVAILABLE = importlib.util.find_spec("pptx") is not None

requires_anydoc = unittest.skipUnless(
    ANYDOC_AVAILABLE, "requires optional firecrawl-anydoc dependency"
)


class OfficeConvertBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(self._cleanup_tmp)

    def _cleanup_tmp(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_docx(self) -> Path:
        import docx
        d = docx.Document()
        d.add_heading("Quarterly Report", 1)
        d.add_heading("Revenue", 2)
        t = d.add_table(rows=2, cols=2)
        t.cell(0, 0).text = "Region"
        t.cell(0, 1).text = "Total"
        t.cell(1, 0).text = "EMEA"
        t.cell(1, 1).text = "42"
        d.add_paragraph("First point", style="List Bullet")
        d.add_paragraph("Second point", style="List Bullet")
        path = self.tmp / "fixture.docx"
        d.save(str(path))
        return path

    def _make_pptx(self) -> Path:
        import pptx
        pres = pptx.Presentation()
        slide = pres.slides.add_slide(pres.slide_layouts[1])
        slide.shapes.title.text = "Fixture Deck"
        body = slide.placeholders[1].text_frame
        body.text = "Alpha bullet"
        body.add_paragraph().text = "Beta bullet"
        path = self.tmp / "fixture.pptx"
        pres.save(str(path))
        return path


class TestAnydocHelper(OfficeConvertBase):
    @requires_anydoc
    @unittest.skipUnless(DOCX_AVAILABLE, "requires python-docx to build fixture")
    def test_docx_structure_survives(self) -> None:
        result = convert._convert_office_anydoc(self._make_docx())
        self.assertIsNotNone(result)
        md, method = result
        self.assertEqual(method, "anydoc")
        # Headings survive as markdown headings (anydoc emits ATX).
        self.assertIn("# Quarterly Report", md)
        self.assertIn("## Revenue", md)
        # Table cells survive inside a pipe table.
        self.assertIn("| Region | Total |", md)
        self.assertIn("| EMEA | 42 |", md)
        # List items survive.
        self.assertIn("- First point", md)
        self.assertIn("- Second point", md)

    @requires_anydoc
    @unittest.skipUnless(PPTX_AVAILABLE, "requires python-pptx to build fixture")
    def test_pptx_title_survives(self) -> None:
        result = convert._convert_office_anydoc(self._make_pptx())
        self.assertIsNotNone(result)
        md, _ = result
        # anydoc renders slide titles as headings (level is its choice —
        # assert presence, not level).
        self.assertIn("Fixture Deck", md)
        self.assertIn("Alpha bullet", md)
        self.assertIn("Beta bullet", md)

    def test_import_error_is_silent(self) -> None:
        # Mapping a module to None makes `import anydoc` raise ImportError.
        path = self.tmp / "anything.docx"
        path.write_bytes(b"irrelevant")
        stderr = io.StringIO()
        with mock.patch.dict(sys.modules, {"anydoc": None}):
            with contextlib.redirect_stderr(stderr):
                result = convert._convert_office_anydoc(path)
        self.assertIsNone(result)
        self.assertEqual(stderr.getvalue(), "")

    @requires_anydoc
    def test_parse_error_writes_stderr_returns_none(self) -> None:
        bad = self.tmp / "bad.docx"
        bad.write_bytes(b"this is not a docx at all")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = convert._convert_office_anydoc(bad)
        self.assertIsNone(result)
        self.assertIn("[convert] anydoc failed:", stderr.getvalue())


class TestConverterTiering(OfficeConvertBase):
    def test_auto_prefers_anydoc(self) -> None:
        # An empty file with an office suffix: if auto reaches markitdown,
        # the sentinel assertion below fails.
        path = self.tmp / "doc.docx"
        path.write_bytes(b"")
        with mock.patch.object(
            convert, "_convert_office_anydoc", return_value=("SENTINEL", "anydoc")
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                out = convert.convert_with_markitdown(str(path), converter="auto")
        self.assertEqual(out, "SENTINEL")

    @unittest.skipUnless(MARKITDOWN_AVAILABLE, "requires markitdown")
    @unittest.skipUnless(DOCX_AVAILABLE, "requires python-docx to build fixture")
    def test_markitdown_flag_bypasses_anydoc(self) -> None:
        path = self._make_docx()
        helper = mock.Mock()
        with mock.patch.object(convert, "_convert_office_anydoc", helper):
            with contextlib.redirect_stderr(io.StringIO()):
                out = convert.convert_with_markitdown(
                    str(path), converter="markitdown")
        helper.assert_not_called()
        self.assertIn("Quarterly Report", out)

    @unittest.skipUnless(MARKITDOWN_AVAILABLE, "requires markitdown")
    @unittest.skipUnless(DOCX_AVAILABLE, "requires python-docx to build fixture")
    def test_auto_falls_back_when_anydoc_fails(self) -> None:
        path = self._make_docx()
        with mock.patch.object(
            convert, "_convert_office_anydoc", return_value=None
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                out = convert.convert_with_markitdown(str(path), converter="auto")
        self.assertIn("Quarterly Report", out)

    def test_forced_anydoc_missing_errors(self) -> None:
        path = self.tmp / "doc.docx"
        path.write_bytes(b"irrelevant")
        with mock.patch.object(convert, "_anydoc_available", return_value=False):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    convert.convert_with_markitdown(str(path), converter="anydoc")
        self.assertEqual(ctx.exception.code, 2)

    def test_forced_anydoc_non_office_errors(self) -> None:
        path = self.tmp / "notes.txt"
        path.write_text("plain text", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                convert.convert_with_markitdown(str(path), converter="anydoc")
        self.assertEqual(ctx.exception.code, 2)


class TestExtensionTyping(unittest.TestCase):
    def test_new_extensions_typed(self) -> None:
        self.assertEqual(convert.specific_type("x.odt", "file"), "odt")
        self.assertEqual(convert.specific_type("x.docm", "file"), "docx")
        self.assertEqual(convert.specific_type("x.xlsb", "file"), "xlsx")
        self.assertEqual(convert.specific_type("x.rtf", "file"), "rtf")
        self.assertEqual(convert.specific_type("x.ppsx", "file"), "pptx")


if __name__ == "__main__":
    unittest.main()
