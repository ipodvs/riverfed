---
slug: review-ai-changes-before-commit
kind: policy
last_updated: 2026-08-15
sources: [contributing-to-riverfed]
tags: [wiki/policies]
---

# Always review git diff before committing

## The rule

Always review `git diff` before committing — even when an agent says
"I made the change you asked for". Trust but verify.

## Why it exists

Sometimes the agent edits more than you wanted, or breaks something
subtle. The diff review is the cheap gate that catches it before it
lands in history (contributing-to-riverfed). When the review
reveals a mess, recover via [[claude-code-made-a-mess]].

## Scope & exceptions

Every commit in any AI-assisted session — which in this repo is
effectively all of them. No exceptions stated.

Respected by: [[sync-and-ship-a-work-session]].
