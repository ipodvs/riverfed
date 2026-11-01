---
slug: rebase-conflict-on-sync
kind: runbook
last_updated: 2026-06-11
sources: [contributing-to-riverfed]
tags: [wiki/runbooks]
---

# Rebase conflict on sync or ship

## Symptoms

`sync.cmd` or `ship.cmd` stops and tells you to resolve a conflict.
Files contain `<<<<<<<` conflict markers. This only happens when two
people edited the **same file at the same time** — rare in practice,
since collaborators are usually in different corners of the repo (one
in `wiki/`, the other in `landing/`).

## Diagnose

1. Run `git status` — always safe; it lists exactly which files are
   conflicted and confirms you're mid-rebase. If it shows no conflict,
   the script stopped for a different reason (read its message — both
   scripts print the exact recovery command).

## Recover

1. Open each file with `<<<<<<<` markers, pick the right lines, save.
2. Stage the resolved files: `git add <file1> <file2> ...`.
3. Continue: `git rebase --continue`.
4. Re-run `sync.cmd` or `ship.cmd` to finish the pull/push.
5. If you'd rather start over from the pre-rebase state instead:
   `git rebase --abort` — do NOT keep half-resolving if you're unsure;
   abort is the clean exit.

## Escalate

If you can't tell which lines are right (you'd be guessing over the
other collaborator's in-progress work), `git rebase --abort` and ask
them — GitHub issue or your usual real-time channel
(contributing-to-riverfed).
