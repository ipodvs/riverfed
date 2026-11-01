---
name: git-sync-ship
description: >
  The two-collaborator git workflow for the Riverfed repo — pull before
  work, commit with the house convention, push when done. Use whenever the user
  wants to "sync", "pull latest", "commit this", "ship it", "push", start or
  end a work session, or hits a push rejection / rebase conflict. Covers the
  sync.cmd/ship.cmd scripts, the commit message format + Co-Authored-By
  trailer, and the LF line-ending rule.
---

# Git sync / ship (two-collaborator workflow)

Two people (often plus AI agents) share `origin/main`. Always pull before
starting, always push when done. Two root scripts handle it safely:

| Script | When | What it does |
|---|---|---|
| `sync.cmd` | **Start** of a session | Pulls `origin/main` with rebase; stops cleanly if you have uncommitted changes |
| `ship.cmd` | **End** of a session, after committing | Pulls (rebase) then pushes — survives the other collaborator pushing first |

After `sync.cmd`, skim **[`CHANGELOG.md`](../../../CHANGELOG.md)** — its top
"Catch-up since you last synced" block is the fastest way to see what landed.

## Committing

One logical change per commit (if the body says "and also", split it). Format:

```
type(scope): one-line summary

Explanatory body — what changed and WHY (not just what).

Co-Authored-By: Codex Fable 5 <noreply@anthropic.com>
```

Types in use: `feat(wiki)`, `feat(studio)`, `feat(convert)`,
`feat(diagrams)`, `fix`, `docs`, `copy`, `content(wiki)`, `chore`, `rebrand`.

**Example:**
Input: added the design picker to Marp decks
Output: `feat(studio): apply the design picker to Marp decks`

Manual flow when not using the scripts:

```bash
git pull --rebase origin main      # before committing, if you skipped sync.cmd
git add <specific files>           # stage intentionally, not "git add ."
git commit -m "type(scope): ..."   # with body + Co-Authored-By trailer
git push origin main
```

## Gotchas

- **Line endings are LF** (`.gitattributes` → `* text=auto eol=lf`). If a file
  shows as modified with an empty `git diff`, it's CRLF phantom-noise, not a
  real change — ignore it or let `git add` renormalize. Don't fight it.
- **Stage intentionally.** The repo often has concurrent-activity changes
  (`landing/*.html`, `.obsidian/`, regenerated artifacts) that aren't yours —
  `git add .` would sweep them in. Stage the specific files you changed.
- **Push rejected?** The other collaborator pushed first. `ship.cmd` handles
  it by rebasing; manually: `git pull --rebase origin main` then push.
- **Don't commit** `node_modules/`, `wiki/training/studio/` output, `.env`,
  `designs/custom/*.md`, `output/*` — all gitignored.

## References (read on demand)

- [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) — full daily workflow +
  conflict-resolution recipes
- [`CHANGELOG.md`](../../../CHANGELOG.md) — what changed, newest first
