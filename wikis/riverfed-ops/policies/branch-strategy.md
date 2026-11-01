---
slug: branch-strategy
kind: policy
last_updated: 2026-08-15
sources: [contributing-to-riverfed]
tags: [wiki/policies]
---

# One feature branch and pull request per coherent block

## The rule

Start each coherent block from an up-to-date `main`, create a fresh feature
branch, and open a pull request. After the PR merges, return to `main` and do
not keep adding commits to the merged branch:

```powershell
git switch main
sync.cmd
git switch -c agent/my-thing
# ... commit intentional files ...
git push -u origin agent/my-thing
gh pr create --draft --fill
```

## Why it exists

This keeps `main` clone-ready and gives both collaborators one visible review
and merge path. It also prevents a merged branch from quietly collecting
unpublished commits (contributing-to-riverfed).

## Scope & exceptions

App, pipeline, setup, dependency, generated-artifact, and roadmap changes all
use the branch + PR path through [[sync-and-ship-a-work-session]]. Tiny
typo-only documentation changes may go directly to `main` when both
collaborators agree.
