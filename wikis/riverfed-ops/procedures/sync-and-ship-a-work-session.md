---
slug: sync-and-ship-a-work-session
kind: procedure
trigger: starting or ending any work session on the repo
last_updated: 2026-08-15
sources: [contributing-to-riverfed]
policies: [commit-message-format, branch-strategy, review-ai-changes-before-commit]
tags: [wiki/procedures, commit-message-format, branch-strategy, review-ai-changes-before-commit]
---

# Sync and ship a work session

## When to run this

At the **start** of every session (pull what the other collaborator
shipped) and at the **end** of every session (push your commits). The
repo has two-or-more collaborators; skipping the start step is why
pushes get rejected later.

## Steps

1. Double-click `sync.cmd` (project root, safe from Explorer) — pulls
   the latest from `origin/main` with rebase. It stops with a clear
   message if you have uncommitted changes, so you never lose work.
2. Skim the top "Catch-up since you last synced" block of
   `CHANGELOG.md` — the quickest way to see what landed while you were
   away, grouped by area with commit hashes and the files to look at.
3. Create a fresh branch for the block per [[branch-strategy]].
4. Before each commit, review `git diff`
   ([[review-ai-changes-before-commit]]) — especially after an agent
   session.
5. Stage intended paths by name, then commit following
   [[commit-message-format]]. Do not use `git add .` after an agent session.
6. Push the branch and open a draft PR with `gh pr create --draft --fill`.
   Merge only after CI and review pass. Then switch to `main` and sync again.

## Gotchas

- Both scripts handle the common failure modes — uncommitted work,
  rebase conflicts, push rejections — and print the exact recovery
  command to type. If either stops on a conflict:
  [[rebase-conflict-on-sync]].
- If you skipped `sync.cmd` and a bare `git push` is rejected, that's
  the other collaborator having pushed first — `ship.cmd` recovers
  automatically by rebasing before pushing.
- The scripts only run silently after the one-time machine setup
  (`git config --global pull.rebase true` + `gh auth setup-git`) in
  [[set-up-a-fresh-machine]].
- When in doubt, `git status` — always safe to run, tells you exactly
  what state your working tree is in.

## Done means

The feature branch is pushed, its PR is visible and green, `git status` is
clean, and merged work is present on `origin/main`.
