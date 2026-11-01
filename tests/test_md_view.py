"""md_view.render_page turns raw wiki/output markdown into a styled, on-brand
HTML document (fixes 'md files load very poorly' — served raw text/markdown).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "wiki" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import md_view  # noqa: E402

SAMPLE = """---
slug: agent-architecture
last_updated: 2026-08-05
sources: [a, b, c]
tags: [wiki/topics]
---

# Agent architecture

## What it is
The shape of a **production-grade** agent with `agents.md` and a [link](https://x.io).

Related: [[memory]] and [[nonexistent-page]].

- top item
  - nested item
- second item

1. first
2. second

> A callout worth boxing.

```python
def go():
    return 1
```

| Col A | Col B |
| ----- | ----- |
| x | y |
"""


class MdView(unittest.TestCase):
    def setUp(self) -> None:
        self.html = md_view.render_page(
            SAMPLE, title="Agent architecture",
            resolve_wikilink=lambda s: "/vault/page?wiki=wiki&file=concepts/memory.md"
            if s == "memory" else None,
        )

    def test_is_full_html_doc_not_raw_markdown(self) -> None:
        self.assertTrue(self.html.lstrip().startswith("<!doctype html>"))
        # frontmatter must NOT appear raw
        self.assertNotIn("slug: agent-architecture", self.html)
        self.assertNotIn("tags: [wiki/topics]", self.html)

    def test_frontmatter_becomes_meta_header(self) -> None:
        self.assertIn("3 sources", self.html)          # source count chip
        self.assertIn("updated 2026-08-05", self.html)
        self.assertIn(">wiki/topics<", self.html)       # tag chip

    def test_block_and_inline_rendering(self) -> None:
        self.assertIn("<h1>Agent architecture</h1>", self.html)
        self.assertIn("<h2>What it is</h2>", self.html)
        self.assertIn("<strong>production-grade</strong>", self.html)
        self.assertIn("<code>agents.md</code>", self.html)
        self.assertIn('<a href="https://x.io"', self.html)
        self.assertIn("<blockquote>", self.html)
        self.assertIn("<pre><code", self.html)
        self.assertIn("<table>", self.html)
        self.assertIn("<th>Col A</th>", self.html)

    def test_nested_lists(self) -> None:
        self.assertIn("<ul>", self.html)
        self.assertIn("<ol>", self.html)
        # the nested item must sit inside a nested <ul>, not flat
        self.assertIn("nested item", self.html)
        self.assertRegex(self.html, r"<li>top item<ul><li>nested item</li></ul></li>")

    def test_wikilinks_resolved_and_unresolved(self) -> None:
        # href is HTML-escaped (&amp;) — the browser decodes it back to &
        self.assertIn('<a class="wl" href="/vault/page?wiki=wiki&amp;file=concepts/memory.md">memory</a>',
                      self.html)
        self.assertIn('wl-dead', self.html)             # nonexistent-page styled, not linked
        self.assertNotIn('nonexistent-page</a>', self.html)

    def test_code_span_contents_not_reparsed(self) -> None:
        # backticked text with ** inside must stay literal
        html = md_view.render_page("use `a ** b` here", title="t")
        self.assertIn("<code>a ** b</code>", html)
        self.assertNotIn("<strong>", html)

    def test_demojibake_repairs_double_encoded_punctuation(self) -> None:
        # em dash, arrow, curly apostrophe stored as Windows-1252-over-UTF-8
        src = "A four-step plan â€” traffic â†’ sell, thatâ€™s it."
        html = md_view.render_page(src, title="t")
        self.assertIn("—", html)          # —
        self.assertIn("→", html)          # →
        self.assertIn("’", html)          # ’
        self.assertNotIn("â€", html)  # no â€ garbage left

    def test_demojibake_leaves_clean_text_untouched(self) -> None:
        html = md_view.render_page("Plain ASCII and a real em—dash.", title="t")
        self.assertIn("em—dash", html)

    def test_bare_urls_autolink(self) -> None:
        html = md_view.render_page(
            "Watch https://www.youtube.com/watch?v=b1mjQIiH7r4 for the demo.", title="t")
        self.assertIn('<a href="https://www.youtube.com/watch?v=b1mjQIiH7r4"', html)
        self.assertIn('target="_blank"', html)
        # trailing period is NOT swallowed into the href
        html2 = md_view.render_page("See https://example.com/x. Done.", title="t")
        self.assertIn('href="https://example.com/x"', html2)
        self.assertNotIn('href="https://example.com/x."', html2)

    def test_source_url_frontmatter_becomes_watch_link(self) -> None:
        src = '---\nurl: "https://www.youtube.com/watch?v=abc"\nchannel: Greg Isenberg\n---\n# T\nbody'
        html = md_view.render_page(src, title="T")
        self.assertIn('class="src-link"', html)
        self.assertIn('href="https://www.youtube.com/watch?v=abc"', html)
        self.assertIn("Greg Isenberg", html)

    def test_html_is_escaped(self) -> None:
        html = md_view.render_page("a <script>alert(1)</script> b", title="t")
        self.assertNotIn("<script>", html.split("<style>")[0] + html.split("</style>")[-1])
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
