"""One-off: capture /about as a shareable PNG + PDF for sending to investors.

Strips localhost CTAs, forces reveal-on-scroll sections visible, and freezes
the looping CSS animations so the capture is clean. Emits two files:
  - a tall full-page PNG (docs/screenshots/about-share.png)
  - a single continuous-page PDF with crisp vector text that scrolls smoothly
    (docs/screenshots/about-share.pdf)
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/about"
OUT_DIR = Path(__file__).resolve().parent / "docs" / "screenshots"
OUT_PNG = OUT_DIR / "about-share.png"
OUT_PDF = OUT_DIR / "about-share.pdf"

PREP_JS = r"""
() => {
  // 1. Reveal every scroll-animated section (IntersectionObserver never
  //    fires for below-the-fold elements during a full-page capture).
  document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));

  // 2. Freeze looping animations (float / spin / pulse / twinkle) so the
  //    capture is deterministic and crisp.
  const style = document.createElement('style');
  style.textContent = '*, *::before, *::after { animation: none !important; transition: none !important; }';
  document.head.appendChild(style);

  // 3. Neutralize localhost-only CTAs/links so investors don't tap dead links.
  document.querySelectorAll('a').forEach(a => {
    const href = a.getAttribute('href') || '';
    if (href.startsWith('/') || href.startsWith('#') || href.includes('127.0.0.1') || href.includes('localhost')) {
      a.removeAttribute('href');
      a.style.cursor = 'default';
    }
  });
}
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    width = 1280
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(
            viewport={"width": width, "height": 1000},
            device_scale_factor=2,  # retina-crisp text
        )
        page.goto(URL, wait_until="networkidle")
        page.evaluate(PREP_JS)
        page.wait_for_timeout(600)  # let fonts settle

        # PNG — tall raster of the whole page.
        page.screenshot(path=str(OUT_PNG), full_page=True)

        # PDF — single continuous page sized to the full content so it scrolls
        # smoothly with no awkward page-break cuts. Keep screen (dark) styling
        # rather than print media, and force background colors to render.
        page.emulate_media(media="screen")
        height = page.evaluate("document.documentElement.scrollHeight")
        page.pdf(
            path=str(OUT_PDF),
            width=f"{width}px",
            height=f"{height}px",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    for f in (OUT_PNG, OUT_PDF):
        print(f"Wrote {f}  ({f.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
