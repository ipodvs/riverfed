from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "wiki" / "scripts"))

from design_tokens import load_design  # noqa: E402


FONT_QUERY = (
    "family=Inter:wght@400;500;600;700;800;900"
    "&family=JetBrains+Mono:wght@400;500;600;700"
)


class TypographyStrategy(unittest.TestCase):
    def test_product_pages_load_the_same_brand_families_and_weights(self) -> None:
        pages = (
            REPO / "index.html",
            REPO / "landing" / "index.html",
            REPO / "landing" / "studio.html",
            REPO / "landing" / "wiki.html",
            REPO / "landing" / "icons" / "preview.html",
        )
        for page in pages:
            text = page.read_text(encoding="utf-8")
            with self.subTest(page=page.relative_to(REPO)):
                self.assertIn(FONT_QUERY, text)
                self.assertIn("--font-sans:", text)
                self.assertIn("--font-mono:", text)
                self.assertIn("font-family: var(--font-sans)", text)

    def test_riverfed_preset_uses_the_brand_pair(self) -> None:
        design = load_design(REPO / "designs" / "riverfed.md")
        for role in ("display", "h1", "h2", "h3", "body-md"):
            with self.subTest(role=role):
                self.assertEqual(design.font_family(role), "Inter")
        for role in ("eyebrow", "cite"):
            with self.subTest(role=role):
                self.assertEqual(design.font_family(role), "JetBrains Mono")

    def test_native_renderer_keeps_wordmark_outside_design_overrides(self) -> None:
        source = (REPO / "wiki" / "scripts" / "studio_pptx.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('FONT_BRAND   = "Inter"', source)
        self.assertIn('("Riverfed", FONT_BRAND', source)
        self.assertNotIn('g["FONT_BRAND"]', source)

        server = (REPO / "server.py").read_text(encoding="utf-8")
        self.assertIn('d.font_family("h1", "Inter")', server)
        self.assertIn('d.font_family("body-md", "Inter")', server)
        self.assertIn('d.font_family("eyebrow", "JetBrains Mono")', server)

    def test_brand_surfaces_do_not_use_albert_sans_as_a_fallback(self) -> None:
        surfaces = (
            REPO / "landing" / "nav.js",
            REPO / "wiki" / "training" / "themes" / "ai-builders.css",
        )
        for surface in surfaces:
            with self.subTest(surface=surface.relative_to(REPO)):
                self.assertNotIn(
                    "Albert Sans", surface.read_text(encoding="utf-8")
                )


if __name__ == "__main__":
    unittest.main()
