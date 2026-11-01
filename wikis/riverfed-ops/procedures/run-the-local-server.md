---
slug: run-the-local-server
kind: procedure
trigger: "the app needs to be running at http://127.0.0.1:8765, or restarted"
last_updated: 2026-06-11
sources: [contributing-to-riverfed]
policies: []
tags: [wiki/procedures]
---

# Run the local server

## When to run this

You need the Riverfed app up (converter, wiki, Studio), or you
need to restart it.

## Steps

1. Start detached: run `start.vbs` — no console window; opens the
   browser at `http://127.0.0.1:8765`.
2. OR start with a visible terminal when you need live logs for
   debugging: run `serve.cmd` instead.
3. Shut it down with `stop.cmd` — works for either start method.

## Gotchas

- Pick `serve.cmd` when something is misbehaving — `start.vbs` gives you
  no console output to read.

## Done means

The browser reaches `http://127.0.0.1:8765`; `stop.cmd` cleanly stops
it.
