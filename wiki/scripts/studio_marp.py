#!/usr/bin/env python3
"""Studio: generate a Marp slide deck from a wiki + a short user prompt.

Reads the wiki content, applies the design system in
wiki/training/design.md, and asks Claude Code (headless mode) to
synthesize a deck. Outputs the Marp markdown source to
wiki/training/studio/<slug>.md.

Usage (from repo root):
    py -3.13 wiki/scripts/studio_marp.py \\
        --wiki wiki \\
        --prompt "How operators use Claude Code in marketing" \\
        --slides 14 \\
        --audience "Builders who already know what an agent is"
"""
from __future__ import annotations
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

# The provider layer, imported at module level because the
# --provider help text is built from it during argparse setup.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_runner  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DESIGN_MD_REL = "wiki/training/design.md"
EXAMPLE_DECK_REL = "wiki/training/ai-builders-handbook.md"
THEME_REL = "wiki/training/themes/ai-builders.css"

# Render targets the studio emits alongside the .md source. Each
# format takes 3-15 sec via the marp CLI. The .md is always emitted
# (Claude writes it directly); HTML/PDF/PPTX are best-effort —
# missing marp / failed render = .md-only deck, no hard failure.
RENDER_FORMATS = ("html", "pdf", "pptx")


def resolve_marp_bin() -> tuple[list[str] | None, str]:
    """Return ([executable, ...args], description). On Windows the
    CLI ships as `marp.CMD` (via npm), so we use shutil.which to walk
    PATHEXT. Falls back to `npx @marp-team/marp-cli@latest` if marp
    isn't installed globally — slower (npx may download on first run)
    but works without a manual install."""
    direct = shutil.which("marp")
    if direct:
        return [direct], f"marp ({direct})"
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "@marp-team/marp-cli@latest"], \
               f"npx @marp-team/marp-cli (via {npx})"
    return None, ""


def _safe_rel(p: Path, root: Path) -> str:
    """Render a path relative to ROOT for display, falling back to
    absolute if it's outside the tree (e.g. when called from a test
    with a non-resolved cwd)."""
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return p.as_posix()


def _render_target(md_path: Path, fmt: str) -> Path:
    """Output path for a rendered format. PPTX gets a '-marp' suffix so it
    can never clobber studio_pptx.py's native editable <stem>.pptx — both
    generators produce the same slug when run with the same prompt, and a
    2026-07-13 run only escaped losing the editable deck because PowerPoint
    happened to hold a lock on it."""
    if fmt == "pptx":
        return md_path.with_name(f"{md_path.stem}-marp.pptx")
    return md_path.with_suffix(f".{fmt}")


def render_marp_outputs(md_path: Path, theme_path: Path) -> dict[str, Path]:
    """Render the .md to HTML / PDF / PPTX. Returns {fmt: Path} for
    every format that succeeded. Silent on missing marp; warns on
    per-format render failures so the user gets partial results."""
    md_path = md_path.resolve()
    theme_path = theme_path.resolve()
    base_cmd, marp_label = resolve_marp_bin()
    if not base_cmd:
        print("[studio_marp] marp CLI not found — emitted .md only. "
              "Install with `npm i -g @marp-team/marp-cli` to also "
              "render HTML/PDF/PPTX.", file=sys.stderr)
        return {}
    print(f"[studio_marp] rendering HTML / PDF / PPTX via {marp_label}…",
          file=sys.stderr)

    no_window = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
                 if sys.platform == "win32" else 0)
    rendered: dict[str, Path] = {}
    for fmt in RENDER_FORMATS:
        out_file = _render_target(md_path, fmt)
        cmd = list(base_cmd) + [
            "--allow-local-files", "--html",
            "--theme", str(theme_path),
            str(md_path),
            "-o", str(out_file),
        ]
        # run_streaming kills the whole process TREE on timeout. A plain
        # subprocess timeout only kills marp.CMD and orphans node/chromium —
        # one such zombie once lived 125 minutes and blocked later renders.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _proc import run_streaming
        try:
            rc, r_out, r_err, timed_out = run_streaming(
                cmd, cwd=str(ROOT), timeout=180, creationflags=no_window)
        except FileNotFoundError:
            print(f"[studio_marp] {fmt}: marp binary disappeared mid-run",
                  file=sys.stderr)
            continue
        if timed_out:
            print(f"[studio_marp] {fmt}: timed out after 3 minutes "
                  "(process tree killed)", file=sys.stderr)
            continue
        if rc != 0 or not out_file.exists():
            tail = [l for l in (r_err or r_out) if l.strip()][-2:]
            tail_str = " | ".join(tail) if tail else f"exit {rc}"
            print(f"[studio_marp] {fmt}: render failed — {tail_str}",
                  file=sys.stderr)
            continue
        rendered[fmt] = out_file
        print(f"[studio_marp] {fmt}: wrote {_safe_rel(out_file, ROOT)}",
              file=sys.stderr)
    return rendered


def slugify(s: str, max_len: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].rstrip("-") or "untitled-deck"


_FONT_STACK = '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = str(h).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _norm_hex(v: object) -> str | None:
    """Normalize a token value to a `#rrggbb` string, or None if empty / not
    a hex colour (e.g. an unresolved `{ref}` or a px dimension)."""
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s if s.startswith("#") else "#" + s
    return s if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", s) else None


def _is_vibrant(h: str) -> bool:
    """True if a hex colour is saturated and mid-lightness enough to read as
    an *accent* (vs a near-black / near-white / grey structural colour).

    Used to decide where a design's accent actually lives: the default puts it in
    `primary` (saber blue), but Heritage puts it in `highlight` (clay) and
    uses `primary` for near-black ink. Without this, the deck's accent
    (eyebrows, KPI numbers, card stripes, links) would render as dull ink."""
    try:
        r, g, b = (v / 255 for v in _hex_to_rgb(h))
    except Exception:
        return True
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    denom = 1 - abs(2 * light - 1)
    sat = 0.0 if mx == mn or denom == 0 else (mx - mn) / denom
    return sat >= 0.30 and 0.18 <= light <= 0.82


def _pick_accent(primary: str | None, highlight: str | None) -> str | None:
    """The deck's accent colour: `primary` when it's vibrant, else
    `highlight` (Heritage's primary is near-black ink; its accent is the
    clay highlight)."""
    return primary if (primary and _is_vibrant(primary)) else (highlight or primary)


def _design_accent(design_path: str) -> str | None:
    """Load a design and return its accent hex (same choice the theme
    override uses), or None. Used to recolour the embedded brand SVGs."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from design_tokens import load_design
        c = load_design(Path(design_path)).colors or {}
        return _pick_accent(_norm_hex(c.get("primary")), _norm_hex(c.get("highlight")))
    except Exception:
        return None


# Brand-blue palette baked into the bundled SVG icon + logo assets.
# Embedded as <img>, so CSS can't recolour them — when a design is applied
# we swap these for the design's accent and inline the SVGs into the deck.
_BRAND_BLUES = ("#4f8cff", "#4dbeff", "#2f6fe6", "#cae3ff")


# Default house per-card accent hexes — match the theme :root and the
# .is-neural / .is-circuit / … card modifiers. The card's number + top stripe
# already use these via CSS; the icon is an <img> SVG CSS can't reach, so we
# inline + recolour it to match at render time.
_CARD_ACCENTS_DEFAULT = {
    "neural":  "#7a59e2",
    "circuit": "#46c98b",
    "fibre":   "#ff6b35",
    "voltage": "#ffd93d",
    "united":  "#ff4d4d",
}
# design.md token that drives each card-accent class (mirrors _DESIGN_COLOR_MAP)
_DESIGN_TOKEN_FOR_CLASS = {
    "neural": "secondary", "circuit": "success",
    "fibre": "warning", "voltage": "highlight", "united": "error",
}


def _card_accent_palette(design_path: str | None) -> dict[str, str]:
    """Map each card-accent class to a hex. Defaults to the house palette;
    a design overrides via its tokens (so a Heritage/Aurora deck's card icons
    match that design's card stripes)."""
    pal = dict(_CARD_ACCENTS_DEFAULT)
    if not design_path:
        return pal
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from design_tokens import load_design
        c = load_design(Path(design_path)).colors or {}
    except Exception:
        return pal
    for cls, token in _DESIGN_TOKEN_FOR_CLASS.items():
        v = c.get(token)
        if v:
            h = str(v).strip()
            pal[cls] = h if h.startswith("#") else "#" + h
    return pal


def _inline_svg(src: str, md_dir: Path, target_hex: str,
                cache: dict) -> str | None:
    """Read a local .svg, recolour its brand-blue strokes/fills to target_hex,
    and return the inlined <svg> markup. None if not a readable local svg.

    Why inline: marp keeps `<img src="../assets/…">` as external paths in the
    rendered HTML, and CSS can't recolour an <img> — so to tint an icon we must
    inline the SVG and rewrite its hardcoded saber-blue."""
    key = (src, target_hex)
    if key in cache:
        return cache[key]
    out: str | None = None
    if not src.startswith(("http:", "https:", "data:")):
        p = (md_dir / src).resolve()
        if p.exists() and p.suffix.lower() == ".svg":
            try:
                svg = p.read_text(encoding="utf-8")
                # Strip the SVG's internal <style> block. The bundled icons
                # define a SHARED class (e.g. .MsftOfcThm_Text1_Stroke_v2) in a
                # <style>; once several icons are inlined into one HTML page
                # those styles are global and the last one's colour overrides
                # ALL icons using that class (CSS beats the inline `stroke`
                # attribute). Removing it makes each icon fall back to its own
                # inline stroke/fill — which we recolour below — so per-card
                # colours survive.
                svg = re.sub(r"<style\b[^>]*>.*?</style>", "", svg,
                             flags=re.IGNORECASE | re.DOTALL)
                for blue in _BRAND_BLUES:
                    svg = re.sub(re.escape(blue), target_hex, svg,
                                 flags=re.IGNORECASE)
                out = svg
            except OSError:
                out = None
    cache[key] = out
    return out


def _recolor_card_icons(text: str, md_dir: Path, palette: dict,
                        cache: dict) -> tuple[str, int]:
    """Inline + recolour each accent-card's icon SVG to that card's accent, so
    the icon matches the card's number + top stripe. Matches a card-opening div
    carrying an accent class (`is-neural`, `circuit`, …), then its first icon
    `<img *.svg>` — guarding (via lookahead) against crossing into the next
    accent card."""
    classes = "|".join(palette)
    pat = re.compile(
        r'(<div\b[^>]*\bclass="[^"]*\b(?:is-)?(' + classes + r')\b[^"]*"[^>]*>)'
        r'((?:(?!<div\b[^>]*\bclass="[^"]*(?:is-)?(?:' + classes + r')\b).)*?)'
        r'<img\b[^>]*?\bsrc="([^"]+\.svg)"[^>]*?/?>',
        re.IGNORECASE | re.DOTALL)

    def repl(m: "re.Match[str]") -> str:
        opener, cls, gap, src = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        svg = _inline_svg(src, md_dir, palette[cls], cache)
        return opener + gap + svg if svg is not None else m.group(0)

    return pat.subn(repl, text)


def _prepare_deck(deck_md: Path, card_palette: dict,
                  design_accent: str | None = None) -> str | None:
    """Prepare the deck for render. Returns the modified markdown, or None if
    nothing changed (caller renders the original).

    ALWAYS: inline + recolour each accent-card's icon to its own card accent,
    so the icon matches the card's number + top stripe (the long-standing
    mismatch — CSS colours the number/stripe but can't reach an <img> SVG).

    WITH A DESIGN: recolour remaining non-card icons to the single design
    accent. The typographic Riverfed cover wordmark stays fixed because
    it belongs to the product brand, not the selectable artifact design."""
    try:
        text = deck_md.read_text(encoding="utf-8")
    except OSError:
        return None
    md_dir = deck_md.parent
    cache: dict = {}
    changed = False

    text, n_cards = _recolor_card_icons(text, md_dir, card_palette, cache)
    if n_cards:
        changed = True

    if design_accent:
        def repl(m: "re.Match[str]") -> str:
            svg = _inline_svg(m.group("src"), md_dir, design_accent, cache)
            return svg if svg is not None else m.group(0)

        text, n_icons = re.subn(
            r'<img\b[^>]*?\bsrc="(?P<src>[^"]+\.svg)"[^>]*?/?>', repl, text,
            flags=re.IGNORECASE)
        if n_icons:
            changed = True

    return text if changed else None


def _rgba(h: str | None, alpha: float) -> str | None:
    if not h:
        return None
    try:
        r, g, b = _hex_to_rgb(h)
    except Exception:
        return None
    return f"rgba({r}, {g}, {b}, {alpha})"


# Generic / system family names we never try to fetch from Google Fonts.
_SYSTEM_FONTS = {
    "sans-serif", "serif", "monospace", "system-ui", "-apple-system",
    "blinkmacsystemfont", "segoe ui", "inherit", "initial", "ui-sans-serif",
}


def _font_import_css(typography: dict) -> str:
    """Build Google Fonts @import lines for the design's font families.

    The base theme references families by name only, so non-system fonts
    (Public Sans, Space Grotesk, Inter…) silently fall back to the OS default
    sans — which is why differently-fonted designs render identically. We
    @import each family (one line each, so one non-Google family failing
    doesn't break the rest) at the top of the derived theme so chromium
    actually fetches and renders them. Returns '' if there are no non-system
    families (or offline — the names still fall back gracefully)."""
    seen: set[str] = set()
    lines: list[str] = []
    for spec in typography.values():
        if not isinstance(spec, dict):
            continue
        fam = str(spec.get("fontFamily") or "").strip()
        key = fam.lower()
        if not fam or key in seen or key in _SYSTEM_FONTS:
            continue
        seen.add(key)
        name = fam.replace(" ", "+")
        lines.append(
            "@import url('https://fonts.googleapis.com/css2?"
            f"family={name}:wght@400;500;600;700&display=swap');")
    return "\n".join(lines)


def _build_design_theme(design_path: str, base_theme: Path,
                        slug: str) -> Path | None:
    """Load a design.md and write a derived Marp theme that re-skins the
    ai-builders theme with the design's full token set. Returns the path to
    the derived theme, or None on any failure (caller falls back to the base
    theme).

    The derived theme is the base CSS verbatim (keeping the `@theme
    ai-builders` name so the deck's front matter still resolves) plus an
    appended override block. The base theme isn't fully variable-driven —
    it hardcodes white card backgrounds, navy shadows, a saber-blue cover
    glow, 10px card radii, and white-on-dark cover/section text. So the
    override does two things:

      1. Re-points the base palette + grey ramp custom properties (most of
         the deck reads through these).
      2. Re-declares the handful of selectors that hardcode values, driving
         them from the design's tokens — card radius (design `rounded`),
         card surfaces/shadows, and the cover / section
         hero slides (design `components.cover-bg` / `section-divider-bg`),
         which a light/editorial palette like Heritage flips from dark to
         light.

    Later rules win by cascade order (equal specificity to the base), so the
    append is enough — no edit to the shared theme (the master handbook stays
    byte-identical)."""
    p = Path(design_path)
    if not p.exists():
        print(f"[studio_marp] design file not found: {p} — using base theme",
              file=sys.stderr)
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from design_tokens import load_design
    except Exception as exc:
        print(f"[studio_marp] design_tokens import failed: {exc} — base theme",
              file=sys.stderr)
        return None
    try:
        d = load_design(p)
        base_css = base_theme.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"[studio_marp] could not load design/theme: {exc} — base theme",
              file=sys.stderr)
        return None

    # Load the design's fonts via Google Fonts so they actually render. The
    # @import goes right after marp's `@import-theme` (a valid top-of-sheet
    # position) — appending it with the override at the end would be ignored.
    font_import = _font_import_css(d.typography or {})
    if font_import:
        marker = '@import-theme "default";'
        if marker in base_css:
            base_css = base_css.replace(marker, marker + "\n" + font_import, 1)
        else:
            base_css = font_import + "\n" + base_css

    c = d.colors or {}

    def col(key: str) -> str | None:
        return _norm_hex(c.get(key))

    primary, highlight, foundation, surface = (
        col("primary"), col("highlight"), col("foundation"), col("surface"))
    # The accent (eyebrows / KPI numbers / card stripes / links) is `primary`
    # when primary is vibrant, else `highlight` (Heritage: primary=ink ->
    # accent lives in clay highlight).
    accent = _pick_accent(primary, highlight)
    on_dark = col("on-primary") or "#ffffff"   # light text on dark slides

    # --- 1) palette + grey-ramp custom properties --------------------------
    root_pairs: list[tuple[str, str | None]] = [
        ("--accent", accent), ("--accent-hover", accent),
        ("--saber-blue-glow", accent),
        ("--neural", col("secondary")), ("--circuit", col("success")),
        ("--voltage", highlight), ("--fibre", col("warning")),
        ("--united", col("error")),
        ("--bg-cream", surface), ("--cream", col("surface-cream")),
        # foundation is reliably dark across light + dark designs, so it
        # powers the dark hero/section bg as well as body text + darkest grey.
        ("--bg-dark", foundation), ("--bg-elevated", foundation),
        ("--foundation", foundation), ("--foundation-2", foundation),
        ("--grey-1", foundation),
        # The grey ramp is NEUTRAL text — only ever map it from the design's
        # muted/faint text tokens, never `secondary` (which can be a bright
        # accent, e.g. Aurora's teal, and would tint subtitles/h2).
        ("--grey-2", col("text-muted") or col("text-faint")),
        ("--grey-3", col("text-muted") or col("text-faint")),
        ("--grey-4", col("text-faint") or col("text-muted")),
        ("--grey-5", col("text-faint") or col("text-muted")),
        ("--grey-6", col("surface-cream")),
    ]
    root_decls = [f"  {var}: {val};" for var, val in root_pairs if val]
    if not root_decls:
        print("[studio_marp] design has no usable colours — using base theme",
              file=sys.stderr)
        return None

    # --- 2) component-driven values ----------------------------------------
    comp = d.components or {}

    def comp_col(name: str, field: str) -> str | None:
        return _norm_hex((comp.get(name) or {}).get(field))

    card_bg = comp_col("card", "backgroundColor") or col("background-elevated")
    cover_bg = comp_col("cover-bg", "backgroundColor") or foundation
    cover_fg = comp_col("cover-bg", "textColor") or on_dark
    section_bg = comp_col("section-divider-bg", "backgroundColor") or foundation
    section_fg = comp_col("section-divider-bg", "textColor") or on_dark
    rounded = d.rounded or {}
    radius_card = ((comp.get("card") or {}).get("rounded")
                   or rounded.get("md") or rounded.get("lg"))
    shadow = _rgba(foundation, 0.10)
    glow = _rgba(accent, 0.40)
    code_tint = _rgba(accent, 0.12)

    body_font = d.font_family("body-md", "")
    display_font = d.font_family("h1", "")
    eyebrow_font = d.font_family("eyebrow", "")

    # --- 3) assemble override ----------------------------------------------
    out_lines: list[str] = [
        f"\n\n/* ===== design override: {d.name} "
        "(generated by studio_marp.py --design) ===== */",
        ":root {", *root_decls, "}",
    ]
    if body_font:
        out_lines.append(f'section {{ font-family: "{body_font}", {_FONT_STACK}; }}')
    if display_font:
        out_lines.append(
            f'h1, h2, h3, h4, h5, h6 {{ font-family: "{display_font}", {_FONT_STACK}; }}')
    if eyebrow_font:
        out_lines.append(
            '.eyebrow, .cards .num, .steps .num, .cite '
            f'{{ font-family: "{eyebrow_font}", {_FONT_STACK}; }}')

    # Inlined icon SVGs (recoloured at render time) sit in .icon /
    # .section-icon containers — the base theme only sizes the <img> child,
    # so size the <svg> too.
    out_lines.append(
        ".icon svg, .section-icon svg "
        "{ width: 100%; height: 100%; display: block; }")

    card_sel = ".kpi > *, .cards > *, .steps > *, .six-up > *, .versus .panel.new"
    if radius_card:
        out_lines.append(
            ".kpi > *, .cards > *, .versus .panel, .callout, .steps > *, "
            f".six-up > *, pre {{ border-radius: {radius_card}; }}")
    if card_bg:
        out_lines.append(f"{card_sel} {{ background: {card_bg}; }}")
    if shadow:
        out_lines.append(f"{card_sel} {{ box-shadow: 0 8px 22px {shadow}; }}")
    if on_dark:
        out_lines.append(
            ".callout, .callout p, .callout h2, .callout h3, .callout em, "
            f".outcomes div, th {{ color: {on_dark}; }}")
    if cover_bg:
        out_lines.append(f"section.cover {{ background: {cover_bg}; }}")
    if cover_fg:
        out_lines.append(f"section.cover, section.cover h1 {{ color: {cover_fg}; }}")
        out_lines.append(
            f"section.cover h2 {{ color: {cover_fg}; opacity: 0.72; }}")
        out_lines.append(
            ".tag-row span "
            f"{{ color: {cover_fg}; border-color: {_rgba(cover_fg, 0.30)}; "
            f"background: {_rgba(cover_fg, 0.06)}; }}")
    if section_bg:
        out_lines.append(f"section.section {{ background: {section_bg}; }}")
    if section_fg:
        out_lines.append(
            f"section.section, section.section h1 {{ color: {section_fg}; }}")
    if code_tint:
        out_lines.append(f"section.dark code {{ background: {code_tint}; }}")

    override = "\n".join(out_lines) + "\n"

    out = Path(tempfile.gettempdir()) / f"ai-builders-{slug or 'deck'}.css"
    try:
        out.write_text(base_css + override, encoding="utf-8")
    except OSError as exc:
        print(f"[studio_marp] cannot write derived theme: {exc} — base theme",
              file=sys.stderr)
        return None
    print(f"[studio_marp] applied design: {d.name} "
          f"(accent={accent}, surface={surface}, foundation={foundation}, "
          f"radius={radius_card or 'default'}, font={body_font or 'default'})",
          file=sys.stderr)
    return out


def _render_deck(out_path: Path, theme_path: Path,
                 design_path: str | None) -> dict[str, Path]:
    """Render the deck to HTML/PDF/PPTX through `theme_path`.

    Always prepares the deck first so each accent-card's icon is inlined and
    recoloured to its own card accent (matching the number + stripe). When a
    design is applied, also drops the cover logo and recolours non-card icons
    to the design accent. If the prep changed anything, render the prepared
    copy and copy the outputs onto the canonical paths; otherwise render in
    place."""
    card_palette = _card_accent_palette(design_path)
    design_accent = _design_accent(design_path) if design_path else None
    prepared = _prepare_deck(out_path, card_palette, design_accent)
    if prepared is not None:
        # Temp .md beside the original so any non-SVG relative refs still
        # resolve; outputs copied back to the canonical names afterwards.
        tmp_md = out_path.with_name(f"{out_path.stem}.recolor-tmp.md")
        try:
            tmp_md.write_text(prepared, encoding="utf-8")
            tmp_rendered = render_marp_outputs(tmp_md, theme_path)
            rendered: dict[str, Path] = {}
            for fmt, p in tmp_rendered.items():
                dest = _render_target(out_path, fmt)
                try:
                    if p.resolve() != dest.resolve():
                        shutil.copyfile(p, dest)
                    rendered[fmt] = dest
                except OSError as exc:
                    print(f"[studio_marp] {fmt}: copy failed — {exc}",
                          file=sys.stderr)
            print(f"[studio_marp] prepared deck (per-card icons"
                  f"{', design accent' if design_accent else ''}); "
                  f"rendered {len(rendered)} format(s)", file=sys.stderr)
            return rendered
        finally:
            tmp_md.unlink(missing_ok=True)
            for fmt in RENDER_FORMATS:
                _render_target(tmp_md, fmt).unlink(missing_ok=True)
    return render_marp_outputs(out_path, theme_path)


def build_prompt(wiki: str, user_prompt: str, slides: int, audience: str,
                 out_path: str) -> str:
    return f"""You are the Riverfed studio agent. Generate a Marp deck.

User request: {user_prompt}

Requirements:
- Read the design system at `{DESIGN_MD_REL}` and follow it.
- Use the example deck at `{EXAMPLE_DECK_REL}` for voice + structure.
- The theme is `{THEME_REL}`; reference component classes from design.md
  (`.kpi`, `.cards`, `.versus`, `.steps`, `.six-up.iconic`, `.callout`,
  `.outcomes`) instead of inventing new HTML.
- Draw content from the wiki at `{wiki}/`. Cite source slugs at the
  bottom-left of any slide with a non-obvious claim (use `.cite`).
- Target ~{slides} slides. Include a cover (`<!-- _class: cover -->`),
  one or two section dividers (`<!-- _class: section -->` with a
  `.section-num`), at least one dark slide for rhythm, and a lead slide
  for the big-idea wrap-up.
- Audience: {audience}.
- The Sith Red rule applies: never use `--united` / `--saber-red` on
  decorative cards — error states only.

Write the final Marp markdown to `{out_path}`. Do not output anything
else to stdout — just create the file. When done, print a single line:
  WROTE {out_path}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True,
                    help="Path to the wiki directory (e.g. 'wiki')")
    ap.add_argument("--prompt", required=True,
                    help="Short user instruction for what the deck is about")
    ap.add_argument("--slides", type=int, default=14,
                    help="Target slide count (default 14)")
    ap.add_argument("--audience", default="Operators who already use AI agents",
                    help="Audience description")
    ap.add_argument("--out-dir", default="wiki/training/studio",
                    help="Where to write the generated .md")
    ap.add_argument("--design", default=None,
                    help="Optional design.md path (e.g. designs/heritage.md). "
                         "Its color + font tokens are applied to the rendered "
                         "HTML/PDF/PPTX by deriving a theme that overrides the "
                         "ai-builders palette. Falls back to the base theme "
                         "if the file is missing or unparseable.")
    ap.add_argument("--provider", default="auto",
                    help=agent_runner.provider_arg_help(
                        "run this generation on"))
    args = ap.parse_args()

    slug = slugify(args.prompt)
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.md"
    rel_out = out_path.relative_to(ROOT).as_posix()

    from _wikis import resolve_vault_dir
    wiki_dir = resolve_vault_dir(args.wiki)
    prompt = build_prompt(args.wiki, args.prompt, args.slides,
                          args.audience, rel_out)

    # Agent invocation goes through the provider layer (A6 step 1) — it
    # owns binary resolution (Windows .CMD), stdin prompt delivery, env
    # scrub, NO_WINDOW and the timeout.
    provider, pstatus = agent_runner.resolve_provider(args.provider)
    if provider is None:
        print(f"Error: {agent_runner.unavailable_message(pstatus)}",
              file=sys.stderr)
        return 2

    print(f"[studio_marp] generating: {rel_out}", file=sys.stderr)
    try:
        res = agent_runner.run(prompt, cwd=ROOT, timeout=600,
                               add_dirs=[ROOT, wiki_dir], provider=provider)
    except FileNotFoundError:
        print(f"Error: the {provider} CLI could not be executed.",
              file=sys.stderr)
        return 2
    if res.timed_out:
        print("Error: generation timed out after 10 minutes.", file=sys.stderr)
        return 3

    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        return res.returncode

    if not out_path.exists():
        print(f"Error: agent did not write {rel_out}", file=sys.stderr)
        sys.stderr.write(res.output or "")
        return 4

    # Render the .md to HTML / PDF / PPTX next to the source. Best-effort:
    # if marp is missing or a format fails, we keep going and the server
    # parses whatever made it out. When --design is given, render through a
    # derived theme that overrides the palette/fonts; otherwise the base
    # ai-builders theme.
    theme_path = ROOT / THEME_REL
    if args.design:
        derived = _build_design_theme(args.design, theme_path, slug)
        if derived is not None:
            theme_path = derived
    # _render_deck always prepares the deck: per-card icons recoloured to each
    # card's accent (default + design), plus design-accent recolour of remaining
    # icons when a design is applied. The cover wordmark remains brand-fixed.
    rendered = _render_deck(out_path, theme_path, args.design)
    # Stdout contract:
    #   - One line per rendered format: `RENDERED:<fmt>:<rel-path>`
    #   - Last line is the canonical .md path (back-compat with server.py)
    for fmt, p in rendered.items():
        print(f"RENDERED:{fmt}:{_safe_rel(p, ROOT)}")
    print(rel_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
