"""Issue #3 — the shared page-frontmatter parser understands every documented
form (inline + block lists), and a block-list relationship field produces the
same graph as its inline twin."""
import unittest

import _util  # noqa: F401  (path bootstrap)
import _frontmatter as F


class ParseForms(unittest.TestCase):
    def test_inline_and_block_lists_agree(self):
        inline = "---\nslug: x\nsources: [alpha, beta]\n---\nbody"
        block = "---\nslug: x\nsources:\n  - alpha\n  - beta\n---\nbody"
        self.assertEqual(F.parse_frontmatter(inline)["sources"], ["alpha", "beta"])
        self.assertEqual(F.parse_frontmatter(block)["sources"], ["alpha", "beta"])

    def test_empty_list(self):
        self.assertEqual(F.parse_frontmatter("---\ntags: []\n---\n")["tags"], [])

    def test_quoted_scalar_with_colon(self):
        fm = F.parse_frontmatter('---\ntitle: "Foo: bar"\n---\n')
        self.assertEqual(fm["title"], "Foo: bar")

    def test_url_hash_is_not_a_comment(self):
        fm = F.parse_frontmatter("---\nurl: https://x#y\n---\n")
        self.assertEqual(fm["url"], "https://x#y")

    def test_trailing_comment_stripped(self):
        fm = F.parse_frontmatter("---\nnote: hello  # a comment\n---\n")
        self.assertEqual(fm["note"], "hello")

    def test_quoted_block_item(self):
        fm = F.parse_frontmatter('---\nsources:\n  - "quoted-slug"\n---\n')
        self.assertEqual(fm["sources"], ["quoted-slug"])

    def test_no_frontmatter(self):
        self.assertEqual(F.parse_frontmatter("# just a body\n"), {})

    def test_hr_in_body_is_not_frontmatter(self):
        self.assertEqual(F.parse_frontmatter("# title\n\n---\n\nmore\n"), {})


class AsList(unittest.TestCase):
    def test_scalar_does_not_iterate_chars(self):
        self.assertEqual(F.as_list("foo"), ["foo"])

    def test_list_preserved(self):
        self.assertEqual(F.as_list(["a", "b"]), ["a", "b"])

    def test_none_and_empty(self):
        self.assertEqual(F.as_list(None), [])
        self.assertEqual(F.as_list(""), [])


if __name__ == "__main__":
    unittest.main()
