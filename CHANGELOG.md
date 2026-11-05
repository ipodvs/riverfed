# Changelog

What has landed on `main`, newest first, grouped by feature with the file
paths you'd touch to use or extend each piece.

When you `sync.cmd` / `./sync.command`, this file tells you everything you
missed.

---

## How to read this changelog as PFreitas91

Updated 2026-11-05. The newest block is **the server no longer
restarts itself every 50 minutes** (and stops opening a browser window
each time). It changed Python: restart the server once (Mac:
`launchctl kickstart -k "gui/$(id -u)/com.riverfed.server"`; Windows:
`stop.cmd`, then `start.vbs`). Before that came **the first public
release**. The project now lives at `github.com/ipodvs/riverfed`, open source under
MIT, with a fresh Git history. Your old checkout and its remote are
retired. The one-time move (re-clone, rename the vault folder and the
Whisper cache, re-install the watchdog) is written up in the README of
the old private repo, so the previous setup doesn't have to be described
here. After the move everything works as before, under the new names:
`~/RiverfedVaults`, `RIVERFED_*` env vars, the `com.riverfed.*`
LaunchAgents on a Mac and the `RiverfedWatchdog` task on Windows.

Each block below says whether it changed Python (restart the server) or
dependencies (re-run `./setup.sh` or `pip install -r requirements.txt`).
See **"Riverfed goes public"** below.

---

## 🛟 No more crash loop or surprise browser windows (2026-11-05)

**The symptom.** Since 2026-10-30 the server died about every 50 minutes
(exit -9, no traceback), the watchdog restarted it, and every restart
opened a new browser window. The channel watcher had stopped finishing
sweeps, so new uploads were converted slowly or not at all.

**The cause.** Background jobs ran in the server's own process group.
When the watcher sweep hit its 45-minute cap, the "kill the whole job
tree" step killed that group, and the server with it. The sweep kept
hitting the cap because the same slow videos were retried first every
time.

**What changed.**

- **Jobs get their own process group** (`wiki/scripts/_proc.py`). A
  timeout now kills the job and everything it started, never the server.
  `kill_tree` also refuses to kill the caller's own group.
- **The browser opens only for a person** (`server.py`
  `should_open_browser`). It opens when you start the server from a
  terminal. launchd, the watchdogs and `start.command` / `start.vbs`
  (which open the page themselves) no longer pop a window. Set
  `RIVERFED_NO_BROWSER=1` to turn it off from a terminal too.
- **Sweeps finish on their own** (`watcher.py`). A sweep stops starting
  conversions once the next one could run past 40 minutes and leaves the
  rest for the next sweep. A video that fails or times out three sweeps
  in a row is skipped, and failing videos are tried after new ones.
  Failure counts live in `subscriptions.json` under `failures`.
- Tests: `tests/test_proc_group_isolation.py`,
  `tests/test_browser_autoopen.py`, `tests/test_watcher_sweep_budget.py`.

Python changed: restart the server once. No dependency changes.

---

## 🌊 Riverfed goes public (2026-11-01)

**What it is.** Riverfed turns a YouTube link or any file into a
structured, Obsidian-compatible wiki and a Marp training deck, using the
agent CLI you are already logged in to (Claude Code, Codex or Grok).
Everything stays local: your knowledge bases are plain Markdown in git
repos you own.

**What changed for an existing install.**

- **One name everywhere.** Every identifier now carries the Riverfed
  name: the vault home `~/RiverfedVaults` (override
  `RIVERFED_VAULTS_DIR`), `RIVERFED_PORT`, `RIVERFED_WHISPER_MODEL` /
  `RIVERFED_WHISPER_DIR`, `RIVERFED_RUN_LIVE_WHISPER`, the LaunchAgents
  `com.riverfed.server` / `com.riverfed.watchdog`, the Windows task
  `RiverfedWatchdog`, the Whisper model cache
  (`~/Library/Caches/Riverfed/whisper.cpp` on a Mac,
  `~/.cache/riverfed/whisper.cpp` elsewhere) and the demo vault
  `wikis/riverfed-ops`.
- **Anki ids are new.** Studio's Anki export derives deck and note-type
  ids from new seeds, so a deck imported before this release is created
  once more instead of updated in place. Delete the old copy in Anki.
- **No API key in `.env.example`.** The pipeline authenticates through
  the agent CLI login. `ANTHROPIC_API_KEY` stays unset; a value would
  override the `claude` login.
- **License.** `LICENSE` (MIT).
- **README gallery.** The slide screenshots are re-rendered from the
  current AI Builders deck.

**Blast radius.** Python changed: restart the server after the move.
An install from before this release must rename its vault folder and
Whisper cache and re-install the watchdog once, or it will start with an
empty vault home and download the Whisper model again.

**Files:** `LICENSE`, `.env.example`, `server.py`, `local_whisper.py`,
`wiki/scripts/_wikis.py`, `wiki/scripts/studio_anki.py`,
`install-watchdog.*`, `uninstall-watchdog.*`, `watchdog.command`,
`setup.sh`, `wikis/riverfed-ops/`.
