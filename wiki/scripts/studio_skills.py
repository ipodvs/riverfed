#!/usr/bin/env python3
"""Studio generator: compile a knowledge base into a Claude Code skill
library — the "knowledge in, agents out" step of the SOPs-to-Skills
pipeline (roadmap A3).

Reads a vault (ideally one using the sops-to-skills model, but any base
with actionable pages works), and emits:

    <out>/.claude/skills/<name>/SKILL.md     one skill per procedure/runbook
    <out>/.claude/skills/README.md           library overview + trigger table
    <out>/AGENTS.md                          context file for agent runtimes

The emitted format is the exact shape of this repo's six hand-written
skills (.claude/skills/*) and the operator best-practices captured in
the wiki (building-skills-for-claude): `name` + `description`
frontmatter where the description is the TRIGGER (Claude under-triggers,
so it quotes the user phrases that should fire it), a body that holds
the workflow with the WHY kept, a Gotchas section, and progressive
disclosure — references point back to the vault pages instead of
duplicating them.

Usage:
    py -3.13 wiki/scripts/studio_skills.py --wiki wikis/acme-ops \\
        --prompt "everything" \\
        [--out wiki/training/studio/skills/acme-ops] [--design <path>]

Prints one `SKILL:<rel-path>` line per generated skill (streamed into
the job log by server.py), then the library root as the final line.
`--design` is accepted for Studio API consistency but not applied —
skills are plain markdown.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

# The provider layer, imported at module level because the
# --provider help text is built from it during argparse setup.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_runner  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]


def slugify(s: str, max_len: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].rstrip("-") or "skills"


def build_prompt(wiki: str, user_prompt: str, out_rel: str,
                 business: str) -> str:
    return f"""You are the Riverfed skills compiler. Turn a knowledge base of
operational knowledge into a Claude Code skill library that a fresh
agent session can discover and execute.

User request: {user_prompt}

Source knowledge base: `{wiki}/` — read its `SCHEMA.md` and `index.md`
first, then every page in its folders. Procedure-like pages (step-by-step
how-tos) and runbook-like pages (symptom -> diagnose -> recover) each
become ONE skill. Policy/rule pages do NOT become standalone skills —
fold each policy into the Gotchas/rules of every skill whose procedure
cites it. If the base uses a different layout (topics/concepts), compile
the actionable how-to knowledge you find the same way; skip pages with
nothing executable.

Write the library under `{out_rel}/`:

1. `{out_rel}/.claude/skills/<skill-name>/SKILL.md` — one per skill.
   <skill-name> is a kebab-case verb phrase (e.g. `onboard-new-client`,
   `recover-crashed-server`). EXACT format (this project's house style):

   ---
   name: <skill-name>
   description: >
     <2-5 lines. What the skill does AND precisely when to trigger it —
     quote the user phrases that should fire it ("onboard", "new client
     signed", "set up the kickoff"), plus the failure symptoms if it is
     a recovery skill. Claude under-triggers, so be generous and
     specific. End with what the skill covers.>
   ---

   # <Human title>

   <One short orienting paragraph: the situation and the outcome.>

   ## Workflow
   Numbered imperative steps from the source page — keep the exact
   commands/paths in backticks and KEEP THE WHY where a step exists to
   prevent a known failure. Use a small table when steps map tools to
   purposes. If the source page has a "Done means" / success criterion,
   end the workflow with it.

   ## Gotchas
   The source page's gotchas PLUS every applicable policy, phrased as
   rules ("Never X — <why>", "Always Y before Z").

   ## References (read on demand)
   Repo-relative links to the source vault pages this skill was compiled
   from (progressive disclosure — depth lives there, don't duplicate it).

2. `{out_rel}/.claude/skills/README.md` — the library overview: one
   intro paragraph naming the business ({business}) and the source base,
   a trigger table (| Skill | Triggers on |, one row per skill), and a
   short "How skills load" note (frontmatter always in context -> body
   on trigger -> references on demand).

3. `{out_rel}/AGENTS.md` — a context file for agent runtimes that read
   AGENTS.md (uppercase — the convention Codex and other agents discover): what this business/knowledge base is, the skill library
   location, the table of skills with one-line whens, and any global
   policies an agent must respect regardless of skill.

Rules:
- Ground every skill in the vault's pages — do NOT invent steps,
  commands, or policies the base doesn't state. Thin pages make thin
  skills; that's correct.
- Kebab-case dir names; every SKILL.md gets valid `name` +
  `description` frontmatter; the description is the ONLY part always in
  context, so it must carry the full trigger surface.
- No emojis in file contents.

You are running NON-INTERACTIVE (headless); edits are pre-approved.
When done, print EXACTLY one line per skill in the form
  SKILL:{out_rel}/.claude/skills/<skill-name>/SKILL.md
then print the final line
  {out_rel}
and nothing after it.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True,
                    help="Path to the knowledge base (e.g. 'wikis/acme-ops')")
    ap.add_argument("--prompt", required=True,
                    help="Scope instruction (e.g. 'everything', 'just the "
                         "client-facing procedures')")
    ap.add_argument("--out", default=None,
                    help="Library root to write into (default: "
                         "wiki/training/studio/skills/<vault-name>)")
    ap.add_argument("--design", default=None,
                    help="Accepted for Studio API consistency; skills are "
                         "plain markdown, so it is not applied.")
    ap.add_argument("--provider", default="auto",
                    help=agent_runner.provider_arg_help(
                        "run this generation on"))
    args = ap.parse_args()

    from _wikis import display_path, resolve_vault_dir
    wiki_dir = resolve_vault_dir(args.wiki)
    wiki_rel = display_path(wiki_dir)
    if not (wiki_dir / "index.md").exists():
        print(f"Error: no knowledge base at {wiki_rel}/ (index.md missing)",
              file=sys.stderr)
        return 2
    vault_name = wiki_dir.name if wiki_dir.name != "wiki" else "wiki"

    if args.design:
        print("[studio_skills] note: --design is not applied to skill "
              "libraries (plain markdown)", file=sys.stderr)

    out_dir = (ROOT / (args.out or
                       f"wiki/training/studio/skills/{slugify(vault_name)}")).resolve()
    try:
        out_rel = out_dir.relative_to(ROOT).as_posix()
    except ValueError:
        print(f"Error: --out must point inside the project ({args.out})",
              file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    # Display name for the README/agents.md intro — the vault's index name.
    business = vault_name.replace("-", " ").title()
    try:
        for line in (wiki_dir / "index.md").read_text(
                encoding="utf-8", errors="replace").splitlines()[:20]:
            m = re.match(r"^name:\s*(.+)$", line)
            if m:
                business = m.group(1).strip().strip('"').strip("'")
                break
    except OSError:
        pass

    prompt = build_prompt(wiki_rel, args.prompt, out_rel, business)

    # Agent invocation goes through the provider layer (A6 step 1).
    provider, pstatus = agent_runner.resolve_provider(args.provider)
    if provider is None:
        print(f"Error: {agent_runner.unavailable_message(pstatus)}",
              file=sys.stderr)
        return 2

    print(f"[studio_skills] compiling {wiki_rel} -> {out_rel}", file=sys.stderr)
    res = agent_runner.run(prompt, cwd=ROOT, timeout=600,
                           add_dirs=[ROOT, wiki_dir], provider=provider)
    if res.timed_out:
        print("Error: generation timed out after 10 minutes.", file=sys.stderr)
        return 3

    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        return res.returncode

    # Trust the filesystem, not the transcript: enumerate what actually
    # landed, so the printed contract is accurate even if the agent's
    # final lines were chatty.
    skills_dir = out_dir / ".claude" / "skills"
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        sys.stderr.write((res.output or "")[-1500:] + "\n")
        print("Error: no skills were generated (no */SKILL.md under "
              f"{out_rel}/.claude/skills/).", file=sys.stderr)
        return 4
    missing = [n for n in ("README.md",) if not (skills_dir / n).exists()]
    if not (out_dir / "AGENTS.md").exists():
        missing.append("AGENTS.md")
    if missing:
        print(f"[studio_skills] warning: {', '.join(missing)} missing from "
              "the library", file=sys.stderr)

    for p in skill_files:
        print(f"SKILL:{p.relative_to(ROOT).as_posix()}")
    print(f"[studio_skills] {len(skill_files)} skill(s) compiled",
          file=sys.stderr)
    print(out_rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
