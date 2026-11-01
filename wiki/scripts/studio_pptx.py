#!/usr/bin/env python3
"""Studio: native PowerPoint renderer (sibling of studio_marp.py).

Two-step pipeline:
  1. Ask Claude Code for a JSON slide structure drawn from the wiki.
  2. Render that JSON into a real .pptx via python-pptx so every slide
     is editable in PowerPoint (real text boxes, real shapes, theme
     colours, embedded brand icons — no flattened HTML).

13 slide types are registered in SLIDE_RENDERERS. Choose between them
in the JSON spec via the "type" field:

  Identity / opener
    cover      — title slide with brand logo + scattered dot pattern
    lead       — single big-idea statement, hero typography
    section    — module divider with giant ghost numeral

  Workhorse content
    content    — bulleted slide with optional dark callout band
    quote      — verbatim quote with vertical accent bar + decorative "

  Numbers
    kpi        — 1-3 hero tiles for raw counts / multipliers / dollars
    donut-kpi  — 1-3 ring charts for percentages

  Comparisons + relationships
    versus     — old / new two-panel comparison with center arrow
    hub        — central concept + 3-6 radial spokes
                 (use when items are CHILDREN of one named parent)

  Collections
    cards      — 2-4 unordered parallel siblings
    six-up     — 3x2 grid for tight catalogues of ≤6 items

  Process
    flow       — 3-5 sequential steps connected by arrows
    timeline   — 3-6 chronological milestones on a horizontal track

Design system rules — see wiki/training/design.md for the source of
truth. Key mechanics implemented here:

  Background:    cream gradient on content slides; deep-space gradient
                 on cover / section. _slide_gradient_background helper.

  Typography:    Inter (titles + body) + JetBrains Mono (technical labels).
                 Alternate Studio designs may override the artifact fonts,
                 but never the Riverfed wordmark fonts.

  Capped cards:  _add_capped_card draws kpi/cards/flow/six-up cells as
                 a SINGLE rounded rect with a 4-stop hard-edge gradient
                 (accent stripe + white body share the rounded corners).
                 Avoids the "two-shape stuck-on stripe" look.

  Brand mark:    _add_brand_mark drops a small saber-blue diamond
                 top-right on every content-style slide — per design.md
                 "Decorative top-right diamond in accent on content
                 slides". Cover gets the full brand logo instead.

  Icons:         landing/icons/png/<name>{-accent}.png. _add_icon
                 resolves the accent → file suffix via
                 ICON_ACCENT_SUFFIX so each cell's icon matches its
                 accent colour.

  Transparency:  Donut PNGs are post-processed (PIL alpha-scale on
                 whiteness) because svglib+reportlab always renders
                 to opaque white. See _png_white_to_transparent.

Usage (from repo root):
    py -3.13 wiki/scripts/studio_pptx.py \\
        --wiki wiki \\
        --prompt "How operators use Claude Code in marketing" \\
        --slides 12 \\
        --audience "Builders who already know what an agent is"

Companion builder (same renderer, content from a hand-curated dict
instead of a Claude-generated JSON):
    .venv\\Scripts\\python.exe wiki/training/scripts/build_handbook_pptx.py
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# The provider layer, imported at module level because the
# --provider help text is built from it during argparse setup.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_runner  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DESIGN_MD_REL = "wiki/training/design.md"
DEFAULT_OUT_DIR = "wiki/training/studio"
ICONS_PNG_DIR = ROOT / "landing" / "icons" / "png"

# === Brand palette (mirrors wiki/training/design.md → Jedi palette) ===
COL_BG_DARK      = "0a0d12"   # space — cover / section base
COL_BG_DARK_HI   = "1a2540"   # cover gradient top stop
COL_BG_DARK_LO   = "05080d"   # cover gradient bottom stop
COL_BG_CREAM     = "fafaff"   # content slide canvas
COL_BG_CREAM_HI  = "ffffff"   # cream gradient top
COL_BG_CREAM_LO  = "eef0f8"   # cream gradient bottom
COL_PANEL_DARK   = "0f1729"   # KPI tile / callout bg on dark
COL_PANEL_GREY   = "f3f4f7"   # KPI tile bg on cream (muted panel)
COL_CARD_BORDER  = "d4d8e0"   # card hairline border
COL_ACCENT_BLUE  = "4f8cff"   # primary — Guardian saber
COL_NEURAL       = "7a59e2"   # purple — Mace
COL_GREEN        = "46c98b"   # Yoda
COL_YELLOW       = "ffd93d"   # Sentinel + Star Wars logo gold
COL_TEXT_DARK    = "0f1729"
COL_TEXT_LIGHT   = "e6e8ee"
COL_TEXT_MUTED   = "9aa3b5"
COL_TEXT_FAINT   = "6e7686"
COL_GREY3        = "4a5160"
COL_SECTION_GHOST = "1a2540"  # the giant numeral colour on section bg

# === Typography ===
# Canonical Riverfed artifact fonts. PowerPoint substitutes locally when
# they are not installed, but the document keeps the brand font names.
FONT_BODY    = "Inter"
FONT_DISPLAY = "Inter"
FONT_MONO    = "JetBrains Mono"

# The wordmark is outside the selectable artifact design: "Riverfed" in
# Inter 900 plus the green signature dot, whatever design the deck uses.
FONT_BRAND   = "Inter"

# === Helpers ===

def slugify(s: str, max_len: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].rstrip("-") or "untitled-deck"


# === Claude prompt → asks for a strict JSON structure ===

# NOTE: this string is consumed via str.format(), so every LITERAL brace
# must be doubled ({{ }}). Only the named placeholders below stay single:
# {prompt} {design_md} {wiki} {slides} {audience} {out_json}. A stray
# single brace in prose/JSON (e.g. "{title, desc}") raises KeyError at
# format() time. After editing, re-run a .format() round-trip to verify.
PROMPT_TEMPLATE = """\
You are the Riverfed studio agent. Generate a slide deck as
*structured JSON* — no Marp markdown, no narrative text outside the
JSON.

User request: {prompt}

Requirements:
- Read the design system at `{design_md}` for voice (direct, concrete,
  no hedging) and the Jedi palette for context. We're rendering to
  native PowerPoint so the components are simpler than Marp.
- Draw content from the wiki at `{wiki}/`. Cite source slugs in the
  `cite` field on slides with non-obvious claims.
- Target ~{slides} slides total.
- Audience: {audience}.
- The Sith Red rule applies: red is for errors only; never use as a
  decorative accent.

Output one JSON object with this exact shape:

```json
{{
  "title": "Deck title",
  "subtitle": "One-line subtitle",
  "audience": "Same audience string",
  "slides": [
    {{ "type": "cover",   "title": "...", "subtitle": "...", "tags": ["25 sources", "Riverfed"] }},
    {{ "type": "lead",    "headline": "Big single statement", "eyebrow": "Optional eyebrow", "cite": "concepts/..." }},
    {{ "type": "section", "number": "01", "module": "Module 1", "title": "Foundations", "subtitle": "..." }},
    {{ "type": "content", "eyebrow": "Optional eyebrow", "title": "...", "bullets": ["bullet 1", "bullet 2", "..."], "callout": "Optional dark band at bottom", "cite": "sources/..." }},
    {{ "type": "kpi",     "title": "...", "kpis": [
        {{ "value": "20×",   "label": "Programmer productivity" }},
        {{ "value": "$100B", "label": "Solo-founder companies" }}
      ], "callout": "Optional bolded statement", "cite": "sources/..." }},
    {{ "type": "quote",   "quote": "Verbatim quote.", "attribution": "— Speaker name", "cite": "sources/..." }},
    {{ "type": "versus",  "title": "...", "old": {{ "title": "Then", "desc": "...", "bullets": ["...", "..."] }}, "new": {{ "title": "Now", "desc": "...", "bullets": ["...", "..."] }}, "callout": "Optional bottom band", "cite": "sources/..." }},
    {{ "type": "cards",   "title": "...", "cards": [
        {{ "num": "01", "title": "Foundations", "desc": "Short 1-2 sentence description." }},
        {{ "num": "02", "title": "Architecture", "desc": "..." }},
        {{ "num": "03", "title": "Build & Operate", "desc": "..." }},
        {{ "num": "04", "title": "Marketing", "desc": "..." }}
      ], "callout": "Optional bottom band", "cite": "sources/..." }},
    {{ "type": "six-up",  "title": "...", "items": [
        {{ "num": "01", "title": "...", "desc": "Short — fits in a small card." }},
        ... up to 6 items
      ], "cite": "concepts/..." }},
    {{ "type": "flow",    "title": "...", "steps": [
        {{ "num": "01", "title": "Step name", "desc": "Short.", "icon": "cog" }},
        {{ "num": "02", "title": "...",      "desc": "...",    "icon": "..." }},
        ... 3-5 steps
      ], "callout": "Optional band", "cite": "..." }},
    {{ "type": "donut-kpi", "title": "...", "kpis": [
        {{ "value": "75%", "label": "Adoption after 90 days" }},
        ... 1-3 percentage stats
      ], "callout": "Optional band", "cite": "..." }},
    {{ "type": "timeline",  "title": "...", "milestones": [
        {{ "label": "DAY 0",  "title": "Define",  "desc": "Write agents.md." }},
        {{ "label": "DAY 30", "title": "First wins", "desc": "Real tasks land." }},
        ... 3-6 milestones
      ], "callout": "Optional band", "cite": "..." }},
    {{ "type": "hub", "title": "...", "hub": "AIOS", "spokes": [
        {{ "title": "C1 · Context", "desc": "What the agent knows." }},
        {{ "title": "C2 · Connections", "desc": "API + CLI tools." }},
        ... 3-6 spokes
      ], "callout": "Optional band", "cite": "..." }}
  ]
}}
```

Slide-type rules:
- Always start with one `cover`, end with one `lead` (the closer).
- Use at most one `section` divider per major module.
- `content` is the workhorse — 3-6 bullets per slide, ≤12 words each.
- `kpi` is for quantitative emphasis — 3 KPIs max per slide.
- `quote` is for verbatim source citation.
- `versus` for old-vs-new comparisons — keep bullets to 3-4 per side.
- `cards` for "the N pieces" / module overviews — 2 to 4 cards, each
  description ≤2 short sentences.
- `six-up` for "the six concepts / principles / steps" — exactly the
  fit for tight catalogues; descriptions ≤10 words each.
- `flow` for sequential processes where the ORDER matters (pipeline,
  onboarding, playbook). 3-5 steps, each ≤2-line description. Choose
  `flow` over `cards` whenever there's a left-to-right progression.
- `donut-kpi` for percent-only metrics — 1-3 ring charts with the
  percentage in the centre. Values MUST be percentages (e.g. "30%",
  "90%"). For raw counts, multipliers, or dollar amounts, use `kpi`.
- `timeline` for chronological milestones — 3-6 dots on a horizontal
  line, each with `label` (eyebrow like "DAY 30"), `title` (short),
  `desc` (1-2 lines below the line). Use for cadence, onboarding
  ramp, roadmap.
- `hub` for "the N parts of <thing>" — central concept with 3-6
  radial spokes. The `hub` field is the short central word (e.g.
  "AIOS"). Each spoke is {{title, desc}}. Use when items are CHILDREN
  of one named parent (vs `cards` for unrelated siblings).
- Include `cite` on any slide that draws a non-obvious claim from a
  specific source — value is the wiki slug (e.g. `sources/building-ai-agents`).
- ICONS: the `icon` field (on flow/cards/six-up steps) MUST be one of these
  exact names — do NOT invent others (unknown names render blank):
  {icons}
  Pick the closest match; omit `icon` entirely if none fits.

Write the JSON to `{out_json}`. Do not output anything else to stdout.
When done, print a single line:
  WROTE {out_json}
"""


def _available_icon_names() -> list[str]:
    """The icon base names the renderer can actually embed — scanned live
    from the icon bank so the prompt never drifts from what exists. Strips
    colour-variant suffixes (-purple/-green/-yellow) and the brand logos
    (not slide icons)."""
    names: set[str] = set()
    for p in ICONS_PNG_DIR.glob("*.png"):
        stem = re.sub(r"-(purple|green|yellow)$", "", p.stem)
        if stem.startswith(("riverfed-mark",)):
            continue
        names.add(stem)
    return sorted(names)


def get_claude_json(wiki: str, user_prompt: str, slides: int,
                    audience: str, out_json: Path,
                    provider_arg: str = "auto") -> dict | None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    icons = _available_icon_names()
    prompt = PROMPT_TEMPLATE.format(
        prompt=user_prompt, wiki=wiki, slides=slides, audience=audience,
        design_md=DESIGN_MD_REL,
        icons=", ".join(icons) if icons else "(none available)",
        out_json=out_json.relative_to(ROOT).as_posix(),
    )
    # Agent invocation goes through the provider layer (A6 step 1).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _wikis import resolve_vault_dir
    wiki_dir = resolve_vault_dir(wiki)
    provider, pstatus = agent_runner.resolve_provider(provider_arg)
    if provider is None:
        print(f"Error: {agent_runner.unavailable_message(pstatus)}",
              file=sys.stderr)
        return None

    print(f"[studio_pptx] asking the agent for slide JSON…", file=sys.stderr)
    try:
        res = agent_runner.run(prompt, cwd=ROOT, timeout=600,
                               add_dirs=[ROOT, wiki_dir], provider=provider)
    except FileNotFoundError:
        print(f"Error: the {provider} CLI could not be executed.",
              file=sys.stderr)
        return None
    if res.timed_out:
        print("Error: generation timed out after 10 minutes.", file=sys.stderr)
        return None

    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        return None
    if not out_json.exists():
        print(f"Error: the agent did not write {out_json}", file=sys.stderr)
        sys.stderr.write(res.output or "")
        return None
    try:
        return json.loads(out_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: the agent wrote invalid JSON: {exc}", file=sys.stderr)
        return None


# === python-pptx renderer ===

def _hex(value: str):
    """Hex string → pptx RGBColor."""
    from pptx.dml.color import RGBColor
    return RGBColor.from_string(value)


def _set_solid_fill(shape, hex_color: str) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = _hex(hex_color)
    shape.line.fill.background()


def _set_gradient_fill(shape, stops, angle_deg: float = 90) -> None:
    """Replace the shape's fill with a linear gradient.

    stops: list of (position, hex) where position ∈ [0, 100000].
    angle_deg: 0 = left→right, 90 = top→bottom, 135 = top-left → bottom-right.
    """
    from lxml import etree
    from pptx.oxml.ns import qn
    # Ensure a solidFill child exists at the right schema position;
    # we'll swap it for our gradFill.
    shape.fill.solid()
    spPr = shape._element.spPr
    solid = spPr.find(qn("a:solidFill"))
    if solid is None:
        return

    grad = etree.Element(qn("a:gradFill"))
    grad.set("rotWithShape", "1")
    gsLst = etree.SubElement(grad, qn("a:gsLst"))
    for pos, hex_color in stops:
        gs = etree.SubElement(gsLst, qn("a:gs"))
        gs.set("pos", str(int(pos)))
        srgb = etree.SubElement(gs, qn("a:srgbClr"))
        srgb.set("val", hex_color.lstrip("#").lower())
    lin = etree.SubElement(grad, qn("a:lin"))
    lin.set("ang", str(int(angle_deg * 60000)))   # 1° = 60000 EMU
    lin.set("scaled", "1")

    solid.addnext(grad)
    spPr.remove(solid)


def _add_shadow(shape, blur_pt: float = 8, dist_pt: float = 4,
                alpha_pct: int = 30, angle_deg: float = 90) -> None:
    """Outer drop shadow. Inserted at the right schema position so
    PowerPoint accepts the file cleanly."""
    from lxml import etree
    from pptx.oxml.ns import qn
    spPr = shape._element.spPr
    for old in spPr.findall(qn("a:effectLst")):
        spPr.remove(old)

    effectLst = etree.Element(qn("a:effectLst"))
    outerShdw = etree.SubElement(effectLst, qn("a:outerShdw"))
    outerShdw.set("blurRad", str(int(blur_pt * 12700)))   # 1pt = 12700 EMU
    outerShdw.set("dist", str(int(dist_pt * 12700)))
    outerShdw.set("dir", str(int(angle_deg * 60000)))
    outerShdw.set("rotWithShape", "0")
    srgbClr = etree.SubElement(outerShdw, qn("a:srgbClr"))
    srgbClr.set("val", "000000")
    alpha_el = etree.SubElement(srgbClr, qn("a:alpha"))
    alpha_el.set("val", str(int(alpha_pct * 1000)))

    # Insert after a:ln if present, else after any fill node
    ln = spPr.find(qn("a:ln"))
    if ln is not None:
        ln.addnext(effectLst)
        return
    for tag in ("a:noFill", "a:solidFill", "a:gradFill",
                "a:blipFill", "a:pattFill", "a:grpFill"):
        fill = spPr.find(qn(tag))
        if fill is not None:
            fill.addnext(effectLst)
            return
    spPr.append(effectLst)


def _set_corner_radius(shape, fraction: float = 0.5) -> None:
    """For ROUNDED_RECTANGLE: 0 = no rounding, 0.5 = full pill on the
    short axis."""
    try:
        shape.adjustments[0] = fraction
    except (IndexError, AttributeError):
        pass


def _add_wordmark_kicker(slide, x_in, y_in, w_in, h_in, *, font_size=11):
    """The Riverfed wordmark as a two-run textbox: "Riverfed" in Inter
    plus the signature dot in brand green (design.md "Brand mark")."""
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    tx = slide.shapes.add_textbox(Inches(x_in), Inches(y_in),
                                  Inches(w_in), Inches(h_in))
    tf = tx.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    for text, font, color, size_scale in (
        ("Riverfed", FONT_BRAND, COL_TEXT_LIGHT, 1.0),
        (".",        FONT_BRAND, COL_GREEN, 1.0),
    ):
        run = p.add_run()
        run.text = text
        run.font.size = Pt(font_size * size_scale)
        run.font.bold = True
        run.font.name = font
        run.font.color.rgb = RGBColor.from_string(color)
    return tx


_INLINE_RE = re.compile(r"<strong>(.*?)</strong>", re.S)


def _split_inline(line: str):
    """Split a line into (chunk, kind) pairs for run-level styling.

    kind is 'text' | 'strong'. `<strong>` needs its own run because the Marp
    deck renders a callout's lead-in phrase in the accent colour, and
    flattening it lost that emphasis entirely. A line without `<strong>`
    returns a single 'text' chunk, so this is a no-op for almost every string.

    (Until 2026-11-01 this also re-styled the old split wordmark wherever it
    appeared in text. "Riverfed" is a plain word in prose, so only the cover
    kicker carries the logo now.)
    """
    out, pos = [], 0
    for m in _INLINE_RE.finditer(line):
        if m.start() > pos:
            out.append((line[pos:m.start()], "text"))
        out.append((m.group(1), "strong"))
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], "text"))
    return out or [(line, "text")]


def _add_text(slide, x_in, y_in, w_in, h_in, text, *,
              font_size=18, bold=False, color=COL_TEXT_DARK,
              font=None, align="left", valign="top"):
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    if font is None:
        font = FONT_BODY
    tx = slide.shapes.add_textbox(Inches(x_in), Inches(y_in),
                                  Inches(w_in), Inches(h_in))
    tf = tx.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    if valign == "middle":
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    elif valign == "bottom":
        tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if align == "center":
            p.alignment = PP_ALIGN.CENTER
        elif align == "right":
            p.alignment = PP_ALIGN.RIGHT
        # Inline <strong> gets its own accent run; handled here rather than
        # in each renderer so every slide type gets it for free.
        for chunk, kind in _split_inline(line):
            r = p.add_run()
            r.text = chunk
            r.font.bold = bold
            if kind == "strong":
                # Matches the Marp callout, whose lead-in phrase is accent.
                r.font.name = font
                r.font.size = Pt(font_size)
                r.font.bold = True
                r.font.color.rgb = _hex(COL_ACCENT_BLUE)
            else:
                r.font.name = font
                r.font.size = Pt(font_size)
                r.font.color.rgb = _hex(color)
    return tx


def _add_filled_rect(slide, x_in, y_in, w_in, h_in, fill_hex):
    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                Inches(x_in), Inches(y_in),
                                Inches(w_in), Inches(h_in))
    _set_solid_fill(sh, fill_hex)
    return sh


def _add_gradient_rect(slide, x_in, y_in, w_in, h_in, stops,
                        angle_deg: float = 90):
    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                Inches(x_in), Inches(y_in),
                                Inches(w_in), Inches(h_in))
    sh.line.fill.background()
    _set_gradient_fill(sh, stops, angle_deg=angle_deg)
    return sh


def _add_rounded_rect(slide, x_in, y_in, w_in, h_in, fill_hex,
                      stroke_hex=None, stroke_pt=1.5, corner_fraction=0.05):
    """Slightly-rounded rectangle. Default corner_fraction=0.05 gives a
    clean modern feel; pass 0.5 for a full pill shape."""
    from pptx.util import Inches, Pt
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Inches(x_in), Inches(y_in),
                                Inches(w_in), Inches(h_in))
    if corner_fraction is not None:
        _set_corner_radius(sh, corner_fraction)
    _set_solid_fill(sh, fill_hex)
    if stroke_hex:
        sh.line.color.rgb = _hex(stroke_hex)
        sh.line.width = Pt(stroke_pt)
    else:
        sh.line.fill.background()
    return sh


def _add_capped_card(slide, x_in, y_in, w_in, h_in, accent_hex, *,
                      stripe_side="top", stripe_in=0.14,
                      corner_fraction=0.05,
                      border_hex=COL_CARD_BORDER, border_pt=1.0,
                      shadow_blur=12, shadow_dist=4, shadow_alpha=14):
    """A white rounded card with a SOLID accent stripe on one side.

    This used to be a single shape whose stripe came from a 4-stop gradient
    with two stops at the same position, relying on the renderer treating
    that as a hard edge. Keynote does not: it interpolates from the first
    stop to the last, washing the entire card in accent-to-white. The result
    looked nothing like the Marp `border-left: 4px solid` it was imitating,
    and on a six-card slide it read as a rainbow of gradients.

    Two solid shapes are unambiguous everywhere. The stripe is inset by the
    corner radius so it cannot overhang the card's rounded corners, which is
    what the single-shape approach was avoiding in the first place.

    stripe_side: 'top' | 'bottom' | 'left' | 'right'
    stripe_in:   thickness of the accent stripe in inches

    Returns the card shape."""
    rect = _add_rounded_rect(slide, x_in, y_in, w_in, h_in, "ffffff",
                              stroke_hex=border_hex, stroke_pt=border_pt,
                              corner_fraction=corner_fraction)
    # Inset the stripe by roughly the corner radius so it stays inside the
    # rounded outline instead of poking past it.
    inset = min(corner_fraction * min(w_in, h_in), stripe_in * 1.5)
    if stripe_side == "top":
        sx, sy, sw, sh = x_in + inset, y_in, w_in - 2 * inset, stripe_in
    elif stripe_side == "bottom":
        sx, sy, sw, sh = (x_in + inset, y_in + h_in - stripe_in,
                          w_in - 2 * inset, stripe_in)
    elif stripe_side == "left":
        sx, sy, sw, sh = x_in, y_in + inset, stripe_in, h_in - 2 * inset
    elif stripe_side == "right":
        sx, sy, sw, sh = (x_in + w_in - stripe_in, y_in + inset,
                          stripe_in, h_in - 2 * inset)
    else:
        raise ValueError(f"unknown stripe_side: {stripe_side}")
    _add_filled_rect(slide, sx, sy, sw, sh, accent_hex)
    if shadow_blur > 0:
        _add_shadow(rect, blur_pt=shadow_blur, dist_pt=shadow_dist,
                    alpha_pct=shadow_alpha)
    return rect


def _add_pill(slide, x_in, y_in, text, *, fill_hex, text_hex,
              padding_x=0.22, height=0.34, font_size=11):
    """Solid rounded-pill chip with mono text inside. Width auto-sized
    from text length using a compact monospace character-width estimate."""
    char_w = font_size / 120.0   # roughly 0.083in per character at 10pt
    w_in = max(0.7, len(text) * char_w + 2 * padding_x)
    sh = _add_rounded_rect(slide, x_in, y_in, w_in, height, fill_hex,
                           corner_fraction=0.5)
    _add_text(slide, x_in, y_in, w_in, height, text,
              font_size=font_size, bold=True, color=text_hex,
              font=FONT_MONO, align="center", valign="middle")
    return sh


def _send_to_back(shape) -> None:
    """Move a shape to render under everything else on the slide."""
    spTree = shape._element.getparent()
    spTree.remove(shape._element)
    spTree.insert(2, shape._element)


# Accent colour → icon filename suffix (matches landing/icons/build.py
# ACCENT_VARIANTS). Default (saber-blue) has no suffix.
ICON_ACCENT_SUFFIX = {
    COL_ACCENT_BLUE: "",
    COL_NEURAL:      "-purple",
    COL_GREEN:       "-green",
    COL_YELLOW:      "-yellow",
}


def _add_icon(slide, icon_name, x_in, y_in, size_in=0.5, accent_hex=None):
    """Embed a house icon PNG on the slide.

    icon_name: the file stem under landing/icons/png/ (e.g. "folder-spark").
    accent_hex: optional saber colour (e.g. COL_NEURAL); when provided,
    looks up the matching colour variant (`<icon>-purple.png` etc.) so
    the icon visually ties to its cell's accent. Defaults to saber-blue."""
    from pptx.util import Inches
    if not icon_name:
        return None
    suffix = ICON_ACCENT_SUFFIX.get(accent_hex, "") if accent_hex else ""
    icon_path = ICONS_PNG_DIR / f"{icon_name}{suffix}.png"
    if not icon_path.exists():
        # Fall back to the default variant before giving up
        fallback = ICONS_PNG_DIR / f"{icon_name}.png"
        if fallback.exists():
            icon_path = fallback
        else:
            sys.stderr.write(f"warning: icon not found: {icon_path}\n")
            return None
    return slide.shapes.add_picture(
        str(icon_path),
        Inches(x_in), Inches(y_in),
        Inches(size_in), Inches(size_in))


def _set_fill_opacity(shape, opacity_pct: float) -> None:
    """Set the alpha on a solid-fill colour, 0-100. Adds <a:alpha> inside
    the existing srgbClr — assumes shape was filled with _set_solid_fill
    first."""
    from lxml import etree
    from pptx.oxml.ns import qn
    spPr = shape._element.spPr
    solid = spPr.find(qn("a:solidFill"))
    if solid is None:
        return
    srgb = solid.find(qn("a:srgbClr"))
    if srgb is None:
        return
    for old in srgb.findall(qn("a:alpha")):
        srgb.remove(old)
    alpha = etree.SubElement(srgb, qn("a:alpha"))
    alpha.set("val", str(int(opacity_pct * 1000)))


def _add_brand_mark(slide, color: str | None = None) -> None:
    """The Riverfed dot, top right, on content-style slides.

    It is a CIRCLE, not a diamond: the brand mark is literally the dot from
    the wordmark, in the per-project signature colour. A lozenge is a
    decorative ornament, which design.md bans; the dot is the identity.

    `color` defaults to None and resolves to COL_ACCENT_BLUE at CALL time,
    not definition time. As a default argument it was bound once at import,
    before _apply_design() rewrites the palette, so every deck kept the
    original accent regardless of the design chosen: a green Riverfed
    deck, and an Aurora or Heritage deck, all got the same blue diamond.
    """
    if color is None:
        color = COL_ACCENT_BLUE
    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE
    d = 0.125
    dot = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                 Inches(12.95), Inches(0.38),
                                 Inches(d), Inches(d))
    _set_solid_fill(dot, color)
    dot.line.fill.background()
    dot.shadow.inherit = False


def _add_cover_rings(slide) -> None:
    """Concentric rings bleeding off the right edge, mirroring the Marp
    cover's motif so the two renderers produce the same deck.

    Replaces the previous scattered-dot field, which diverged from the Marp
    cover AND broke the design's own rule: "no ambient glow, blue-purple
    gradient, scattered-dot field, or neon shadow". Two rings, one accent,
    one neutral: structure rather than atmosphere.
    """
    from pptx.util import Inches, Pt
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.dml.color import RGBColor

    # (centre_x, centre_y, radius_in, hex, line_pt) — centres sit off the
    # right edge so only the arc shows, as in the CSS version.
    for cx, cy, r, hexcol, width in (
        (11.9, 2.05, 4.35, COL_ACCENT_BLUE, 26),
        (11.9, 2.05, 2.75, "2a2f3a", 22),
    ):
        ring = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(cx - r), Inches(cy - r),
            Inches(r * 2), Inches(r * 2))
        ring.fill.background()
        ring.line.color.rgb = RGBColor.from_string(hexcol.upper())
        ring.line.width = Pt(width)
        ring.shadow.inherit = False
        # Deliberately NOT _send_to_back: the gradient background rectangle is
        # added first, so sending the rings behind it hides them completely.
        # Cover text is added after this call and therefore stays on top.


def _add_cover_decoration(slide) -> None:
    """Deprecated: the scattered-dot cover. Kept only so an older deck spec
    that calls it still renders. New covers use _add_cover_rings."""
    import random
    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE
    rng = random.Random(42)
    # 14 dots (was 22), all saber-blue, opacity 15-40%. Avoid heavy
    # clustering in the centre-left where the headline sits.
    placements = []
    for _ in range(14):
        x = rng.uniform(0.1, 12.9)
        y = rng.uniform(0.1, 7.2)
        if 2.5 < y < 6.0 and 0.5 < x < 11:
            size = rng.uniform(0.08, 0.18)
        else:
            size = rng.uniform(0.12, 0.42)
        placements.append((x, y, size, rng.uniform(15, 40)))
    for x, y, size, opacity in placements:
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                      Inches(x), Inches(y),
                                      Inches(size), Inches(size))
        _set_solid_fill(dot, COL_ACCENT_BLUE)
        _set_fill_opacity(dot, opacity)
        dot.line.fill.background()


def _slide_background(slide, hex_color):
    """Flat-colour full-bleed background, sent to back."""
    sh = _add_filled_rect(slide, 0, 0, 13.333, 7.5, hex_color)
    _send_to_back(sh)
    return sh


def _slide_gradient_background(slide, stops, angle_deg: float = 90):
    """Gradient full-bleed background, sent to back."""
    sh = _add_gradient_rect(slide, 0, 0, 13.333, 7.5, stops,
                             angle_deg=angle_deg)
    _send_to_back(sh)
    return sh


# --- per-slide-type renderers ---

def render_cover(slide, data):
    # Atmospheric three-stop gradient: deep blue top-left → space-dark
    # bottom-right. Mimics the Marp radial.
    _slide_gradient_background(slide, [
        (0,       COL_BG_DARK_HI),
        (50000,   COL_BG_DARK),
        (100000,  COL_BG_DARK_LO),
    ], angle_deg=135)

    # Concentric ring motif, matching the Marp cover
    _add_cover_rings(slide)

    # Brand kicker (left). Wordmark rule (design.md): "Riverfed" in the
    # display family plus the green signature dot.
    _add_wordmark_kicker(slide, 0.6, 0.55, 7, 0.4, font_size=11)

    # Wordmark-only branding (design.md): the kicker text above is the
    # cover's brand presence — no pictorial mark anywhere on slides.

    # Headline — push to display weight + larger
    _add_text(slide, 0.6, 2.4, 12.1, 3.3,
              data.get("title", "Untitled deck"),
              font_size=68, bold=True, color="ffffff",
              font=FONT_DISPLAY, valign="bottom")

    if data.get("subtitle"):
        _add_text(slide, 0.6, 5.85, 12.1, 0.9,
                  data["subtitle"], font_size=22,
                  color=COL_TEXT_MUTED, font=FONT_BODY)

    # Tag pills, matching the Marp cover's .tag-row (bordered capsules) rather
    # than a dot-separated string. Capsule geometry is sanctioned here:
    # design.md reserves `pill` for compact tags, which is exactly this.
    tags = data.get("tags") or []
    x, font_size, padding_x = 0.6, 11, 0.22
    for tag in tags:
        tag = str(tag)
        # Mirror _add_pill's own auto-sizing so the next pill starts clear.
        width = max(0.7, len(tag) * (font_size / 120.0) + 2 * padding_x)
        _add_pill(slide, x, 6.78, tag, fill_hex=COL_PANEL_DARK,
                  text_hex="ffffff", font_size=font_size, padding_x=padding_x)
        x += width + 0.14


def render_lead(slide, data):
    # Subtle cream gradient
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)

    # Vertical accent rail (left side, ~60% slide height)
    _add_filled_rect(slide, 0.6, 2.3, 0.08, 3.2, COL_ACCENT_BLUE)

    if data.get("eyebrow"):
        _add_text(slide, 0.9, 2.38, 11.6, 0.32,
                  data["eyebrow"].upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.9, 2.85, 11.6, 3.2,
              data.get("headline", ""),
              font_size=58, bold=True, color=COL_TEXT_DARK,
              font=FONT_DISPLAY)

    if data.get("cite"):
        _add_text(slide, 0.9, 7.05, 11.6, 0.3, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_section(slide, data):
    # Dark gradient with subtle blue cast on the left
    _slide_gradient_background(slide, [
        (0,       "0e1830"),
        (60000,   COL_BG_DARK),
        (100000,  COL_BG_DARK_LO),
    ], angle_deg=90)

    # Vertical accent rail
    _add_filled_rect(slide, 0.6, 2.6, 0.08, 3.5, COL_ACCENT_BLUE)

    # Giant ghost numeral on the right
    if data.get("number"):
        _add_text(slide, 7.0, 0.5, 6.2, 7.0,
                  data["number"], font_size=340, bold=True,
                  color=COL_SECTION_GHOST, font=FONT_DISPLAY,
                  align="right", valign="middle")

    if data.get("module"):
        _add_text(slide, 0.9, 2.6, 7.5, 0.4,
                  data["module"].upper(),
                  font_size=14, bold=True, color=COL_ACCENT_BLUE,
                  font=FONT_MONO)

    _add_text(slide, 0.9, 3.1, 7.5, 1.8,
              data.get("title", ""),
              font_size=66, bold=True, color="ffffff",
              font=FONT_DISPLAY)

    if data.get("subtitle"):
        _add_text(slide, 0.9, 5.05, 7.5, 1.6,
                  data["subtitle"], font_size=20,
                  color=COL_TEXT_MUTED, font=FONT_BODY)


def render_content(slide, data):
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.4,
              data.get("title", ""),
              font_size=40, bold=True, color=COL_TEXT_DARK,
              font=FONT_DISPLAY)

    from pptx.util import Inches, Pt

    # Lead paragraph. This field existed in the spec and in the Marp emitter
    # but was read NOWHERE here, so a content slide's opening paragraph was
    # silently dropped from the PowerPoint while showing in the Marp deck.
    y = 2.05
    body = (data.get("body") or "").strip()
    if body:
        lines = max(1, len(body) // 95 + 1)
        h = 0.34 * lines + 0.1
        _add_text(slide, 0.7, y, 11.9, h, body,
                  font_size=20, color=COL_TEXT_DARK, font=FONT_BODY)
        y += h + 0.25

    bullets = data.get("bullets") or []
    if bullets:
        # Bullets start under the body when there is one, and the block is
        # bounded by the callout band at 6.4 so the two cannot collide.
        avail = max(1.2, (6.25 if data.get("callout") else 7.0) - y)
        tx = slide.shapes.add_textbox(Inches(0.85), Inches(y),
                                       Inches(11.6), Inches(avail))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = 0
        # Tighten spacing when the slide is carrying a body paragraph too.
        gap = 16 if not body else 10
        size = 22 if len(bullets) <= 4 else 19
        # Where the bullet block ends, so the callout can follow the content
        # instead of being pinned to the slide floor. Marp flows the callout
        # straight after the text and lets the slack fall BELOW it; pinning
        # put all the slack above, which is what made the two look unrelated.
        #
        # Estimate honestly: PowerPoint's line box is about 1.25x the point
        # size, and a long bullet wraps. A first version used size+gap and no
        # wrapping, underestimated by ~0.4in, and dropped the callout on top
        # of the final bullet.
        chars_per_line = int(11.6 * 72 / (size * 0.55))
        wrapped = sum(max(1, (len(b) // chars_per_line) + 1) for b in bullets)
        y += (wrapped * size * 1.25 + len(bullets) * gap) / 72.0 + 0.3
        for i, b in enumerate(bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(gap)
            dot = p.add_run()
            dot.text = "•  "
            dot.font.name = FONT_BODY
            dot.font.size = Pt(size)
            # Green markers, as in the Marp theme's `ul li::marker`.
            dot.font.color.rgb = _hex(COL_ACCENT_BLUE)
            r = p.add_run()
            r.text = b
            r.font.name = FONT_BODY
            r.font.size = Pt(size)
            r.font.color.rgb = _hex(COL_TEXT_DARK)

    if data.get("callout"):
        cy = min(6.4, max(2.6, y))
        co = _add_rounded_rect(slide, 0.7, cy, 11.9, 0.8, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, cy + 0.15, 11.4, 0.5,
                  data["callout"], font_size=14, color="ffffff",
                  bold=True, valign="middle")

    if data.get("cite"):
        _add_text(slide, 0.7, 7.22, 11.9, 0.25, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_kpi(slide, data):
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.4,
              data.get("title", ""),
              font_size=40, bold=True, color=COL_TEXT_DARK,
              font=FONT_DISPLAY)

    kpis = data.get("kpis") or []
    n = max(1, min(4, len(kpis)))
    total_w, gap = 11.9, 0.25
    tile_w = (total_w - gap * (n - 1)) / n
    base_x, base_y = 0.7, 2.9
    tile_h = 2.8
    # ONE ACCENT. design.md: "Never rotate colours merely to make
    # neighbouring cards look different." A single entry means the
    # modulo index below always returns the accent.
    accent_cycle = [COL_ACCENT_BLUE]
    for i, k in enumerate(kpis[:n]):
        x = base_x + i * (tile_w + gap)
        accent = accent_cycle[i % len(accent_cycle)]
        # Single unified card: stripe + body as one rounded rect
        _add_capped_card(slide, x, base_y, tile_w, tile_h, accent,
                          stripe_side="top", stripe_in=0.14)
        # Giant value
        _add_text(slide, x + 0.25, base_y + 0.32, tile_w - 0.5, 1.55,
                  k.get("value", ""), font_size=76, bold=True,
                  color=accent, font=FONT_DISPLAY)
        # Label
        _add_text(slide, x + 0.25, base_y + 1.95, tile_w - 0.5, 0.8,
                  k.get("label", ""), font_size=14,
                  color=COL_TEXT_DARK, font=FONT_BODY)

    if data.get("callout"):
        co = _add_rounded_rect(slide, 0.7, 6.05, 11.9, 1.0, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, 6.2, 11.4, 0.7,
                  data["callout"], font_size=14, color="ffffff", bold=True,
                  valign="middle")

    if data.get("cite"):
        _add_text(slide, 0.7, 7.22, 11.9, 0.25, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_quote(slide, data):
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    # Giant decorative quote mark in faint accent
    _add_text(slide, 0.4, 0.4, 3.5, 3.5, "“",
              font_size=260, bold=True, color=COL_ACCENT_BLUE,
              font=FONT_DISPLAY, valign="top")

    # Vertical accent bar
    _add_filled_rect(slide, 0.7, 2.7, 0.08, 3.0, COL_ACCENT_BLUE)

    # Quote text (no surrounding quotes — giant " carries the visual)
    _add_text(slide, 1.0, 2.7, 11.6, 3.0,
              data.get("quote", ""),
              font_size=36, bold=True, color=COL_TEXT_DARK,
              font=FONT_DISPLAY, valign="middle")

    if data.get("attribution"):
        _add_text(slide, 1.0, 5.9, 11.6, 0.5,
                  data["attribution"], font_size=18,
                  color=COL_GREY3, font=FONT_BODY)

    if data.get("cite"):
        _add_text(slide, 0.7, 7.22, 11.9, 0.25, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_versus(slide, data):
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.4,
              data.get("title", ""), font_size=40, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)

    left = data.get("old") or {}
    right = data.get("new") or {}
    panel_y, panel_h = 2.9, 3.5
    left_x, left_w = 0.7, 5.6
    right_x, right_w = 7.05, 5.6

    # Left panel — muted with subtle shadow
    lp = _add_rounded_rect(slide, left_x, panel_y, left_w, panel_h,
                            COL_PANEL_GREY,
                            stroke_hex=COL_CARD_BORDER, stroke_pt=1.0)
    _add_shadow(lp, blur_pt=8, dist_pt=2, alpha_pct=10)

    _add_text(slide, left_x + 0.35, panel_y + 0.3, left_w - 0.7, 0.5,
              left.get("title", "Then"), font_size=22, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)
    if left.get("desc"):
        _add_text(slide, left_x + 0.35, panel_y + 0.85, left_w - 0.7, 0.6,
                  left["desc"], font_size=14, color=COL_GREY3,
                  font=FONT_BODY)
    bullets_left = left.get("bullets") or []
    if bullets_left:
        from pptx.util import Inches, Pt
        tx = slide.shapes.add_textbox(Inches(left_x + 0.35),
                                       Inches(panel_y + 1.55),
                                       Inches(left_w - 0.7), Inches(1.8))
        tf = tx.text_frame
        tf.word_wrap = True
        for i, b in enumerate(bullets_left):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(8)
            r = p.add_run()
            r.text = "•  " + b
            r.font.name = FONT_BODY
            r.font.size = Pt(15)
            r.font.color.rgb = _hex(COL_GREY3)

    # Right panel — accent with stronger shadow (the "winner")
    rp = _add_rounded_rect(slide, right_x, panel_y, right_w, panel_h,
                            "ffffff",
                            stroke_hex=COL_ACCENT_BLUE, stroke_pt=3.0)
    _add_shadow(rp, blur_pt=14, dist_pt=4, alpha_pct=20)

    _add_text(slide, right_x + 0.35, panel_y + 0.3, right_w - 0.7, 0.5,
              right.get("title", "Now"), font_size=22, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)
    if right.get("desc"):
        _add_text(slide, right_x + 0.35, panel_y + 0.85, right_w - 0.7, 0.6,
                  right["desc"], font_size=14, color=COL_GREY3,
                  font=FONT_BODY)
    bullets_right = right.get("bullets") or []
    if bullets_right:
        from pptx.util import Inches, Pt
        tx = slide.shapes.add_textbox(Inches(right_x + 0.35),
                                       Inches(panel_y + 1.55),
                                       Inches(right_w - 0.7), Inches(1.8))
        tf = tx.text_frame
        tf.word_wrap = True
        for i, b in enumerate(bullets_right):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(8)
            r = p.add_run()
            r.text = "•  " + b
            r.font.name = FONT_BODY
            r.font.size = Pt(15)
            r.font.color.rgb = _hex(COL_TEXT_DARK)

    # Clean right-arrow between panels — no circle, no shadow, no
    # text-character hack. Just a single MSO_SHAPE.RIGHT_ARROW in
    # saber-blue, centred in the gap between the two panels.
    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE
    arrow_w = 0.6
    arrow_h = 0.34
    # Gap between panels: left_x + left_w (=6.3) -> right_x (=7.05) = 0.75
    arrow_x = (left_x + left_w + right_x - arrow_w) / 2
    arrow_y = panel_y + panel_h / 2 - arrow_h / 2
    arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,
                                    Inches(arrow_x), Inches(arrow_y),
                                    Inches(arrow_w), Inches(arrow_h))
    _set_solid_fill(arrow, COL_ACCENT_BLUE)
    arrow.line.fill.background()

    if data.get("callout"):
        co = _add_rounded_rect(slide, 0.7, 6.55, 11.9, 0.7, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, 6.65, 11.4, 0.5,
                  data["callout"], font_size=14, color="ffffff", bold=True,
                  valign="middle")

    if data.get("cite"):
        _add_text(slide, 0.7, 7.27, 11.9, 0.2, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_cards(slide, data):
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.4,
              data.get("title", ""), font_size=40, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)

    cards = data.get("cards") or []
    n = max(1, min(4, len(cards)))
    total_w, gap = 11.9, 0.25
    card_w = (total_w - gap * (n - 1)) / n
    # Geometry from the Marp `.cards` rule at 96px per inch: 4px top border,
    # ~20px padding, and a card that HUGS its content. The old 3.55in box left
    # the text floating in the top third with dead space beneath it.
    base_x, base_y, card_h = 0.7, 2.85, 1.85
    # ONE ACCENT. design.md: "Never rotate colours merely to make
    # neighbouring cards look different." A single entry means the
    # modulo index below always returns the accent.
    accent_cycle = [COL_ACCENT_BLUE]
    for i, c in enumerate(cards[:n]):
        x = base_x + i * (card_w + gap)
        accent = accent_cycle[i % len(accent_cycle)]
        # Single unified card: stripe + body as one rounded rect
        _add_capped_card(slide, x, base_y, card_w, card_h, accent,
                          stripe_side="top", stripe_in=0.05)
        pad = 0.21
        ty = base_y + pad + 0.04
        icon = c.get("icon")
        if icon:
            _add_icon(slide, icon, x + pad, ty, size_in=0.4,
                      accent_hex=accent)
            ty += 0.5
        # Small tracked label, as in `.cards .num` (13px / 800 / accent),
        # sitting directly above the title rather than a third of a card away.
        if c.get("num"):
            _add_text(slide, x + pad, ty, card_w - 2 * pad, 0.26,
                      str(c["num"]).upper(), font_size=11, bold=True,
                      color=accent, font=FONT_MONO)
            ty += 0.26
        _add_text(slide, x + pad, ty, card_w - 2 * pad, 0.34,
                  c.get("title", ""), font_size=16, bold=True,
                  color=COL_TEXT_DARK, font=FONT_DISPLAY)
        ty += 0.36
        if c.get("desc"):
            _add_text(slide, x + pad, ty, card_w - 2 * pad,
                      base_y + card_h - ty - pad + 0.1,
                      c["desc"], font_size=12.5, color=COL_GREY3,
                      font=FONT_BODY)

    if data.get("callout"):
        cy = min(6.5, base_y + card_h + 0.3)
        co = _add_rounded_rect(slide, 0.7, cy, 11.9, 0.72, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, cy + 0.11, 11.4, 0.5,
                  data["callout"], font_size=14, color="ffffff", bold=True,
                  valign="middle")

    if data.get("cite"):
        _add_text(slide, 0.7, 7.27, 11.9, 0.2, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_six_up(slide, data):
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.0,
              data.get("title", ""), font_size=34, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)

    items = data.get("items") or []
    n = max(1, min(6, len(items)))
    cols, rows = 3, 2
    gap = 0.2
    total_w = 11.9
    card_w = (total_w - gap * (cols - 1)) / cols
    # Two rows at 2.05 end at 6.60, which leaves no room for a callout band
    # before the citation line at 7.27. Shrink the cards when there is one.
    has_callout = bool(data.get("callout"))
    card_h = 1.85 if has_callout else 2.05
    base_x, base_y = 0.7, 2.3
    # ONE ACCENT. design.md: "Never rotate colours merely to make
    # neighbouring cards look different." A single entry means the
    # modulo index below always returns the accent.
    accent_cycle = [COL_ACCENT_BLUE]
    for i, it in enumerate(items[:n]):
        row, col = divmod(i, cols)
        x = base_x + col * (card_w + gap)
        y = base_y + row * (card_h + gap)
        accent = accent_cycle[i % len(accent_cycle)]
        # Single unified card with left accent stripe (0.10 wide so it
        # fully covers the rounded left corners on the 2.05-tall card)
        _add_capped_card(slide, x, y, card_w, card_h, accent,
                          stripe_side="left", stripe_in=0.10,
                          shadow_blur=10, shadow_dist=3, shadow_alpha=10)
        # Optional icon at top-left; if present, push num to its right.
        # Icon colour matches the cell's accent so the row reads as a
        # cohesive colour block.
        icon = it.get("icon")
        if icon:
            _add_icon(slide, icon, x + 0.28, y + 0.18, size_in=0.42,
                      accent_hex=accent)
            num_x = x + 0.78
        else:
            num_x = x + 0.3
        if it.get("num"):
            _add_text(slide, num_x, y + 0.22, card_w - (num_x - x) - 0.2, 0.3,
                      str(it["num"]).upper(), font_size=12, bold=True,
                      color=accent, font=FONT_MONO)
        _add_text(slide, x + 0.3, y + 0.7, card_w - 0.5, 0.6,
                  it.get("title", ""), font_size=16, bold=True,
                  color=COL_TEXT_DARK, font=FONT_DISPLAY)
        if it.get("desc"):
            _add_text(slide, x + 0.3, y + 1.25, card_w - 0.5, card_h - 1.35,
                      it["desc"], font_size=12, color=COL_GREY3,
                      font=FONT_BODY)

    # six-up was the only content renderer without callout support, so a spec
    # carrying one silently lost it in the pptx while the Marp deck showed it.
    if has_callout:
        co = _add_rounded_rect(slide, 0.7, 6.35, 11.9, 0.72, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, 6.46, 11.4, 0.5,
                  data["callout"], font_size=13, color="ffffff",
                  bold=True, valign="middle")

    if data.get("cite"):
        _add_text(slide, 0.7, 7.27, 11.9, 0.2, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def _png_white_to_transparent(png_bytes: bytes) -> bytes:
    """Convert white background pixels in a PNG to transparent.

    svglib + reportlab always renders with an opaque white canvas.
    This post-processes: any pixel where min(R,G,B) > 200 becomes
    proportionally transparent (pure white -> alpha 0; near-white
    anti-aliased fringe -> partial alpha). Returns the new PNG bytes."""
    from io import BytesIO
    from PIL import Image
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    new_pixels = []
    for r, g, b, a in img.getdata():
        whiteness = min(r, g, b)
        if whiteness > 200:
            new_alpha = max(0, int((255 - whiteness) / 55 * 255))
            new_pixels.append((r, g, b, new_alpha))
        else:
            new_pixels.append((r, g, b, a))
    img.putdata(new_pixels)
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _render_donut_to_bytes(percent: float, accent_hex: str,
                             stroke_w: int = 13,
                             size_px: int = 480):
    """Render a single donut ring (no centre text) as PNG bytes.

    percent: 0-100, accent_hex: filled portion colour (with or without
    leading '#'). The unfilled portion is a very faint same-accent
    ghost ring (opacity 0.15). The white canvas background is
    post-processed to transparent so the donut sits cleanly on the
    cream slide. Returns BytesIO ready for add_picture()."""
    import math
    from io import BytesIO
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM

    r = 42
    circumference = 2 * math.pi * r
    filled_len = circumference * max(0, min(100, percent)) / 100
    accent = "#" + accent_hex.lstrip("#")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<circle cx="50" cy="50" r="{r}" fill="none" stroke="{accent}" '
        f'stroke-width="{stroke_w}" stroke-opacity="0.15"/>'
        f'<circle cx="50" cy="50" r="{r}" fill="none" stroke="{accent}" '
        f'stroke-width="{stroke_w}" stroke-linecap="round" '
        f'stroke-dasharray="{filled_len:.2f} {circumference:.2f}" '
        f'transform="rotate(-90 50 50)"/>'
        f'</svg>'
    )
    drawing = svg2rlg(BytesIO(svg.encode("utf-8")))
    scale = size_px / drawing.width
    drawing.scale(scale, scale)
    drawing.width *= scale
    drawing.height *= scale
    png = renderPM.drawToString(drawing, fmt="PNG")
    return BytesIO(_png_white_to_transparent(png))


def render_donut_kpi(slide, data):
    """1-3 donut charts showing percentage stats. Big % text overlaid
    inside each ring + a label below. Use for percent-only KPIs (for
    raw counts / multipliers / $-values, use the regular `kpi` type)."""
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.4,
              data.get("title", ""), font_size=40, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)

    kpis = data.get("kpis") or []
    n = max(1, min(3, len(kpis)))
    donut_size = 2.8
    label_h = 0.9
    total_w = n * donut_size + (n - 1) * 0.4
    base_x = (13.333 - total_w) / 2
    base_y = 2.85
    # ONE ACCENT. design.md: "Never rotate colours merely to make
    # neighbouring cards look different." A single entry means the
    # modulo index below always returns the accent.
    accent_cycle = [COL_ACCENT_BLUE]

    from pptx.util import Inches

    for i, kpi in enumerate(kpis[:n]):
        x = base_x + i * (donut_size + 0.4)
        accent = accent_cycle[i % len(accent_cycle)]
        value_str = str(kpi.get("value", "")).strip()
        # Parse percent from value string (e.g. "75%" -> 75.0)
        try:
            percent = float(value_str.rstrip("%").replace(",", "").strip())
        except ValueError:
            percent = 100  # fallback: show full ring
        png = _render_donut_to_bytes(percent, accent)
        slide.shapes.add_picture(png, Inches(x), Inches(base_y),
                                  Inches(donut_size), Inches(donut_size))
        # Big % text centred inside the donut
        _add_text(slide, x, base_y + donut_size / 2 - 0.65,
                  donut_size, 1.3,
                  value_str, font_size=64, bold=True, color=accent,
                  font=FONT_DISPLAY, align="center", valign="middle")
        # Label below donut
        _add_text(slide, x - 0.2, base_y + donut_size + 0.12,
                  donut_size + 0.4, label_h,
                  kpi.get("label", ""), font_size=13,
                  color=COL_TEXT_DARK, font=FONT_BODY, align="center")

    if data.get("callout"):
        co = _add_rounded_rect(slide, 0.7, 6.55, 11.9, 0.7, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, 6.65, 11.4, 0.5,
                  data["callout"], font_size=14, color="ffffff", bold=True,
                  valign="middle")
    if data.get("cite"):
        _add_text(slide, 0.7, 7.27, 11.9, 0.2, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_timeline(slide, data):
    """Horizontal milestone strip — saber-blue track with N coloured
    nodes, each labelled and backed by a content card below.

    Each milestone: `label` (small accent kicker — e.g. "DAY 30"),
    `title` (bold accent headline inside the card), `desc` (1-3 line
    description in the card)."""
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.0,
              data.get("title", ""), font_size=36, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)

    milestones = data.get("milestones") or []
    n = max(2, min(6, len(milestones)))

    # Wider margin so first/last labels stay on-slide. item_w is
    # capped at 2*margin so a centred label never overflows.
    margin = 1.4
    total_w = 13.333 - 2 * margin
    line_y = 3.65
    # ONE ACCENT. design.md: "Never rotate colours merely to make
    # neighbouring cards look different." A single entry means the
    # modulo index below always returns the accent.
    accent_cycle = [COL_ACCENT_BLUE]

    # Track — saber-blue tinted bar (more brand-on than grey hairline)
    from pptx.util import Inches, Pt
    from pptx.enum.shapes import MSO_SHAPE
    track_thick = 0.10
    track = _add_filled_rect(slide, margin, line_y - track_thick / 2,
                              total_w, track_thick, COL_ACCENT_BLUE)
    _set_fill_opacity(track, 22)

    if n == 1:
        positions = [margin + total_w / 2]
    else:
        positions = [margin + i * total_w / (n - 1) for i in range(n)]

    item_w = min(2 * margin - 0.15, (total_w / n) * 0.95)

    card_y = line_y + 0.6
    card_h = 1.9

    for i, m in enumerate(milestones[:n]):
        cx = positions[i]
        accent = accent_cycle[i % len(accent_cycle)]

        # Above line: just the small kicker label (DAY 0 / DAY 30 / ...)
        if m.get("label"):
            _add_text(slide, cx - item_w / 2, line_y - 0.65,
                      item_w, 0.35,
                      m["label"], font_size=13, bold=True, color=accent,
                      font=FONT_MONO, align="center")

        # Node on line — large filled circle + shadow, with a small
        # white centre dot for an "anchor" feel
        node_d = 0.55
        node = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                       Inches(cx - node_d / 2),
                                       Inches(line_y - node_d / 2),
                                       Inches(node_d), Inches(node_d))
        _set_solid_fill(node, accent)
        _add_shadow(node, blur_pt=10, dist_pt=3, alpha_pct=24)
        inner_d = 0.18
        inner = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                        Inches(cx - inner_d / 2),
                                        Inches(line_y - inner_d / 2),
                                        Inches(inner_d), Inches(inner_d))
        _set_solid_fill(inner, "ffffff")
        inner.line.fill.background()

        # Below line: content card holding title + desc
        card_x = cx - item_w / 2
        _add_capped_card(slide, card_x, card_y, item_w, card_h, accent,
                          stripe_side="top", stripe_in=0.08,
                          shadow_blur=8, shadow_dist=2, shadow_alpha=10)
        if m.get("title"):
            _add_text(slide, card_x + 0.2, card_y + 0.22,
                      item_w - 0.4, 0.5,
                      m["title"], font_size=17, bold=True,
                      color=COL_TEXT_DARK, font=FONT_DISPLAY)
        if m.get("desc"):
            _add_text(slide, card_x + 0.2, card_y + 0.78,
                      item_w - 0.4, card_h - 0.95,
                      m["desc"], font_size=12, color=COL_GREY3,
                      font=FONT_BODY)

    if data.get("callout"):
        co = _add_rounded_rect(slide, 0.7, 6.7, 11.9, 0.65, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, 6.78, 11.4, 0.5,
                  data["callout"], font_size=14, color="ffffff", bold=True,
                  valign="middle")
    if data.get("cite"):
        _add_text(slide, 0.7, 7.27, 11.9, 0.2, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_hub(slide, data):
    """Hub-and-spokes: central concept (hub) with 3-6 radial spokes.

    Each spoke is a connector line from the hub edge to an endpoint
    dot, with a title + description beyond the dot. Use when items are
    the constituent PARTS of a single named thing (Four C's of AIOS,
    Four pillars of X, etc.) — distinct from `cards` which is for
    parallel siblings without a unifying parent.

    Data: `hub` (short string for the centre, e.g. "AIOS"), `spokes`
    (list of {title, desc}). Spokes arrange clockwise from 12 o'clock."""
    import math
    from pptx.util import Inches, Pt
    from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR

    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.0,
              data.get("title", ""), font_size=36, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)

    spokes = data.get("spokes") or []
    n = max(3, min(6, len(spokes)))

    cx, cy = 13.333 / 2, 4.4
    hub_r = 0.95
    line_inner = hub_r + 0.05
    line_outer = 2.0
    label_w = 3.4
    label_h = 1.5

    # ONE ACCENT. design.md: "Never rotate colours merely to make
    # neighbouring cards look different." A single entry means the
    # modulo index below always returns the accent.
    accent_cycle = [COL_ACCENT_BLUE]

    # Hub — outline-only ring with no fill. The slide background
    # shows through inside the ring; spokes terminate at the visible
    # outline. Lightest possible centre, so the coloured spokes get
    # full visual focus.
    hub = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                  Inches(cx - hub_r), Inches(cy - hub_r),
                                  Inches(hub_r * 2), Inches(hub_r * 2))
    hub.fill.background()
    hub.line.color.rgb = _hex(COL_ACCENT_BLUE)
    hub.line.width = Pt(3)
    _add_text(slide, cx - hub_r, cy - 0.5, hub_r * 2, 1.0,
              data.get("hub", ""), font_size=26, bold=True,
              color=COL_TEXT_DARK,
              font=FONT_DISPLAY, align="center", valign="middle")

    # For 4-spoke layouts, use diagonals (NE/SE/SW/NW) — the cardinal
    # layout (N/E/S/W) crams top/bottom labels into title + callout
    # bands. For other counts, start at 12 o'clock.
    start_angle = -45 if n == 4 else -90
    angle_step = 360.0 / n

    for i, spoke in enumerate(spokes[:n]):
        angle_deg = start_angle + i * angle_step
        angle_rad = math.radians(angle_deg)
        accent = accent_cycle[i % len(accent_cycle)]
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Spoke line: hub edge -> endpoint
        x1 = cx + line_inner * cos_a
        y1 = cy + line_inner * sin_a
        x2 = cx + line_outer * cos_a
        y2 = cy + line_outer * sin_a
        line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                           Inches(x1), Inches(y1),
                                           Inches(x2), Inches(y2))
        line.line.color.rgb = _hex(accent)
        line.line.width = Pt(2.5)

        # Endpoint dot
        dot_d = 0.26
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                                      Inches(x2 - dot_d / 2),
                                      Inches(y2 - dot_d / 2),
                                      Inches(dot_d), Inches(dot_d))
        _set_solid_fill(dot, accent)
        _add_shadow(dot, blur_pt=6, dist_pt=2, alpha_pct=20)
        dot.line.fill.background()

        # Label placement — beyond the endpoint, aligned by quadrant
        if cos_a > 0.15:        # right side
            label_x = x2 + 0.3
            align = "left"
        elif cos_a < -0.15:     # left side
            label_x = x2 - label_w - 0.3
            align = "right"
        else:                   # top or bottom (only when n != 4)
            label_x = x2 - label_w / 2
            align = "center"

        # Vertical position: centre label on the endpoint when it's a
        # side spoke; nudge above/below for pure top/bottom spokes.
        if sin_a > 0.7:         # nearly straight down
            label_y = y2 + 0.2
        elif sin_a < -0.7:      # nearly straight up
            label_y = y2 - label_h - 0.2
        else:
            label_y = y2 - label_h / 2

        # Constrain to slide bounds (title ends ~y=2.05; cite at y=7.3)
        label_x = max(0.2, min(13.333 - label_w - 0.2, label_x))
        label_y = max(2.1, min(7.05 - label_h, label_y))

        # Title (bold, dark)
        _add_text(slide, label_x, label_y, label_w, 0.55,
                  spoke.get("title", ""), font_size=18, bold=True,
                  color=COL_TEXT_DARK, font=FONT_DISPLAY, align=align)
        # Desc (regular, muted) — gets the rest of the label height
        if spoke.get("desc"):
            _add_text(slide, label_x, label_y + 0.6, label_w,
                      label_h - 0.6,
                      spoke["desc"], font_size=13, color=COL_GREY3,
                      font=FONT_BODY, align=align)

    # Callout goes into slide notes for hub layouts — no room on the
    # slide once spokes are placed without overlapping the labels.
    notes = []
    if data.get("callout"):
        notes.append(data["callout"])
    if notes:
        slide.notes_slide.notes_text_frame.text = "\n\n".join(notes)

    if data.get("cite"):
        _add_text(slide, 0.7, 7.27, 11.9, 0.2, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


def render_flow(slide, data):
    """Horizontal flow chart: 3-5 nodes connected by arrows. Each node
    is a rounded card with an optional icon + step number + title +
    short description, centred. Use for sequential processes where the
    order matters (pipeline, onboarding, playbook, etc.)."""
    _slide_gradient_background(slide, [
        (0,       COL_BG_CREAM_HI),
        (100000,  COL_BG_CREAM_LO),
    ], angle_deg=135)
    _add_brand_mark(slide)

    eyebrow = (data.get("eyebrow") or "").strip()
    if eyebrow:
        _add_text(slide, 0.7, 0.55, 12, 0.32,
                  eyebrow.upper(), font_size=11, bold=True,
                  color=COL_ACCENT_BLUE, font=FONT_MONO)

    _add_text(slide, 0.7, 1.05, 12, 1.4,
              data.get("title", ""), font_size=40, bold=True,
              color=COL_TEXT_DARK, font=FONT_DISPLAY)

    steps = data.get("steps") or []
    n = max(2, min(5, len(steps)))
    margin = 0.7
    # The Marp `.steps` grid is a plain 14px gap with NO arrows: the numerals
    # carry the sequence. Arrows here were an extra ornament the other
    # renderer never had, and they forced the cards narrower.
    arrow_w = 0.15
    total_w = 13.333 - 2 * margin
    node_w = (total_w - (n - 1) * arrow_w) / n
    # Geometry mirrors the Marp `.steps` rule, converted at 96px per inch:
    # 20px padding -> 0.21, 4px top border -> 0.042, and a card only as tall
    # as its content rather than a fixed 3.5in box with the text floating in
    # the middle of it.
    base_y = 2.8
    node_h = 2.15
    # ONE ACCENT. design.md: "Never rotate colours merely to make
    # neighbouring cards look different." A single entry means the
    # modulo index below always returns the accent.
    accent_cycle = [COL_ACCENT_BLUE]

    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE

    for i, step in enumerate(steps[:n]):
        x = margin + i * (node_w + arrow_w)
        accent = accent_cycle[i % len(accent_cycle)]

        _add_capped_card(slide, x, base_y, node_w, node_h, accent,
                          stripe_side="top", stripe_in=0.05)

        pad = 0.21
        ty = base_y + pad + 0.05
        if step.get("icon"):
            _add_icon(slide, step["icon"], x + pad, ty,
                      size_in=0.42, accent_hex=accent)
            ty += 0.52

        # The step number is a LARGE ACCENT NUMERAL, matching `.steps .num`
        # (26px / weight 800 / accent). It was a filled pill, which read as a
        # button and was the loudest difference between the two renderers.
        if step.get("num"):
            _add_text(slide, x + pad, ty, node_w - 2 * pad, 0.34,
                      str(step["num"]), font_size=19, bold=True,
                      color=accent, font=FONT_DISPLAY)
            ty += 0.34

        # Left-aligned, packed from the top of the card. Centring is what made
        # the cards read as posters rather than as the Marp step tiles.
        _add_text(slide, x + pad, ty, node_w - 2 * pad, 0.3,
                  step.get("title", ""), font_size=14, bold=True,
                  color=COL_TEXT_DARK, font=FONT_DISPLAY)
        ty += 0.32

        if step.get("desc"):
            _add_text(slide, x + pad, ty, node_w - 2 * pad,
                      base_y + node_h - ty - pad, step["desc"],
                      font_size=12, color=COL_GREY3, font=FONT_BODY)

    # Callout follows the cards rather than sitting at the slide floor, so the
    # slack falls below it as it does in the Marp flow layout.
    if data.get("callout"):
        cy = min(6.55, base_y + node_h + 0.3)
        co = _add_rounded_rect(slide, 0.7, cy, 11.9, 0.72, COL_PANEL_DARK)
        _add_shadow(co, blur_pt=10, dist_pt=3, alpha_pct=25)
        _add_text(slide, 0.95, cy + 0.11, 11.4, 0.5,
                  data["callout"], font_size=14, color="ffffff", bold=True,
                  valign="middle")

    if data.get("cite"):
        _add_text(slide, 0.7, 7.27, 11.9, 0.2, data["cite"],
                  font_size=10, color=COL_TEXT_FAINT, font=FONT_MONO)


SLIDE_RENDERERS = {
    "cover":      render_cover,
    "lead":       render_lead,
    "section":    render_section,
    "content":    render_content,
    "kpi":        render_kpi,
    "donut-kpi":  render_donut_kpi,
    "quote":      render_quote,
    "versus":     render_versus,
    "cards":      render_cards,
    "six-up":     render_six_up,
    "flow":       render_flow,
    "timeline":   render_timeline,
    "hub":        render_hub,
}


def build_pptx(deck: dict, out_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    prs.slide_width = Inches(13.333)   # 16:9 widescreen
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    for spec in deck.get("slides") or []:
        kind = spec.get("type") or "content"
        renderer = SLIDE_RENDERERS.get(kind, render_content)
        slide = prs.slides.add_slide(blank_layout)
        try:
            renderer(slide, spec)
        except Exception as exc:
            sys.stderr.write(f"warning: failed to render {kind} slide: {exc}\n")
            render_content(slide, {"title": spec.get("title", kind),
                                   "bullets": [str(spec)[:200]]})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))


# === Main ===

def _apply_design(design_path: str | None) -> None:
    """Load a design.md and reassign the renderer's module-level
    palette + font constants. Silent no-op if path is missing or
    the file fails to parse — the renderer's default Riverfed
    palette stays in place."""
    if not design_path:
        return
    p = Path(design_path)
    if not p.exists():
        print(f"[studio_pptx] warning: design file not found: {p}",
              file=sys.stderr)
        return
    # design_tokens lives next to this script
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from design_tokens import load_design
    except Exception as exc:
        print(f"[studio_pptx] warning: design_tokens import failed: {exc}",
              file=sys.stderr)
        return
    try:
        d = load_design(p)
    except Exception as exc:
        print(f"[studio_pptx] warning: failed to load {p}: {exc}",
              file=sys.stderr)
        return

    g = globals()
    color_map = {
        "primary":             "COL_ACCENT_BLUE",
        "secondary":           "COL_NEURAL",
        "success":             "COL_GREEN",
        "highlight":           "COL_YELLOW",
        "warning":             "COL_FIBRE" if "COL_FIBRE" in g else None,
        "error":               "COL_UNITED" if "COL_UNITED" in g else None,
        "background":          "COL_BG_DARK",
        "background-elevated": "COL_PANEL_DARK",
        "surface":             "COL_BG_CREAM",
        "surface-cream":       "COL_BG_CREAM_LO",
        "foundation":          "COL_TEXT_DARK",
        "text-muted":          "COL_TEXT_MUTED",
        "text-faint":          "COL_TEXT_FAINT",
    }
    for design_key, const_name in color_map.items():
        if not const_name:
            continue
        raw = d.colors.get(design_key)
        if raw:
            g[const_name] = str(raw).lstrip("#").lower()

    # Font overrides — design.md typography roles → our 3 font constants
    g["FONT_DISPLAY"] = d.font_family("h1", g.get("FONT_DISPLAY", "Inter"))
    g["FONT_BODY"]    = d.font_family("body-md", g.get("FONT_BODY", "Inter"))
    g["FONT_MONO"]    = d.font_family("eyebrow", g.get("FONT_MONO", "JetBrains Mono"))

    print(f"[studio_pptx] applied design: {d.name} "
          f"(primary=#{d.color('primary')}, font={g['FONT_DISPLAY']})",
          file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--slides", type=int, default=14)
    ap.add_argument("--audience", default="Operators who already use AI agents")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--design", default=None,
                    help="Optional design.md path (overrides palette + fonts).")
    ap.add_argument("--provider", default="auto",
                    help=agent_runner.provider_arg_help(
                        "run this generation on"))
    args = ap.parse_args()

    _apply_design(args.design)

    slug = slugify(args.prompt)
    out_dir = ROOT / args.out_dir
    out_json = out_dir / f"{slug}.pptx.json"
    out_pptx = out_dir / f"{slug}.pptx"

    deck = get_claude_json(args.wiki, args.prompt, args.slides,
                           args.audience, out_json,
                           provider_arg=args.provider)
    if deck is None:
        return 2

    print(f"[studio_pptx] rendering {len(deck.get('slides') or [])} slides…",
          file=sys.stderr)
    # Build to a sibling .tmp.pptx, then atomically swap onto the canonical
    # path. If PowerPoint has the canonical file open (exclusive lock on
    # Windows), the swap raises PermissionError — keep the .tmp.pptx so the
    # new build is still available, and report that path. Mirrors
    # wiki/training/scripts/build_handbook_pptx.py.
    tmp_pptx = out_pptx.with_suffix(".tmp.pptx")
    try:
        build_pptx(deck, tmp_pptx)
    except Exception as exc:
        print(f"Error: python-pptx render failed: {exc}", file=sys.stderr)
        return 3

    final_path = out_pptx
    try:
        tmp_pptx.replace(out_pptx)
    except PermissionError:
        final_path = tmp_pptx
        print(f"warning: {out_pptx.relative_to(ROOT).as_posix()} is locked "
              "(close PowerPoint to swap). New build available at "
              f"{tmp_pptx.relative_to(ROOT).as_posix()}", file=sys.stderr)

    print(final_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
