from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class SharedNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.nav = (REPO / "landing" / "nav.js").read_text(encoding="utf-8")

    def test_primary_navigation_has_only_the_three_product_destinations(self) -> None:
        self.assertIn('{ href: "/",      label: "Add" }', self.nav)
        self.assertIn('{ href: "/wiki",  label: "Knowledge" }', self.nav)
        self.assertIn('studioCurrent + ">Create</a>"', self.nav)
        self.assertNotIn('label: "About"', self.nav)
        self.assertNotIn("Create →", self.nav)

    def test_brand_is_the_about_link_with_accessible_current_state(self) -> None:
        self.assertIn('routeHref("/about")', self.nav)
        self.assertIn('aria-label="Riverfed: About"', self.nav)
        self.assertIn('currentRoute === "/about"', self.nav)
        self.assertIn('aria-current="page"', self.nav)

    def test_keyboard_focus_and_mobile_links_remain_visible(self) -> None:
        self.assertIn(":focus-visible", self.nav)
        self.assertIn("outline:3px solid", self.nav)
        self.assertIn("@media(max-width:720px)", self.nav)
        self.assertNotIn(".pa-nav__link{display:none;}", self.nav)

    def test_file_previews_use_local_html_destinations(self) -> None:
        self.assertIn('location.protocol === "file:"', self.nav)
        self.assertIn('if (route === "/") return "../index.html";', self.nav)
        self.assertIn('if (route === "/about") return "index.html";', self.nav)
        self.assertIn('return "landing/" + route.slice(1) + ".html";', self.nav)

        pages = {
            REPO / "index.html": "landing/nav.js",
            REPO / "landing" / "index.html": "nav.js",
            REPO / "landing" / "studio.html": "nav.js",
            REPO / "landing" / "wiki.html": "nav.js",
        }
        for page, local_script in pages.items():
            text = page.read_text(encoding="utf-8")
            with self.subTest(page=page.relative_to(REPO)):
                self.assertIn('location.protocol === "file:"', text)
                self.assertIn(f'? "{local_script}" : "/nav.js"', text)


if __name__ == "__main__":
    unittest.main()
