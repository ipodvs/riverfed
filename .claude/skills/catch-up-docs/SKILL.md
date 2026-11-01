---
name: catch-up-docs
description: >
  Refresh the collaborator-facing docs so Paulo (PFreitas91) can sync, catch up,
  and contribute without having been present for any decision. Use after
  shipping a coherent block of work, when the user says "update the docs",
  "catch up the changelog", "make sure my brother can follow this", before a
  hand-off, or whenever you notice a doc claiming something that is no longer
  true. Covers which four docs to touch in what order, the staleness checks
  that have actually caught bugs, and the roadmap's formatter quirk.
---

# Catch-up docs (keep the second collaborator current)

**Paulo** (GitHub `PFreitas91`) is the second human on this repo. He syncs
intermittently, was present for **none** of the design decisions, and relies
entirely on these docs. He is also the designated **Mac tester**. Every
coherent block of shipped work must leave the docs true for him — otherwise
he pulls, reads something stale, and either wastes a session or reports a
"bug" that is really a doc lie.

This is not optional polish. Stale docs propagate: the ingest agent reads
`plans/implementation-roadmap.md` as ground truth, so a block that shipped but
was never ticked gets restated as "the next action" in generated pages.

## The four docs, in priority order

| # | Doc | Update when | Note |
|---|---|---|---|
| 1 | [`CHANGELOG.md`](../../../CHANGELOG.md) | **Every** shipped block | New section at top (newest-first) **and** refresh the "How to read this changelog as PFreitas91" guide that sits above all sections — that guide is his entry point, not the sections |
| 2 | [`plans/implementation-roadmap.md`](../../../plans/implementation-roadmap.md) | A block ships or partly ships | Tick it. See the formatter warning below |
| 3 | [`CLAUDE.md`](../../../CLAUDE.md) / [`AGENTS.md`](../../../AGENTS.md) | Structure, scripts, or "What's intentionally not done yet" changed | Both files — they mirror each other for Claude Code and Codex |
| 4 | [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) | Only when the **human workflow** changed | Includes the Mac section, which is written *at* Paulo |

`README.md` is the product narrative for strangers — update it when a
user-visible feature lands, not on every block.

## Do this

1. **Find what he missed.** The CHANGELOG guide carries an `Updated <date>`
   line; everything after it is unreported:
   ```bash
   git log --oneline "$(git log -1 --format=%H -- CHANGELOG.md)..HEAD"
   ```
2. **Write the CHANGELOG section** — grouped by feature, with the file paths
   he'd touch to use or extend it, and *why* the change was made. He can read
   the diff himself; what he can't recover is the reasoning.
3. **Refresh the guide at the top** — it must lead with the newest work and
   give him a numbered catch-up path. If Python changed, say so: he has to
   restart the server after pulling.
4. **Run the staleness checks below**, then tick the roadmap.
5. Commit in the house format (see the `git-sync-ship` skill).

## Staleness checks that have actually caught something

Claims rot silently because nobody re-reads a doc they wrote. These are real
misses found later, so check each one:

- **"No unit tests"** in CLAUDE.md — false since CI began running
  `unittest discover -s tests`. Any "we don't have X yet" claim needs a check
  that we still don't.
- **"Never been run on a Mac"** in CONTRIBUTING — false from 2026-07-15, and
  it was written *at* the one person it misled.
- **An unticked roadmap block that shipped** — C2 had six `.command`
  launchers, POSIX venv resolution and a verified end-to-end Mac run before
  anyone marked it. Grep the block's deliverables against the tree before
  believing its status.
- **Instructions naming a file that no longer exists** — e.g. CONTRIBUTING
  pointed at a `sync_vaults.py` invocation after `sync-vaults.command` shipped.

Rule of thumb: **any sentence containing "never", "not yet", "only", "first",
or "currently" is a dated claim.** Verify it against the tree rather than
trusting it.

## Roadmap formatter warning

`plans/implementation-roadmap.md` is reformatted by an editor integration that
races the edit tool — an edit can be silently reverted or mangled. **Splice it
with a script instead**, asserting the match count first so a failed match is
loud:

```python
from pathlib import Path
p = Path("plans/implementation-roadmap.md")
t = p.read_text(encoding="utf-8")
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")
```

## Scope

Ticking a roadmap block is a factual edit — do it. **Changing what a block
*means*, reordering the sequence, or declaring a block done when only part
shipped are decisions, not updates**: propose those, don't apply them. When a
block is partly delivered, say exactly which parts, as C2 does.
