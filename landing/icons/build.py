#!/usr/bin/env python3
"""Generate Riverfed original icon SVGs (+ PNG companions).

These replace the Streamline icons we'd been borrowing from the
Computacenter brand library. The Streamline library is licensed to
Computacenter for THEIR brand only; using them in Riverfed is
IP-theft. This script is the source-of-truth for our own icons.

Outputs:
  landing/icons/*.svg       : the web/HTML source of truth (themeable)
  landing/icons/png/*.png   : 256px raster companions for pptx embedding
                              (python-pptx can't insert SVG directly)

Style spec:
- viewBox  0 0 64 64    (4px grid, 16 cells)
- color    #4f8cff       (saber-blue default; inherits via currentColor)
- fill     currentColor  (themeable from CSS or parent <svg color="...">)
- No strokes; flat filled geometric shapes only
- Use opacity (0.5-0.85) to imply depth / hierarchy
- Rounded corners on rects (rx=2-4) for friendly geometry
- Recurring motif: 4-point sparkle for any AI-adjacent concept

Regenerate after editing:
    py -3.13 landing/icons/build.py
"""
from __future__ import annotations
import sys
from pathlib import Path

ICONS_DIR = Path(__file__).resolve().parent
PNG_DIR = ICONS_DIR / "png"
PNG_SIZE_PX = 256        # plenty for pptx; slides are ~13" wide @ 96dpi
ICON_SIZE = 64
DEFAULT_COLOR = "#4f8cff"

# Saber palette → PNG filename suffix. Default (saber-blue) has no
# suffix; the three accents do. pptx renderers look up
# `<icon>{suffix}.png` to recolour an icon per-cell.
ACCENT_VARIANTS = {
    "":        DEFAULT_COLOR,    # saber-blue (default)
    "-purple": "#7a59e2",        # neural / Mace
    "-green":  "#46c98b",        # circuit / Yoda
    "-yellow": "#ffd93d",        # voltage / Sentinel
}


def _svg(color: str, body: str) -> str:
    """Wrap an icon body in an SVG root with the given colour."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {ICON_SIZE} {ICON_SIZE}" '
        f'color="{color}" fill="currentColor">\n'
        + body + "</svg>\n"
    )


# Kept for tests / backwards compat
HEADER = (
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'viewBox="0 0 {ICON_SIZE} {ICON_SIZE}" '
    f'color="{DEFAULT_COLOR}" fill="currentColor">\n'
)
FOOTER = "</svg>\n"


def sparkle(cx: int, cy: int, r: int = 8, opacity: float = 1.0) -> str:
    """4-point star used as the house "AI" motif."""
    a, b = r, max(2, r // 3)
    d = (f"M{cx},{cy-a} L{cx+b},{cy-b} L{cx+a},{cy} L{cx+b},{cy+b} "
         f"L{cx},{cy+a} L{cx-b},{cy+b} L{cx-a},{cy} L{cx-b},{cy-b} Z")
    op = f' opacity="{opacity}"' if opacity < 1.0 else ""
    return f'  <path d="{d}"{op}/>\n'


# All active icons (referenced somewhere in the codebase). Names match
# the existing file names so HTML/CSS references don't need to change.
ICONS: dict[str, str] = {

    # -- network / connectivity --
    "hub-integration": (
        '  <circle cx="32" cy="32" r="10"/>\n'
        '  <circle cx="32" cy="10" r="5"/>\n'
        '  <circle cx="54" cy="32" r="5"/>\n'
        '  <circle cx="32" cy="54" r="5"/>\n'
        '  <circle cx="10" cy="32" r="5"/>\n'
        '  <rect x="30" y="13" width="4" height="13" rx="2"/>\n'
        '  <rect x="38" y="30" width="13" height="4" rx="2"/>\n'
        '  <rect x="30" y="38" width="4" height="13" rx="2"/>\n'
        '  <rect x="13" y="30" width="13" height="4" rx="2"/>\n'
    ),
    "network": (
        '  <circle cx="14" cy="14" r="5"/>\n'
        '  <circle cx="50" cy="14" r="5"/>\n'
        '  <circle cx="32" cy="32" r="7"/>\n'
        '  <circle cx="14" cy="50" r="5"/>\n'
        '  <circle cx="50" cy="50" r="5"/>\n'
        '  <path d="M17 17 L28 28 M47 17 L36 28 M17 47 L28 36 M47 47 L36 36" '
        'fill="none" stroke="currentColor" stroke-width="2.5" '
        'stroke-linecap="round" opacity="0.85"/>\n'
    ),

    # -- files / storage --
    "folder-spark": (
        '  <path d="M8 20 Q8 16 12 16 L24 16 L28 20 L52 20 '
        'Q56 20 56 24 L56 50 Q56 54 52 54 L12 54 Q8 54 8 50 Z"/>\n'
        + sparkle(46, 12, r=6, opacity=0.9)
    ),
    "file-spark": (
        '  <path d="M14 8 Q14 6 16 6 L36 6 L52 22 L52 56 '
        'Q52 58 50 58 L16 58 Q14 58 14 56 Z '
        'M36 6 L36 20 Q36 22 38 22 L52 22 L36 6 Z" '
        'fill-rule="evenodd"/>\n'
        + sparkle(28, 38, r=6, opacity=0.9)
    ),
    "database-ai": (
        '  <ellipse cx="26" cy="14" rx="16" ry="5"/>\n'
        '  <path d="M10 14 L10 22 Q10 25 26 25 Q42 25 42 22 L42 14 '
        'Q42 17 26 17 Q10 17 10 14 Z"/>\n'
        '  <path d="M10 28 L10 36 Q10 39 26 39 Q42 39 42 36 L42 28 '
        'Q42 31 26 31 Q10 31 10 28 Z" opacity="0.75"/>\n'
        '  <path d="M10 42 L10 50 Q10 53 26 53 Q42 53 42 50 L42 42 '
        'Q42 45 26 45 Q10 45 10 42 Z" opacity="0.55"/>\n'
        + sparkle(52, 16, r=5, opacity=0.95)
    ),
    "layers": (
        '  <rect x="12" y="40" width="40" height="11" rx="3"/>\n'
        '  <rect x="12" y="26" width="40" height="11" rx="3" opacity="0.75"/>\n'
        '  <rect x="12" y="12" width="40" height="11" rx="3" opacity="0.5"/>\n'
    ),
    "layers-stack": (
        '  <path d="M32 8 L56 22 L32 36 L8 22 Z"/>\n'
        '  <path d="M8 32 L32 46 L56 32" fill="none" stroke="currentColor" '
        'stroke-width="4" stroke-linecap="round" stroke-linejoin="round" '
        'opacity="0.75"/>\n'
        '  <path d="M8 44 L32 58 L56 44" fill="none" stroke="currentColor" '
        'stroke-width="4" stroke-linecap="round" stroke-linejoin="round" '
        'opacity="0.5"/>\n'
    ),

    # -- AI / sparks --
    "ai-spark": (
        sparkle(32, 32, r=22)
        + sparkle(52, 14, r=6, opacity=0.7)
        + sparkle(14, 50, r=4, opacity=0.6)
    ),

    # -- comms --
    "chat-check": (
        '  <path d="M10 14 Q10 8 16 8 L48 8 Q54 8 54 14 L54 38 '
        'Q54 44 48 44 L26 44 L16 54 L18 44 Q10 44 10 38 Z"/>\n'
        '  <path d="M22 24 L29 32 L44 18" fill="none" stroke="#fff" '
        'stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>\n'
    ),
    "mail-send": (
        '  <rect x="6" y="14" width="52" height="36" rx="3"/>\n'
        '  <path d="M6 18 L32 36 L58 18" fill="none" stroke="#fff" '
        'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>\n'
    ),
    "announcement": (
        '  <path d="M14 26 L14 38 Q14 42 18 42 L20 42 L22 52 '
        'L30 52 L28 42 L42 48 L52 54 L52 10 L42 16 L28 22 L18 22 '
        'Q14 22 14 26 Z"/>\n'
        '  <circle cx="40" cy="32" r="2.5" opacity="0.5"/>\n'
    ),
    "megaphone": (
        '  <path d="M10 26 L10 38 Q10 42 14 42 L18 42 L20 52 '
        'L28 52 L26 42 L40 48 L52 54 L52 10 L40 16 L26 22 L14 22 '
        'Q10 22 10 26 Z"/>\n'
        '  <path d="M52 22 L58 20 L58 44 L52 42 Z" opacity="0.7"/>\n'
    ),

    # -- devices --
    "laptop": (
        '  <rect x="10" y="14" width="44" height="28" rx="3"/>\n'
        '  <rect x="14" y="18" width="36" height="20" rx="1" '
        'fill="#fff" opacity="0.18"/>\n'
        '  <path d="M4 46 L60 46 Q62 46 60 50 L4 50 Q2 46 4 46 Z"/>\n'
    ),

    # -- people --
    "users-team": (
        '  <circle cx="20" cy="22" r="6"/>\n'
        '  <path d="M8 50 Q8 38 20 38 Q32 38 32 50 L32 54 L8 54 Z"/>\n'
        '  <circle cx="44" cy="22" r="6"/>\n'
        '  <path d="M32 50 Q32 38 44 38 Q56 38 56 50 L56 54 L32 54 Z" '
        'opacity="0.85"/>\n'
        '  <circle cx="32" cy="14" r="7" opacity="0.7"/>\n'
        '  <path d="M20 36 Q20 26 32 26 Q44 26 44 36" opacity="0.7"/>\n'
    ),
    "critical-thinking": (
        '  <path d="M22 12 Q22 6 28 6 L40 6 Q48 6 48 14 L48 22 '
        'Q48 28 44 30 L44 38 L40 38 L40 42 L34 42 L34 50 L26 50 '
        'L26 44 Q26 42 24 40 Q18 36 18 28 Q18 18 22 12 Z"/>\n'
        + sparkle(52, 26, r=5, opacity=0.8)
    ),

    # -- time --
    "calendar-schedule": (
        '  <rect x="8" y="12" width="48" height="44" rx="4"/>\n'
        '  <rect x="8" y="12" width="48" height="10" rx="4" opacity="0.55"/>\n'
        '  <rect x="16" y="6" width="4" height="12" rx="2"/>\n'
        '  <rect x="44" y="6" width="4" height="12" rx="2"/>\n'
        '  <circle cx="20" cy="32" r="2.5" fill="#fff"/>\n'
        '  <circle cx="32" cy="32" r="2.5" fill="#fff"/>\n'
        '  <circle cx="44" cy="32" r="2.5" fill="#fff"/>\n'
        '  <circle cx="20" cy="44" r="2.5" fill="#fff"/>\n'
    ),

    # -- system / config --
    "cog": (
        '  <path d="M28 4 L36 4 L37.5 12 Q40.5 13 43 14.5 L50 11 L55 16 '
        'L51 23 Q52.5 25.5 53 28.5 L60 30 L60 34 L53 35.5 '
        'Q52.5 38.5 51 41 L55 48 L50 53 L43 49.5 Q40.5 51 37.5 52 L36 60 '
        'L28 60 L26.5 52 Q23.5 51 21 49.5 L14 53 L9 48 L13 41 '
        'Q11.5 38.5 11 35.5 L4 34 L4 30 L11 28.5 Q11.5 25.5 13 23 '
        'L9 16 L14 11 L21 14.5 Q23.5 13 26.5 12 Z '
        'M32 22 Q22 22 22 32 Q22 42 32 42 Q42 42 42 32 Q42 22 32 22 Z" '
        'fill-rule="evenodd"/>\n'
    ),

    # -- business --
    "coins-stack": (
        '  <ellipse cx="32" cy="48" rx="20" ry="6"/>\n'
        '  <path d="M12 38 L12 48 Q12 54 32 54 Q52 54 52 48 L52 38 '
        'Q52 44 32 44 Q12 44 12 38 Z"/>\n'
        '  <ellipse cx="32" cy="34" rx="20" ry="6" opacity="0.85"/>\n'
        '  <path d="M12 24 L12 34 Q12 40 32 40 Q52 40 52 34 L52 24 '
        'Q52 30 32 30 Q12 30 12 24 Z" opacity="0.85"/>\n'
        '  <ellipse cx="32" cy="20" rx="20" ry="6" opacity="0.7"/>\n'
        '  <path d="M12 10 L12 20 Q12 26 32 26 Q52 26 52 20 L52 10 '
        'Q52 16 32 16 Q12 16 12 10 Z" opacity="0.7"/>\n'
    ),
    "trophy": (
        '  <path d="M20 8 L44 8 L44 22 Q44 32 32 36 Q20 32 20 22 Z"/>\n'
        '  <path d="M8 12 L20 12 L20 22 Q14 22 12 18 Q10 14 8 12 Z" '
        'opacity="0.7"/>\n'
        '  <path d="M44 12 L56 12 Q54 14 52 18 Q50 22 44 22 L44 12 Z" '
        'opacity="0.7"/>\n'
        '  <rect x="28" y="36" width="8" height="10"/>\n'
        '  <rect x="20" y="46" width="24" height="6" rx="2"/>\n'
    ),

    # -- product / build --
    "browser-build": (
        '  <rect x="8" y="12" width="48" height="40" rx="3"/>\n'
        '  <rect x="8" y="12" width="48" height="10" rx="3" opacity="0.55"/>\n'
        '  <circle cx="14" cy="17" r="1.5" fill="#fff"/>\n'
        '  <circle cx="20" cy="17" r="1.5" fill="#fff"/>\n'
        '  <circle cx="26" cy="17" r="1.5" fill="#fff"/>\n'
        '  <path d="M20 32 L28 40 L20 48 M32 48 L44 48" fill="none" '
        'stroke="#fff" stroke-width="3" stroke-linecap="round" '
        'stroke-linejoin="round"/>\n'
    ),
    "startup": (
        '  <path d="M32 6 Q44 14 44 32 L44 42 L36 50 L28 50 L20 42 '
        'L20 32 Q20 14 32 6 Z"/>\n'
        '  <circle cx="32" cy="24" r="4" fill="#fff"/>\n'
        '  <path d="M28 50 L24 60 L29 57 L30 60 L32 50 Z '
        'M36 50 L40 60 L35 57 L34 60 L32 50 Z" opacity="0.7"/>\n'
    ),

    # -- workflow --
    "loop": (
        '  <path d="M32 14 Q14 14 14 32 Q14 50 32 50 Q44 50 50 40 '
        'L46 38 Q42 46 32 46 Q18 46 18 32 Q18 18 32 18 L32 24 '
        'L42 14 L32 4 Z"/>\n'
    ),
}


def _png_white_to_transparent(png_bytes: bytes) -> bytes:
    """Convert white pixels in a PNG to transparent. svglib+reportlab
    always renders with an opaque white canvas; this post-processes
    so the icon sits cleanly on any background (cream slide, dark
    card, etc.) instead of carrying a white square around it."""
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


def _render_png_from_svg(svg_content: str, png_path: Path,
                          size_px: int = PNG_SIZE_PX) -> bool:
    """Render an SVG string to a transparent PNG via svglib+reportlab.

    The white canvas background is post-processed to transparent so
    the icon doesn't carry a white square around it. Returns True on
    success, False if svglib isn't installed."""
    try:
        from io import BytesIO
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
    except ImportError:
        print("  [skip png] svglib/reportlab not installed; run "
              "`pip install svglib reportlab` for pptx-embeddable PNGs",
              file=sys.stderr)
        return False
    drawing = svg2rlg(BytesIO(svg_content.encode("utf-8")))
    if drawing is None:
        return False
    scale = size_px / float(drawing.width or size_px)
    drawing.scale(scale, scale)
    drawing.width *= scale
    drawing.height *= scale
    png_bytes = renderPM.drawToString(drawing, fmt="PNG")
    png_bytes = _png_white_to_transparent(png_bytes)
    png_path.write_bytes(png_bytes)
    return True


def _render_png(svg_path: Path, png_path: Path, size_px: int = PNG_SIZE_PX) -> None:
    """Render an SVG file path to a PNG. Wrapper kept for the
    riverfed-mark* SVGs that aren't in the ICONS dict."""
    _render_png_from_svg(svg_path.read_text(encoding="utf-8"),
                         png_path, size_px=size_px)


def main() -> int:
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    total_pngs = 0
    for name, body in ICONS.items():
        # Write the canonical SVG (saber-blue, used by the web pages)
        svg_path = ICONS_DIR / f"{name}.svg"
        svg_path.write_text(_svg(DEFAULT_COLOR, body), encoding="utf-8")

        # Render 4 PNG variants: default + 3 accents
        for suffix, color in ACCENT_VARIANTS.items():
            png_path = PNG_DIR / f"{name}{suffix}.png"
            colored = _svg(color, body)
            if _render_png_from_svg(colored, png_path):
                total_pngs += 1
        print(f"wrote {svg_path.name} + {len(ACCENT_VARIANTS)} PNG variants")

    # Also render the riverfed-mark* brand SVGs to PNG (no accent variants;
    # the brand mark is fixed-colour).
    for logo in ICONS_DIR.glob("riverfed-mark*.svg"):
        _render_png(logo, PNG_DIR / f"{logo.stem}.png")
        total_pngs += 1

    print(f"\nGenerated {len(ICONS)} icon SVGs in {ICONS_DIR}/")
    print(f"Generated {total_pngs} PNG variants in {PNG_DIR}/ "
          f"(default + purple + green + yellow)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
