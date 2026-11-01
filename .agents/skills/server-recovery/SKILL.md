---
name: server-recovery
description: >
  Diagnose and recover the Riverfed local server and ingest pipeline.
  Use whenever the user says "site is down", "can't connect", "server's not
  responding", "ingest is stuck", "it's loading forever", "spinning", or the
  page won't load. Covers restarting the detached server, telling a genuinely
  hung ingest from one that already finished, and killing stuck processes
  SURGICALLY without touching the user's Codex session, the server, or
  their desktop app.
---

# Server & ingest recovery

The server runs detached (pythonw via `start.vbs`) on
`http://127.0.0.1:8765`. Work from evidence — most "stuck" reports are
actually a finished job whose browser fetch was dropped.

## 1. Is the server up?

```bash
netstat -ano | grep ":8765 " | grep LISTENING      # is the port held?
curl -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 5 http://127.0.0.1:8765/
```

- **HTTP 200** → server is fine; the problem is elsewhere (browser, ingest).
- **No listener / HTTP 000** → server is down. Restart it:

```bash
wscript.exe start.vbs      # relaunch detached; wait ~3s, re-check the port
```

The server can go down on its own from a Windows sign-out, sleep, or closing
the launching session. A clean restart (no crash trace in `server.log`) is
usually all it needs.

## 2. Is the ingest actually stuck, or already done?

A finished ingest can leave the UI banner spinning. **Check for a live
process before assuming a hang:**

```bash
# any ingest.py / promote_backlog.py running, and for how long?
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*ingest.py*' -or \$_.CommandLine -like '*promote*' } | Select-Object ProcessId,@{N='RunMin';E={[math]::Round(((Get-Date)-\$_.CreationDate).TotalMinutes,1)}}"
```

- **No process** → the ingest **finished**. The banner is stale — tell the
  user to refresh; then verify with `py -3.13 wiki\scripts\pending.py`.
  (Remember: pending is matched by video id, so a video may be "done" even if
  it lingered in the list — see the convert-and-ingest skill.)
- **A process, but no agent-CLI child (`Codex` / `codex`) after ~2 min** →
  likely hung. Confirm no wiki files changed recently, then kill it (step 3).
  Note: both CLIs can take 30–60 s just to spawn, so don't judge a hang
  before that. (Which agent ran it: the job log's `$ Codex -p ...` /
  `$ codex exec ...` line, or `--provider` in the ingest argv.)

## 3. Kill a stuck ingest — SURGICALLY

Only kill the project's own `ingest.py` / `promote_backlog.py` trees by their
**specific PID**. NEVER kill:
- the user's Codex session (`...\Codex\...\Codex.exe`),
- the user's Codex sessions / the Codex **Desktop** app
  (`...\OpenAI\Codex\...\codex.exe`),
- the server (`pythonw.exe ... server.py`),
- the Codex **Desktop** app (`WindowsApps\...\Codex.exe` renderers).

```bash
taskkill //PID <ingest_pid> //T //F     # //T kills its child tree too
```

Killing frees the lock (the server's `subprocess.run` returns) and the UI
unblocks. A killed mid-run ingest can leave the wiki mid-edit (e.g. a source
page deleted before recreate) — recover with `git restore wiki/sources/<page>.md`.

## Prevention (already in place)

Ingest/review is **single-flight** (`_INGEST_LOCK` in server.py) — a second
"Ingest pending" / "Run review" click is rejected immediately, so concurrent
runs can't stack and deadlock anymore. If you still see *multiple* ingest.py,
something bypassed the UI (e.g. a CLI run) — kill the extras.

## References (read on demand)

- [`AGENTS.md`](../../../AGENTS.md) → "Known gotchas" — the canonical recovery
  recipe and the single-flight rationale
- `serve.cmd` (visible console for debugging) vs `start.vbs` (detached);
  `stop.cmd` to shut down
