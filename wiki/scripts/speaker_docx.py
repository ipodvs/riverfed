#!/usr/bin/env python3
"""Render a speaker-notes Markdown file to a styled Word .docx, themed by a
design.md (the Studio design picker).

Shared by:
  - wiki/training/scripts/build_speaker_doc.py  (the handbook builder —
    calls with no design = the default house palette)
  - wiki/scripts/studio_guide.py                (the Studio guide generator —
    calls with the chosen --design so the doc matches the deck's identity)

Design tokens map onto the doc the same way the Marp reskin maps them:
  - foundation (reliably dark) -> Title / H1 / H2 / body / bold runs
  - accent (vibrant: primary if vibrant, else highlight) -> H3, the cover
    eyebrow + accent rule, callout/quote left border
  - text-muted -> subtitle + meta greys (never `secondary`, which can be a
    bright accent like Aurora's teal)
  - surface-cream -> inline-code + code-block shading
  - body-md fontFamily -> body font (with a Calibri fallback, since Word
    can't @import web fonts — if the family isn't installed it falls back)

No template required; styles are defined inline so the doc opens cleanly in
any Word version. Saves via a .tmp.docx atomic swap so a doc the user has
open in Word degrades to a sibling file instead of a hard failure.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent.parent


# --------------------------------------------------------------------------- #
# Palette resolution
# --------------------------------------------------------------------------- #

@dataclass
class Palette:
    """Resolved colours + fonts for the doc. Hex fields are 6-char, no '#'."""
    foundation_hex: str = "0f1729"   # dark — headings + body
    accent_hex: str = "4f8cff"       # vibrant — H3, eyebrow, rule, borders
    muted_hex: str = "4a5160"        # subtitle / meta grey
    code_bg_hex: str = "eff1f4"      # inline-code + code-block shading
    rule_grey_hex: str = "c4c7cc"    # hr + code-block left border (neutral)
    body_font: str = "Inter"
    body_fallback: str = "Calibri"
    mono_font: str = "JetBrains Mono"
    mono_fallback: str = "Consolas"
    name: str = "Riverfed"

    @property
    def foundation(self) -> RGBColor:
        return _rgb(self.foundation_hex)

    @property
    def accent(self) -> RGBColor:
        return _rgb(self.accent_hex)

    @property
    def muted(self) -> RGBColor:
        return _rgb(self.muted_hex)


def _rgb(h: str) -> RGBColor:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _norm_hex(v: object) -> str | None:
    """Return a 6-char lowercase hex (no '#') or None if not a hex colour."""
    if not v:
        return None
    s = str(v).strip().lstrip("#")
    if re.fullmatch(r"[0-9A-Fa-f]{3}", s):
        s = "".join(c * 2 for c in s)
    return s.lower() if re.fullmatch(r"[0-9A-Fa-f]{6}", s) else None


def _is_vibrant(hex6: str) -> bool:
    """True if the colour is saturated + mid-lightness enough to read as an
    accent (vs near-black ink or near-white). Mirrors studio_marp.py."""
    try:
        r = int(hex6[0:2], 16) / 255
        g = int(hex6[2:4], 16) / 255
        b = int(hex6[4:6], 16) / 255
    except Exception:
        return True
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    denom = 1 - abs(2 * light - 1)
    sat = 0.0 if mx == mn or denom == 0 else (mx - mn) / denom
    return sat >= 0.30 and 0.18 <= light <= 0.82


def palette_from_design(design_path: str | Path | None) -> Palette:
    """Build a Palette from a design.md, or the default house palette when
    design_path is None / missing / unparseable."""
    p = Palette()
    if not design_path:
        return p
    dp = Path(design_path)
    if not dp.exists():
        sys.stderr.write(f"[speaker_docx] design not found: {dp} — default palette\n")
        return p
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from design_tokens import load_design
        d = load_design(dp)
    except Exception as exc:
        sys.stderr.write(f"[speaker_docx] design load failed: {exc} — default palette\n")
        return p

    c = d.colors or {}
    primary = _norm_hex(c.get("primary"))
    highlight = _norm_hex(c.get("highlight"))
    foundation = _norm_hex(c.get("foundation"))
    # accent: vibrant primary, else highlight (Heritage primary is ink ->
    # its accent lives in the clay highlight)
    accent = primary if (primary and _is_vibrant(primary)) else (highlight or primary)
    # greys: neutral text tokens only, never `secondary` (can be bright)
    muted = _norm_hex(c.get("text-muted")) or _norm_hex(c.get("text-faint"))
    code_bg = _norm_hex(c.get("surface-cream"))

    if foundation:
        p.foundation_hex = foundation
    if accent:
        p.accent_hex = accent
    if muted:
        p.muted_hex = muted
    if code_bg:
        p.code_bg_hex = code_bg
    body_font = d.font_family("body-md", "")
    if body_font:
        p.body_font = body_font
    if d.name:
        p.name = d.name
    return p


# --------------------------------------------------------------------------- #
# DOCX low-level helpers
# --------------------------------------------------------------------------- #

def _set_rfonts(style_or_run_element, font_name: str) -> None:
    rPr = style_or_run_element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("ascii", "hAnsi", "cs"):
        rFonts.set(qn(f"w:{attr}"), font_name)


def _add_paragraph_border(paragraph, side: str, color_hex: str, sz: int = 24) -> None:
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = pPr.find(qn("w:pBdr"))
    if pBdr is None:
        pBdr = OxmlElement("w:pBdr")
        pPr.append(pBdr)
    border = OxmlElement(f"w:{side}")
    border.set(qn("w:val"), "single")
    border.set(qn("w:sz"), str(sz))
    border.set(qn("w:space"), "8")
    border.set(qn("w:color"), color_hex)
    pBdr.append(border)


def _shade_run(run, fill_hex: str) -> None:
    rPr = run._element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    rPr.append(shd)


# --------------------------------------------------------------------------- #
# Renderer
# --------------------------------------------------------------------------- #

INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


class SpeakerDocx:
    def __init__(self, palette: Palette):
        self.pal = palette

    # ---- styles ----

    def _style_heading(self, doc, name, size_pt, color, bold=True,
                       space_before=18, space_after=6):
        style = doc.styles[name]
        style.font.name = self.pal.body_font
        style.font.size = Pt(size_pt)
        style.font.bold = bold
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(space_before)
        style.paragraph_format.space_after = Pt(space_after)
        style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        _set_rfonts(style.element, self.pal.body_font)

    def configure_styles(self, doc):
        normal = doc.styles["Normal"]
        normal.font.name = self.pal.body_font
        normal.font.size = Pt(11)
        normal.font.color.rgb = self.pal.foundation
        normal.paragraph_format.space_after = Pt(8)
        normal.paragraph_format.line_spacing = 1.32
        _set_rfonts(normal.element, self.pal.body_font)

        self._style_heading(doc, "Title", 32, self.pal.foundation,
                            space_before=0, space_after=10)
        self._style_heading(doc, "Subtitle", 16, self.pal.muted, bold=False,
                            space_before=0, space_after=18)
        self._style_heading(doc, "Heading 1", 22, self.pal.foundation,
                            space_before=24, space_after=8)
        self._style_heading(doc, "Heading 2", 16, self.pal.foundation,
                            space_before=18, space_after=6)
        self._style_heading(doc, "Heading 3", 13, self.pal.accent,
                            space_before=12, space_after=4)

        names = [s.name for s in doc.styles]
        if "Callout" not in names:
            callout = doc.styles.add_style("Callout", WD_STYLE_TYPE.PARAGRAPH)
            callout.font.name = self.pal.body_font
            callout.font.size = Pt(11)
            callout.font.italic = True
            callout.font.color.rgb = self.pal.foundation
            callout.paragraph_format.left_indent = Cm(0.6)
            callout.paragraph_format.space_before = Pt(8)
            callout.paragraph_format.space_after = Pt(8)
            callout.paragraph_format.line_spacing = 1.4
            _set_rfonts(callout.element, self.pal.body_font)

    # ---- inline markdown ----

    def _add_inline_runs(self, paragraph, text, base_italic=False):
        remaining = text
        while remaining:
            candidates = []
            m = INLINE_CODE_RE.search(remaining)
            if m:
                candidates.append((m.start(), "code", m))
            m = BOLD_RE.search(remaining)
            if m:
                candidates.append((m.start(), "bold", m))
            m = ITALIC_RE.search(remaining)
            if m:
                candidates.append((m.start(), "italic", m))
            if not candidates:
                r = paragraph.add_run(remaining)
                r.italic = base_italic
                return
            candidates.sort(key=lambda t: t[0])
            idx, kind, match = candidates[0]
            if idx > 0:
                r = paragraph.add_run(remaining[:idx])
                r.italic = base_italic
            content = match.group(1)
            if kind == "code":
                r = paragraph.add_run(content)
                r.font.name = self.pal.mono_font
                r.font.size = Pt(10)
                r.font.color.rgb = self.pal.foundation
                _set_rfonts(r._element, self.pal.mono_font)
                _shade_run(r, self.pal.code_bg_hex)
            elif kind == "bold":
                r = paragraph.add_run(content)
                r.bold = True
                r.italic = base_italic
                r.font.color.rgb = self.pal.foundation
            elif kind == "italic":
                r = paragraph.add_run(content)
                r.italic = True
            remaining = remaining[match.end():]

    # ---- cover ----

    def add_cover(self, doc, eyebrow, title, subtitle, meta):
        if eyebrow:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(eyebrow.upper())
            r.font.name = self.pal.body_font
            r.font.size = Pt(10)
            r.font.bold = True
            r.font.color.rgb = self.pal.accent
            _set_rfonts(r._element, self.pal.body_font)

        h = doc.add_paragraph(style="Title")
        h.add_run(title)
        if subtitle:
            s = doc.add_paragraph(style="Subtitle")
            s.add_run(subtitle)

        rule = doc.add_paragraph()
        rule.paragraph_format.space_before = Pt(0)
        rule.paragraph_format.space_after = Pt(16)
        _add_paragraph_border(rule, "bottom", self.pal.accent_hex, sz=36)

        for line in meta or []:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(line)
            r.font.color.rgb = self.pal.muted
            r.font.size = Pt(10)

    # ---- body ----

    def convert_body(self, body, doc):
        lines = body.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            if line.strip() == "\\newpage":
                doc.add_page_break()
                i += 1
                continue

            if re.match(r"^-{3,}\s*$", line):
                sep = doc.add_paragraph()
                _add_paragraph_border(sep, "bottom", self.pal.rule_grey_hex, sz=6)
                i += 1
                continue

            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                level = len(m.group(1))
                text = m.group(2)
                style = "Heading 1" if level == 1 else ("Heading 2" if level == 2 else "Heading 3")
                p = doc.add_paragraph(style=style)
                self._add_inline_runs(p, text)
                i += 1
                continue

            if line.startswith(">"):
                content = line.lstrip(">").lstrip()
                italic = (content.startswith("*") and content.endswith("*")
                          and content.count("*") == 2)
                if italic:
                    content = content[1:-1]
                p = doc.add_paragraph(style="Callout")
                _add_paragraph_border(p, "left", self.pal.accent_hex, sz=24)
                self._add_inline_runs(p, content, base_italic=italic)
                i += 1
                continue

            if line.startswith("```"):
                i += 1
                code_lines = []
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(10)
                p.paragraph_format.left_indent = Cm(0.4)
                _add_paragraph_border(p, "left", self.pal.rule_grey_hex, sz=24)
                r = p.add_run("\n".join(code_lines))
                r.font.name = self.pal.mono_font
                r.font.size = Pt(9.5)
                r.font.color.rgb = self.pal.foundation
                _set_rfonts(r._element, self.pal.mono_font)
                continue

            if re.match(r"^\s*[-*]\s+", line):
                while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                    content = re.sub(r"^\s*[-*]\s+", "", lines[i])
                    p = doc.add_paragraph(style="List Bullet")
                    self._add_inline_runs(p, content)
                    i += 1
                continue

            if re.match(r"^\s*\d+\.\s+", line):
                while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                    content = re.sub(r"^\s*\d+\.\s+", "", lines[i])
                    p = doc.add_paragraph(style="List Number")
                    self._add_inline_runs(p, content)
                    i += 1
                continue

            if line.strip():
                p = doc.add_paragraph()
                self._add_inline_runs(p, line)
                i += 1
                continue

            i += 1


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    raw = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta = {}
    for line in raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def render_markdown_to_docx(
    md_path: Path,
    out_path: Path,
    design_path: str | Path | None = None,
    *,
    eyebrow: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
) -> Path:
    """Render a speaker-notes .md to a design-styled .docx.

    Returns the path actually written — the canonical out_path normally, or a
    sibling .tmp.docx if Word has the canonical file open (locked)."""
    md_path = Path(md_path)
    out_path = Path(out_path)
    palette = palette_from_design(design_path)
    md_text = md_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(md_text)

    doc_title = title or fm.get("title") or md_path.stem.replace("-", " ").title()
    doc_subtitle = subtitle if subtitle is not None else fm.get("subtitle", "")
    doc_eyebrow = eyebrow if eyebrow is not None else (
        fm.get("eyebrow") or f"{palette.name} · Speaker notes")
    meta = [fm[k] for k in ("author", "date") if fm.get(k)]

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.4)
        section.right_margin = Cm(2.4)

    r = SpeakerDocx(palette)
    r.configure_styles(doc)
    r.add_cover(doc, doc_eyebrow, doc_title, doc_subtitle, meta)
    r.convert_body(body, doc)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic swap: build to .tmp.docx, replace onto canonical. If Word has the
    # canonical open (exclusive lock on Windows), keep the .tmp.docx.
    tmp = out_path.with_suffix(".tmp.docx")
    doc.save(str(tmp))
    try:
        tmp.replace(out_path)
        return out_path
    except PermissionError:
        sys.stderr.write(
            f"[speaker_docx] {out_path.name} is locked (close Word to swap); "
            f"wrote {tmp.name} instead\n")
        return tmp
