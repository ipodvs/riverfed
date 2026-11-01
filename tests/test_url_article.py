"""Readable-article extraction for non-YouTube web URLs (convert.py).

Fully offline: exercises `extract_article_markdown` on a hand-built HTML
page (navigation + article + footer). No network — readability isolates the
article region and markitdown renders it. Guards the three properties the
feature promises: boilerplate is dropped, heading structure survives, and
relative links become absolute.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import convert  # noqa: E402

ARTICLE_DEPS_AVAILABLE = all(
    importlib.util.find_spec(module) is not None
    for module in ("bs4", "lxml", "markitdown", "readability")
)
requires_article_deps = unittest.skipUnless(
    ARTICLE_DEPS_AVAILABLE,
    "requires optional web-article extraction dependencies",
)


# A realistic-density page: chrome around an article whose prose clearly
# outweighs the nav/footer, so readability keeps the <article> and discards
# the chrome (its density heuristic needs real textual weight to discriminate,
# which a toy two-line fixture does not provide).
_P = (
    "The {s} section carries several sentences of genuine analytical prose "
    "about harness engineering, verification loops, and autonomous agents, so "
    "the readability extractor scores this region as the dominant content of "
    "the page and keeps it intact rather than discarding it as peripheral "
    "chrome that surrounds the real article body. "
)
FIXTURE_HTML = f"""<!doctype html>
<html><head><title>ACME Blog — Home | Pricing | Careers</title></head>
<body>
  <nav><a href="/">Home</a> <a href="/pricing">Pricing</a>
       <a href="/careers">Careers</a> <img src="/logo.svg" alt="ACME logo"></nav>
  <article>
    <h1>The Real Article Title</h1>
    <p>{_P.format(s="opening") * 2}</p>
    <img src="/media/architecture.png" alt="An architecture diagram">
    <h2>First Section Heading</h2>
    <p>{_P.format(s="first") * 3} It also contains
    <a href="/deep/reference">a relative link</a> that must be rewritten to an
    absolute URL once the page is pulled into the wiki, otherwise it dangles.</p>
    <img src="/_next/image?url=https%3A%2F%2Fcdn.example.com%2Ffig2.png&w=800" alt="">
    <h2>Second Section Heading</h2>
    <p>{_P.format(s="second") * 3}</p>
  </article>
  <footer>Copyright 2026 ACME. All rights reserved.
    Privacy Policy · Cookie Policy · Terms and Conditions</footer>
</body></html>
"""

BASE_URL = "https://example.com/blog/the-real-article-title"


@requires_article_deps
class ExtractArticleMarkdown(unittest.TestCase):
    def setUp(self):
        result = convert.extract_article_markdown(FIXTURE_HTML, BASE_URL)
        self.assertIsNotNone(
            result, "extraction returned None on a well-formed article page"
        )
        self.body, self.title = result

    def test_headings_are_preserved(self):
        self.assertIn("## First Section Heading", self.body)
        self.assertIn("## Second Section Heading", self.body)

    def test_article_prose_is_kept(self):
        self.assertIn("genuine analytical prose", self.body)
        self.assertIn("dominant content", self.body)

    def test_navigation_and_footer_are_stripped(self):
        self.assertNotIn("All rights reserved", self.body)
        self.assertNotIn("Cookie Policy", self.body)
        self.assertNotIn("Careers", self.body)

    def test_relative_links_become_absolute(self):
        self.assertIn("https://example.com/deep/reference", self.body)
        self.assertNotIn("](/deep/reference)", self.body)

    def test_content_images_survive_and_are_cleaned(self):
        # Whether readability keeps an image inline or drops it (we re-attach
        # dropped ones as a Figures section), the article's figures end up in
        # the body with absolute, unwrapped URLs.
        self.assertIn("https://example.com/media/architecture.png", self.body)
        # Next.js proxy URL unwrapped to the underlying file
        self.assertIn("https://cdn.example.com/fig2.png", self.body)
        self.assertNotIn("_next/image", self.body)

    def test_chrome_logos_are_not_treated_as_figures(self):
        # the nav SVG logo must never appear
        self.assertNotIn("logo.svg", self.body)
        self.assertNotIn("ACME logo", self.body)


@requires_article_deps
class CollectContentImages(unittest.TestCase):
    """Deterministic unit of the image collector, independent of readability."""

    def setUp(self):
        self.images = convert._collect_content_images(FIXTURE_HTML, BASE_URL)
        self.by_url = {u: alt for u, alt in self.images}

    def test_relative_image_absolutized_with_alt(self):
        self.assertEqual(
            self.by_url.get("https://example.com/media/architecture.png"),
            "An architecture diagram",
        )

    def test_next_image_proxy_is_unwrapped(self):
        self.assertIn("https://cdn.example.com/fig2.png", self.by_url)

    def test_svg_logo_and_chrome_excluded(self):
        urls = " ".join(self.by_url)
        self.assertNotIn("logo.svg", urls)

    def test_thin_page_declines_so_caller_can_fall_back(self):
        # A near-empty page must return None (signal: fall back to markitdown),
        # not a useless stub.
        thin = "<html><body><article><p>hi</p></article></body></html>"
        self.assertIsNone(convert.extract_article_markdown(thin, BASE_URL))


if __name__ == "__main__":
    unittest.main()
