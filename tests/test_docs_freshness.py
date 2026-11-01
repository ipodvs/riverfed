"""Mechanical half of the catch-up-docs discipline.

The `catch-up-docs` skill tells an agent to refresh the collaborator-facing
docs; nothing forces it. These tests enforce the subset a machine can actually
verify, so a doc lie that has burned us once cannot silently return.

Two kinds of check:

1. **Dated claims.** A doc asserts "we don't have X yet" and then X ships and
   nobody re-reads the sentence. Each entry pairs a phrase with the condition
   that makes it false. When you write a new "not yet" claim, add it here —
   that is the cost of making the claim.
2. **Agent parity.** `.claude/skills/` and `.agents/skills/` must stay
   mirrored, or Claude Code and Codex sessions follow different procedures and
   the two collaborators drift apart by tooling.
"""
from __future__ import annotations

import re
import unittest

import _util

PROJECT_DIR = _util.PROJECT_DIR


def _read(name: str) -> str:
    return (PROJECT_DIR / name).read_text(encoding="utf-8", errors="replace")


class DatedClaims(unittest.TestCase):
    """Each test: a doc must not still assert something the tree contradicts."""

    def test_no_stale_unit_test_claim(self):
        # Caught 2026-07-25: CLAUDE.md still said "No unit tests" long after
        # CI began running `unittest discover -s tests`.
        tests = list((PROJECT_DIR / "tests").glob("test_*.py"))
        if not tests:
            self.skipTest("no test modules — the claim would be true")
        for doc in ("CLAUDE.md", "AGENTS.md"):
            with self.subTest(doc=doc):
                self.assertNotIn(
                    "No unit tests", _read(doc),
                    f"{doc} claims there are no unit tests, but "
                    f"tests/ has {len(tests)} test modules that CI runs.")

    def test_no_stale_never_run_on_mac_claim(self):
        # Caught 2026-07-25: CONTRIBUTING told Paulo the app had "never been
        # run on a Mac" — false since 2026-07-15, in the section written at
        # the one person it misled.
        launchers = list(PROJECT_DIR.glob("*.command"))
        if not launchers:
            self.skipTest("no POSIX launchers — the claim may still hold")
        self.assertNotIn(
            "never been run on a Mac", _read("CONTRIBUTING.md"),
            f"CONTRIBUTING says the app has never run on a Mac, but "
            f"{len(launchers)} .command launchers are committed.")

    def test_changelog_guide_keeps_its_updated_stamp(self):
        # The guide's `Updated <date>` is how anyone (and the skill) works out
        # what Paulo has not yet been told. Losing it breaks that.
        text = _read("CHANGELOG.md")
        self.assertIn("How to read this changelog as PFreitas91", text,
                      "CHANGELOG lost the collaborator catch-up guide")
        head = text.split("## ", 2)[:3]
        self.assertRegex(
            "".join(head), r"Updated \d{4}-\d{2}-\d{2}",
            "the catch-up guide must carry an `Updated YYYY-MM-DD` stamp near "
            "the top so staleness is measurable")


class AgentParity(unittest.TestCase):
    """Claude Code and Codex must be given the same procedures."""

    def _skill_names(self, root: str) -> set[str]:
        d = PROJECT_DIR / root
        return {p.parent.name for p in d.glob("*/SKILL.md")}

    def test_skills_are_mirrored(self):
        claude = self._skill_names(".claude/skills")
        codex = self._skill_names(".agents/skills")
        self.assertTrue(claude, "no Claude skills found")
        self.assertEqual(
            claude, codex,
            "\n.claude/skills and .agents/skills have drifted:\n"
            f"  only in .claude: {sorted(claude - codex)}\n"
            f"  only in .agents: {sorted(codex - claude)}\n"
            "Mirror the skill so both collaborators' agents follow the same "
            "procedure.")

    @staticmethod
    def _headings(path) -> list[str]:
        """The skill's procedure as section headings, agent name erased.

        Deliberately structural rather than byte-for-byte: the two copies are
        hand-maintained and their prose legitimately differs (each addresses
        its own CLI). What must NOT differ is the procedure — if someone adds
        a step to one copy and not the other, the collaborators start
        following different SOPs, and that is what this catches."""
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^#{1,6}\s", line):
                h = line.strip()
                for name in ("Claude Code", "Codex CLI", "Codex", "Claude",
                             "claude", "codex"):
                    h = h.replace(name, "AGENT")
                out.append(h)
        return out

    def test_mirrored_skills_share_the_same_procedure(self):
        for name in self._skill_names(".claude/skills"):
            a = (PROJECT_DIR / ".claude/skills" / name / "SKILL.md")
            b = (PROJECT_DIR / ".agents/skills" / name / "SKILL.md")
            if not b.exists():
                continue  # reported by test_skills_are_mirrored
            with self.subTest(skill=name):
                self.assertEqual(
                    self._headings(a), self._headings(b),
                    f"skill '{name}' has different sections in .claude vs "
                    ".agents — the two agents would follow different "
                    "procedures. Prose may differ; steps may not.")


class SkillsIndex(unittest.TestCase):
    def test_every_skill_is_listed_in_the_readme(self):
        readme = _read(".claude/skills/README.md")
        for p in (PROJECT_DIR / ".claude/skills").glob("*/SKILL.md"):
            with self.subTest(skill=p.parent.name):
                self.assertIn(
                    p.parent.name, readme,
                    f"skill '{p.parent.name}' is missing from the skills "
                    "README table — it won't be discoverable.")


if __name__ == "__main__":
    unittest.main()
