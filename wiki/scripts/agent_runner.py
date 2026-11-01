#!/usr/bin/env python3
"""Provider layer for agent CLI invocations — A6 "bring your own agent".

Every script that shells out to an agent CLI goes through this module
instead of building its own subprocess call: ingest.py, promote_backlog.py,
the six studio_*.py generators, and server.py's status probes. Three
providers ship: ``claude-code`` (the default; behavior byte-identical to
the per-script invocations A6 step 1 replaced), ``codex`` (A6 step 2 —
``codex exec`` with a feature-probed flag set, so CLI drift degrades
gracefully instead of breaking), and ``grok`` (A7 — a Claude-Code-shaped
CLI: it reads CLAUDE.md and .claude/skills natively and can SEE images
through its own read_file, but it cannot take a prompt on stdin).

What this module owns (the MECHANICS):
  - binary resolution (Windows .CMD via _agent_bin; CLAUDE_BIN /
    CODEX_BIN / GROK_BIN overrides)
  - per-provider argv construction:
      claude-code: ``-p --dangerously-skip-permissions --add-dir ...
                   [--allowedTools ...]``
      codex:       ``exec - --sandbox workspace-write [--image ...] [--cd ...]
                   [--skip-git-repo-check] [--ephemeral] --add-dir ...``
                   — each optional flag only if ``codex exec --help``
                   advertises it (probed once per process).
                   ``allowed_tools`` is Claude vocabulary; codex governs
                   via its sandbox, so the param is ignored there.
      grok:        ``--prompt-file F --permission-mode bypassPermissions
                   --sandbox off --no-leader --cwd ...`` — no flag probe
                   (its surface is stable and Claude-compatible); both
                   ``add_dirs`` and ``allowed_tools`` are ignored, the
                   first because grok sandboxes nothing by default and
                   the second because its tool IDs are its own.
  - prompt delivery, per provider (``PROMPT_DELIVERY``): "stdin" for
    claude/codex (claude.CMD truncates argv past ~8 KB; codex takes
    ``-`` to read stdin), "file" for a CLI that cannot read its prompt
    from stdin — the prompt is written to a temp file whose path the
    argv builder receives, and unlinked on every exit path
  - nested-session env scrub (per-provider var list)
  - CREATE_NO_WINDOW so pythonw.exe parents don't flash consoles
  - the two run modes: streamed (ingest/promote — line callback, stderr
    merged, prompt written from a worker thread to dodge the Windows
    write/read deadlock, timeout on wait() after stdout EOF) and captured
    (studio scripts — subprocess.run(input=...), timeout on the whole run)
  - probes (``--version`` / auth: capture_output, text=True with locale
    encoding, timeout 10, inherited env)
  - provider selection: status() per provider (with an optional TTL
    cache for the server's 10 s polls) and resolve_provider() — "auto"
    walks PROVIDERS in order (claude-code, then grok, then codex); an
    EXPLICIT provider that is not ready hard-fails with its login hint,
    never silently falls back.

What stays with CALLERS: exit codes, error message wording, stdout
contracts (RENDERED:/SKILL: lines), and echo prefixes for streamed lines.
Scripts verify results by FILESYSTEM, not transcript — that invariant is
what makes providers swappable.

Error contract: FileNotFoundError propagates from run()/probe() so each
caller keeps its own not-on-PATH handling; timeouts never raise — both
run modes report them uniformly via RunResult.timed_out.
"""
from __future__ import annotations

import json
import re
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
import _agent_bin  # noqa: E402
from _wikis import _env_file_value  # noqa: E402

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _new_session_kwargs() -> dict:
    """Popen kwargs that make the child lead its own process group / session
    so the WHOLE tree (agent CLI + any tool subprocesses it spawns, e.g.
    claude's Bash tool) can be killed together on timeout. POSIX: setsid via
    start_new_session, so os.killpg reaches every descendant. Windows: nothing
    special — taskkill /T walks the child tree by PID in _kill_tree()."""
    if sys.platform == "win32":
        return {}
    return {"start_new_session": True}


def _kill_tree(proc: subprocess.Popen) -> None:
    """Force-kill ``proc`` and every process it spawned. A plain proc.kill()
    only reaps the direct child, orphaning grandchildren (a hung claude that
    forked a tool subprocess) — those keep the port/model busy and show up as
    'ingest still running'. POSIX kills the process group; Windows uses
    taskkill /T. Idempotent and best-effort — never raises."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=NO_WINDOW)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass
    # Fallback: if the group kill missed the leader, kill it directly.
    try:
        proc.kill()
    except (ProcessLookupError, OSError):
        pass

DEFAULT_PROVIDER = "claude-code"
# Auto-resolution order: claude-code preferred, then grok, then codex.
# Grok sits ahead of codex deliberately (decided 2026-08-15): the usual
# reason auto falls through is a Claude usage limit mid-queue, and grok
# can SEE frames (its read_file returns image pixels) while codex only
# gets OCR text — so the failover keeps deep visual capture instead of
# silently degrading it.
PROVIDERS: tuple[str, ...] = ("claude-code", "grok", "codex")

DISPLAY_NAMES = {"claude-code": "Claude Code", "codex": "Codex",
                 "grok": "Grok"}
LOGIN_HINTS = {"claude-code": "claude auth login", "codex": "codex login",
               "grok": "grok login"}
# Short command labels for log/echo lines ("$ claude -p ...").
CMD_LABELS = {"claude-code": "claude -p", "codex": "codex exec",
              "grok": "grok -p"}

_SCRUB_VARS: dict[str, tuple[str, ...]] = {
    # Claude Code refuses to launch nested inside another Claude Code
    # session; scrub the markers so scripts work from a Claude terminal.
    "claude-code": ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_PROJECT_DIR"),
    # Codex marks the shell env of commands it sandboxes; scrub so a
    # pipeline started from inside a Codex session doesn't inherit them.
    "codex": ("CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED"),
    # Grok publishes no nested-session marker, but two of its env vars
    # would silently reshape a pipeline run: GROK_SANDBOX picks a sandbox
    # profile (`workspace` confines writes to cwd + /tmp, which would
    # break every vault write), and GROK_AGENT swaps the agent profile
    # out from under us. The argv pins --sandbox off explicitly too;
    # this is the belt to that pair of braces.
    "grok": ("GROK_SANDBOX", "GROK_AGENT"),
}

# How each provider's CLI wants the prompt handed to it.
#   "stdin" — written to the child's stdin. Preferred: no prompt ever
#             touches the filesystem, and it dodges the ~8 KB argv
#             truncation of claude.CMD on Windows.
#   "file"  — written to a temp file whose path is passed in argv (the
#             builder receives it). For CLIs that simply cannot read a
#             prompt from stdin; the file is unlinked on every exit
#             path, timeouts included.
PROMPT_DELIVERY: dict[str, str] = {
    "claude-code": "stdin",
    "codex": "stdin",
    # grok has no stdin route at all: `grok -p -` treats the "-" as a
    # literal prompt. --prompt-file is the only headless way in.
    "grok": "file",
}


def _check_provider(provider: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError(f"unknown agent provider: {provider!r} "
                         f"(available: {', '.join(PROVIDERS)})")


def resolve_agent_bin(provider: str = DEFAULT_PROVIDER) -> str | None:
    """Absolute path of the provider's CLI, or None if not installed."""
    _check_provider(provider)
    return _agent_bin.resolve_agent_bin(provider)


def scrub_env(provider: str = DEFAULT_PROVIDER) -> dict[str, str]:
    """os.environ minus the provider's nested-session markers."""
    _check_provider(provider)
    env = os.environ.copy()
    for k in _SCRUB_VARS[provider]:
        env.pop(k, None)
    return env


@dataclass
class RunResult:
    """Outcome of one agent run.

    output: combined stream in streaming mode (stderr merged, joined
            non-empty lines); stdout in capture mode.
    stderr: capture mode only ("" when streaming — merged into output).
    error:  human-readable failure ("timed out after Ns"), None on success.
    """
    returncode: int
    output: str
    stderr: str
    elapsed_seconds: float
    error: str | None = None
    timed_out: bool = False


def _build_claude_argv(bin_path: str, cwd: Path | str,
                       add_dirs: Sequence[Path | str],
                       allowed_tools: str | None,
                       prompt_file: str | None = None) -> list[str]:
    # prompt_file is unused: claude takes its prompt on stdin.
    argv = [bin_path, "-p", "--dangerously-skip-permissions"]
    # Pin the pipeline's Claude model independently of the user's
    # interactive default (~/.claude settings.json), which -p otherwise
    # inherits silently. Real env var wins, then .env — same resolution
    # as RIVERFED_VAULTS_DIR, so server jobs and direct CLI runs agree.
    # Two modes: a family alias ("opus") tracks the newest model of that
    # tier and is the house policy (one tier below frontier — needs a
    # current CLI: 2.1.71's stale table resolved opus to 4-6, 2.1.202
    # resolves to 4-8); a full id (claude-opus-4-8) is a hard pin.
    model = (os.environ.get("CLAUDE_MODEL", "").strip()
             or _env_file_value("CLAUDE_MODEL"))
    if model:
        argv.extend(["--model", model])
    for d in add_dirs:
        argv.extend(["--add-dir", str(d)])
    if allowed_tools:
        argv.extend(["--allowedTools", allowed_tools])
    return argv


_CODEX_EXEC_FLAGS: set[str] | None = None


def _codex_exec_flags() -> set[str]:
    """Flags advertised by `codex exec --help`, probed once per process.

    The Codex CLI moves fast — build argv only from flags that exist
    (the roadmap's explicit correction: never hardcode from the plan).
    """
    global _CODEX_EXEC_FLAGS
    if _CODEX_EXEC_FLAGS is None:
        try:
            help_proc = probe(["exec", "--help"], provider="codex", timeout=20)
            _CODEX_EXEC_FLAGS = set(
                re.findall(r"--[a-z][a-z-]*", help_proc.stdout or ""))
        except Exception:
            _CODEX_EXEC_FLAGS = set()
    return _CODEX_EXEC_FLAGS


def _build_codex_argv(bin_path: str, cwd: Path | str,
                      add_dirs: Sequence[Path | str],
                      allowed_tools: str | None,
                      prompt_file: str | None = None) -> list[str]:
    # prompt_file is unused: `codex exec -` reads its prompt from stdin.
    flags = _codex_exec_flags()
    if "--sandbox" not in flags:
        raise RuntimeError(
            "this codex CLI does not advertise --sandbox in `codex exec "
            "--help`; refusing to run agent tasks without a sandbox policy")
    argv = [bin_path, "exec", "-", "--sandbox", "workspace-write"]
    # Tier-policy twin of CLAUDE_MODEL: pin the codex model explicitly
    # (e.g. the sub-frontier tier once GPT-5.6's moon/earth/sun tiers
    # land); unset = the user's ~/.codex/config.toml default. An explicit
    # pin the CLI can't honor fails loudly — never silently.
    model = (os.environ.get("CODEX_MODEL", "").strip()
             or _env_file_value("CODEX_MODEL"))
    if model:
        if "--model" not in flags:
            raise RuntimeError(
                "CODEX_MODEL is set but this codex CLI does not advertise "
                "--model in `codex exec --help`")
        argv.extend(["--model", model])
    if "--cd" in flags:
        argv.extend(["--cd", str(cwd)])
    if "--skip-git-repo-check" in flags:
        # Vault-home vaults are their own repos, but scratch/staging dirs
        # and fresh scaffolds may not be — don't let codex refuse them.
        argv.append("--skip-git-repo-check")
    if "--ephemeral" in flags:
        # Pipeline runs shouldn't pile up in the user's session history.
        argv.append("--ephemeral")
    if add_dirs:
        if "--add-dir" not in flags:
            raise RuntimeError(
                "this codex CLI lacks --add-dir; cannot grant the vault "
                "write access outside the workspace")
        for d in add_dirs:
            argv.extend(["--add-dir", str(d)])
    # allowed_tools intentionally unused: Claude-specific vocabulary.
    return argv


def _build_grok_argv(bin_path: str, cwd: Path | str,
                     add_dirs: Sequence[Path | str],
                     allowed_tools: str | None,
                     prompt_file: str | None = None) -> list[str]:
    """Grok is a Claude-Code-shaped CLI, so this is the shortest builder
    of the three — but three of its flags are load-bearing in ways the
    other providers' aren't (probed on grok 1.0.3, 2026-08-15).
    """
    if not prompt_file:
        raise RuntimeError("grok needs --prompt-file; run() must deliver "
                           "the prompt as a file (PROMPT_DELIVERY)")
    argv = [bin_path, "--prompt-file", prompt_file,
            # The --dangerously-skip-permissions twin.
            "--permission-mode", "bypassPermissions",
            # Grok's sandbox is OFF by default, which is exactly why no
            # --add-dir equivalent is needed: the agent can already write
            # the vault dirs outside cwd. But --sandbox also reads
            # GROK_SANDBOX from the environment, and the `workspace`
            # profile confines writes to cwd + /tmp — which would break
            # every vault write with no error we'd recognise. Pinning it
            # here makes the guarantee independent of the user's shell.
            "--sandbox", "off",
            # Grok can attach to a shared leader process instead of
            # running the agent itself ([cli] use_leader). Under leader
            # mode the real worker lives OUTSIDE our process tree, so
            # _kill_tree() would reap a client and leave it running —
            # voiding the wall-clock timeout that the 2026-08-05 41-min
            # hang fix exists to enforce. Off by default; pin it anyway.
            "--no-leader",
            "--cwd", str(cwd)]
    # Tier-policy twin of CLAUDE_MODEL / CODEX_MODEL. Unset = grok's own
    # default (grok-4.7 on grok 1.0.41). Deliberately NOT defaulted to a
    # "one tier below frontier" pin the way CLAUDE_MODEL is: grok-4.7,
    # grok-4.6, and grok-4.5 are versions, not tiers, so there is no
    # ladder to hold.
    model = (os.environ.get("GROK_MODEL", "").strip()
             or _env_file_value("GROK_MODEL"))
    if model:
        argv.extend(["--model", model])
    # add_dirs intentionally unused: with the sandbox off grok already
    # reads and writes everywhere the user can, so there is nothing to
    # grant. allowed_tools likewise — grok's tool IDs are its own
    # (run_terminal_cmd, search_replace, read_file), so mapping Claude's
    # vocabulary onto --allow would mislead more than it constrains.
    return argv


_ARGV_BUILDERS = {
    "claude-code": _build_claude_argv,
    "codex": _build_codex_argv,
    "grok": _build_grok_argv,
}

_CODEX_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _append_image_args(argv: list[str], provider: str,
                       image_paths: Sequence[Path | str]) -> list[str]:
    """Attach local images to Codex's initial prompt.

    Merely adding a frame directory with ``--add-dir`` lets Codex read the
    JPEG *bytes* from the filesystem, but does not put their pixels into the
    model's vision input.  ``codex exec --image`` is the required handoff.
    Claude callers keep using the Read tool, so image args are Codex-only.
    """
    if provider != "codex" or not image_paths:
        return argv
    if "--image" not in _codex_exec_flags():
        raise RuntimeError(
            "this codex CLI does not advertise --image; cannot pass captured "
            "video frames to the model")

    resolved: list[str] = []
    seen: set[Path] = set()
    for raw in image_paths:
        try:
            path = Path(raw).resolve(strict=True)
        except OSError as exc:
            raise ValueError(f"Codex image does not exist: {raw}") from exc
        if not path.is_file():
            raise ValueError(f"Codex image is not a file: {path}")
        if path.suffix.lower() not in _CODEX_IMAGE_SUFFIXES:
            raise ValueError(f"unsupported Codex image type: {path.suffix}")
        if path not in seen:
            seen.add(path)
            resolved.append(str(path))

    if not resolved:
        return argv
    return [*argv, "--image", *resolved]

# codex `exec` echoes the whole session to stdout — the prompt (a block after
# a bare `user` marker), every tool call, and full tool output (a file read
# can be thousands of lines). claude -p prints only the final message, and
# every downstream consumer of the streamed lines (job log tails, ingest
# stdout, the / status boxes) was sized for that quiet stream. Filter the
# codex stream down to something readable: drop the prompt echo, cap each
# output block, always pass block markers and error lines through. Applied
# to the on_line callback only — RunResult.output keeps the full stream.
_CODEX_BLOCK_MARKERS = {"user", "codex", "exec", "thinking"}
_CODEX_RESULT_PREFIXES = ("tokens used", "succeeded in", "exited with", "failed in")
_CODEX_MAX_BLOCK_LINES = 12


def _codex_line_filter(emit: Callable[[str], None]) -> Callable[[str], None]:
    state = {"in_prompt": False, "block_lines": 0}

    def fn(line: str) -> None:
        bare = line.strip()
        if bare in _CODEX_BLOCK_MARKERS:
            state["in_prompt"] = bare == "user"
            state["block_lines"] = 0
            emit(line + ("  (prompt echo omitted)" if bare == "user" else ""))
            return
        if bare.startswith(_CODEX_RESULT_PREFIXES):
            state["in_prompt"] = False
            state["block_lines"] = 0
            emit(line)
            return
        if "ERROR" in line:
            emit(line)
            return
        if state["in_prompt"]:
            return
        state["block_lines"] += 1
        if state["block_lines"] == _CODEX_MAX_BLOCK_LINES + 1:
            emit("... (long output trimmed)")
        if state["block_lines"] > _CODEX_MAX_BLOCK_LINES:
            return
        emit(line)

    return fn


def run(prompt: str, *, cwd: Path | str, timeout: int,
        add_dirs: Sequence[Path | str] = (),
        image_paths: Sequence[Path | str] = (),
        allowed_tools: str | None = None,
        on_line: Callable[[str], None] | None = None,
        provider: str = DEFAULT_PROVIDER) -> RunResult:
    """Run one agent task; the prompt reaches the CLI by whichever route
    that provider supports (``PROMPT_DELIVERY``: stdin, or a temp file
    named in argv).

    on_line given  -> streaming mode: each non-empty rstripped line of the
                      merged stdout+stderr stream is passed to the callback
                      as it arrives; `timeout` bounds wait() after EOF.
    on_line absent -> capture mode: blocking run, `timeout` bounds the
                      whole invocation; stdout/stderr captured separately.

    Raises FileNotFoundError if the provider CLI is missing (callers keep
    their own messaging). Timeouts return RunResult(timed_out=True).
    """
    _check_provider(provider)
    bin_path = resolve_agent_bin(provider)
    if not bin_path:
        raise FileNotFoundError(f"{provider} CLI not found on PATH")

    # A file-delivery provider needs its prompt on disk BEFORE argv is
    # built — the builder puts that path in the command line. Written
    # here, unlinked in the finally below so no exit path (success,
    # timeout, or a builder that raises) leaves prompt text in the
    # temp dir.
    delivery = PROMPT_DELIVERY.get(provider, "stdin")
    prompt_file: str | None = None
    if delivery == "file":
        fd, prompt_file = tempfile.mkstemp(prefix="riverfed-prompt-",
                                           suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(prompt)
    # stdin providers get the prompt piped in; file providers get DEVNULL,
    # so a CLI that reads stdin at startup sees EOF instead of blocking on
    # a pipe nobody will ever write to.
    stdin_prompt = prompt if delivery == "stdin" else None

    try:
        argv = _ARGV_BUILDERS[provider](bin_path, cwd, add_dirs,
                                        allowed_tools, prompt_file)
        argv = _append_image_args(argv, provider, image_paths)
        env = scrub_env(provider)
        t0 = time.time()

        if on_line is None:
            return _run_captured(argv, stdin_prompt, cwd, env, timeout, t0)

        if provider == "codex":
            on_line = _codex_line_filter(on_line)
        return _run_streamed(argv, stdin_prompt, cwd, env, timeout,
                             on_line, t0)
    finally:
        if prompt_file:
            try:
                os.unlink(prompt_file)
            except OSError:
                pass


def _run_captured(argv: list[str], stdin_prompt: str | None,
                  cwd: Path | str, env: dict[str, str], timeout: int,
                  t0: float) -> RunResult:
    """Capture mode: blocking run, `timeout` bounds the whole invocation,
    stdout/stderr captured separately."""
    # Popen + communicate(timeout=) rather than subprocess.run so a
    # timeout kills the whole process TREE (subprocess.run's internal
    # timeout only reaps the direct child, orphaning grandchildren).
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE if stdin_prompt is not None
        else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        creationflags=NO_WINDOW,
        env=env,
        **_new_session_kwargs(),
    )
    try:
        out, err = proc.communicate(input=stdin_prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        return RunResult(-1, out or "", err or "", time.time() - t0,
                         error=f"timed out after {timeout}s",
                         timed_out=True)
    return RunResult(proc.returncode, out or "",
                     err or "", time.time() - t0)


def _run_streamed(argv: list[str], stdin_prompt: str | None,
                  cwd: Path | str, env: dict[str, str], timeout: int,
                  on_line: Callable[[str], None], t0: float) -> RunResult:
    """Streaming mode: each non-empty rstripped line of the merged
    stdout+stderr stream goes to `on_line` as it arrives."""
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE if stdin_prompt is not None
        else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        bufsize=1,
        creationflags=NO_WINDOW,
        env=env,
        **_new_session_kwargs(),
    )

    # Write the prompt in a worker thread so the caller's thread can stream
    # stdout without risking a write/read deadlock on Windows. File-delivery
    # providers have no stdin to write, so they skip the thread entirely.
    sender: threading.Thread | None = None
    if stdin_prompt is not None:
        def _send_prompt() -> None:
            try:
                assert proc.stdin is not None
                proc.stdin.write(stdin_prompt)
                proc.stdin.close()
            except Exception:
                pass

        sender = threading.Thread(target=_send_prompt, daemon=True)
        sender.start()

    # Hard wall-clock deadline over the ENTIRE run. Critical: `for line in
    # proc.stdout` blocks as long as the pipe stays open, so a hung agent that
    # stops emitting but never closes stdout (never reaches EOF) would hang the
    # reader forever — proc.wait(timeout=) below is only reached AFTER EOF, so
    # it can't cap a mid-stream hang. This timer fires regardless of stream
    # state, kills the tree (which closes the pipe → the loop ends), and flags
    # the timeout. (Real 2026-08-05 hang: a claude child idled 41 min at 5s CPU
    # with stdout open; the per-transcript timeout never fired.)
    timed_out = threading.Event()

    def _on_deadline() -> None:
        timed_out.set()
        _kill_tree(proc)

    deadline = threading.Timer(timeout, _on_deadline)
    deadline.daemon = True
    deadline.start()

    captured: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                captured.append(line)
                on_line(line)
        # Stream closed. The deadline timer still guards this wait, so a slow
        # exit after EOF can't hang us either.
        rc = proc.wait()
    finally:
        deadline.cancel()
        if sender is not None:
            sender.join(timeout=5)
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except OSError:
            pass

    if timed_out.is_set():
        return RunResult(-1, "\n".join(captured), "", time.time() - t0,
                         error=f"timed out after {timeout}s",
                         timed_out=True)

    return RunResult(rc, "\n".join(captured), "", time.time() - t0)


def probe(args: Sequence[str], *, timeout: int = 10,
          provider: str = DEFAULT_PROVIDER) -> subprocess.CompletedProcess:
    """Run a short CLI probe (e.g. ["--version"], ["auth", "status"]).

    Mirrors the original probes exactly: captured, text=True with the
    locale encoding, inherited env, CREATE_NO_WINDOW. Raises
    FileNotFoundError when the CLI is missing.
    """
    bin_path = resolve_agent_bin(provider)
    if not bin_path:
        raise FileNotFoundError(f"{provider} CLI not found on PATH")
    return subprocess.run(
        [bin_path, *args],
        capture_output=True, text=True, timeout=timeout,
        creationflags=NO_WINDOW,
    )


def _status_claude() -> dict:
    base = {"provider": "claude-code", "ok": False, "logged_in": False,
            "account": "", "version": ""}
    try:
        ver = probe(["--version"], provider="claude-code")
    except Exception as exc:
        # Timeout / transient spawn failure (common when the CLI is cold or
        # the box is busy right after an ingest) — NOT a real "not installed".
        return {**base, "error": f"--version probe failed: {exc}", "transient": True}
    if ver.returncode != 0:
        return {**base, "error": f"--version exit {ver.returncode}"}
    version = (ver.stdout or "").strip().splitlines()[0] if ver.stdout else ""
    try:
        auth = probe(["auth", "status"], provider="claude-code")
        data = json.loads(auth.stdout or "{}")
    except Exception as exc:
        return {**base, "ok": True, "version": version,
                "error": f"auth probe failed: {exc}", "transient": True}
    return {
        "provider": "claude-code",
        "ok": True,
        "logged_in": bool(data.get("loggedIn")),
        "account": data.get("email") or "",
        "version": version,
    }


def _status_codex() -> dict:
    base = {"provider": "codex", "ok": False, "logged_in": False,
            "account": "", "version": ""}
    try:
        ver = probe(["--version"], provider="codex")
    except Exception as exc:
        return {**base, "error": f"--version probe failed: {exc}", "transient": True}
    if ver.returncode != 0:
        return {**base, "error": f"--version exit {ver.returncode}"}
    version = (ver.stdout or "").strip().splitlines()[0] if ver.stdout else ""
    try:
        auth = probe(["login", "status"], provider="codex")
    except Exception as exc:
        return {**base, "ok": True, "version": version,
                "error": f"login probe failed: {exc}", "transient": True}
    text = ((auth.stdout or "") + (auth.stderr or "")).strip()
    logged_in = auth.returncode == 0 and "logged in" in text.lower() \
        and "not logged in" not in text.lower()
    # "Logged in using ChatGPT" -> account "ChatGPT"
    m = re.search(r"logged in (?:using|with)\s+(.+)", text,
                  flags=re.IGNORECASE)
    return {
        "provider": "codex",
        "ok": True,
        "logged_in": logged_in,
        "account": (m.group(1).strip() if m else ""),
        "version": version,
    }


def _status_grok() -> dict:
    base = {"provider": "grok", "ok": False, "logged_in": False,
            "account": "", "version": ""}
    try:
        ver = probe(["--version"], provider="grok")
    except Exception as exc:
        return {**base, "error": f"--version probe failed: {exc}", "transient": True}
    if ver.returncode != 0:
        return {**base, "error": f"--version exit {ver.returncode}"}
    version = (ver.stdout or "").strip().splitlines()[0] if ver.stdout else ""
    # There is no `grok login status`. `grok models` is the cheapest
    # command that needs a live credential (~0.7 s): it leads with
    # "You are logged in with <account>." and then lists the models.
    try:
        auth = probe(["models"], provider="grok", timeout=20)
    except Exception as exc:
        return {**base, "ok": True, "version": version,
                "error": f"models probe failed: {exc}", "transient": True}
    text = ((auth.stdout or "") + (auth.stderr or "")).strip()
    # "You are logged in with grok.com." -> account "grok.com": take the
    # whole line and drop only the sentence-ending period, since the
    # account itself contains dots.
    m = re.search(r"you are logged in with\s+([^\n]+)", text,
                  flags=re.IGNORECASE)
    return {
        "provider": "grok",
        "ok": True,
        "logged_in": auth.returncode == 0 and m is not None,
        "account": (m.group(1).strip().rstrip(".") if m else ""),
        "version": version,
    }


_STATUS_FNS = {"claude-code": _status_claude, "codex": _status_codex,
               "grok": _status_grok}
_STATUS_CACHE: dict[str, tuple[float, dict]] = {}


def status(provider: str = DEFAULT_PROVIDER, *, ttl: float = 0.0) -> dict:
    """Canonical provider status: {provider, ok, logged_in, account,
    version} (+ error when not ok, + display_name/login_hint always).

    ttl > 0 serves a cached answer newer than ttl seconds — the server
    polls /pending every 10 s and two providers would otherwise mean four
    subprocess probes per poll.
    """
    _check_provider(provider)
    if ttl > 0:
        hit = _STATUS_CACHE.get(provider)
        if hit and (time.time() - hit[0]) < ttl:
            return hit[1]
    if not resolve_agent_bin(provider):
        s = {"provider": provider, "ok": False, "logged_in": False,
             "account": "", "version": "",
             "error": f"{provider} CLI not found on PATH"}
    else:
        s = _STATUS_FNS[provider]()
    s["display_name"] = DISPLAY_NAMES[provider]
    s["login_hint"] = LOGIN_HINTS[provider]
    # A transient probe failure (timeout/spawn error — e.g. the CLI is cold
    # or the box is busy right after an ingest) must NOT flip a known-good
    # provider to "not ready" and then cache that false negative for the TTL:
    # that's what greyed out the "Run review now" button for ~20s after a
    # successful ingest. Serve the last-known-good status instead, and don't
    # cache the blip — so the next call re-probes and recovers immediately.
    # A real logout returns a clean (non-exception) negative and is NOT
    # marked transient, so genuine sign-outs still propagate.
    if s.pop("transient", False):
        prev = _STATUS_CACHE.get(provider)
        if prev and prev[1].get("ok") and prev[1].get("logged_in"):
            return prev[1]
        return s  # no good prior — report not-ready, but don't cache it
    _STATUS_CACHE[provider] = (time.time(), s)
    return s


def resolve_provider(requested: str | None = None, *,
                     ttl: float = 0.0) -> tuple[str | None, dict]:
    """Pick the provider for a task.

    requested None/"auto" -> first READY provider in PROVIDERS order
    (Claude preferred, Codex fallback). An explicit provider that is not
    ready returns (None, its_status) — the caller must surface the
    login_hint; NEVER silently fall back to another provider.

    Returns (provider_id or None, status_dict). When auto finds nothing,
    the dict carries {"error": ..., "providers": {id: status, ...}}.
    """
    req = (requested or "auto").strip().lower()
    if req in ("", "auto"):
        statuses: dict[str, dict] = {}
        for p in PROVIDERS:
            s = status(p, ttl=ttl)
            statuses[p] = s
            if s.get("ok") and s.get("logged_in"):
                return p, s
        return None, {
            "ok": False, "logged_in": False,
            "error": "no agent CLI is installed and logged in "
                     "(claude-code or codex)",
            "providers": statuses,
        }
    if req not in PROVIDERS:
        return None, {"ok": False, "logged_in": False,
                      "error": f"unknown agent provider: {requested!r} "
                               f"(available: auto, {', '.join(PROVIDERS)})"}
    s = status(req, ttl=ttl)
    if s.get("ok") and s.get("logged_in"):
        return req, s
    return None, s


def provider_arg_help(task: str = "run the task") -> str:
    """`--provider` help text for the CLI scripts, built from PROVIDERS so
    a fourth provider never has to be spelled into eight argparse calls
    (it was hardcoded in six studio scripts before A7)."""
    names = ", ".join(PROVIDERS[:-1]) + f", or {PROVIDERS[-1]}"
    order = " then ".join(DISPLAY_NAMES[p] for p in PROVIDERS)
    return (f"Agent CLI to {task}: auto (default), {names}. "
            f"Auto tries {order}; an explicit choice hard-fails with a "
            f"login hint when that CLI isn't ready, never silently "
            f"switching.")


def unavailable_message(pstatus: dict) -> str:
    """One-line human error for a failed resolve_provider() — names the
    problem and, when the CLI is installed but logged out, the login
    command. Shared by the CLI scripts and the server gate so the wording
    stays in one place."""
    err = pstatus.get("error") or (
        f"{pstatus.get('display_name', 'the agent CLI')} is installed "
        "but not logged in")
    hint = pstatus.get("login_hint")
    if hint and pstatus.get("ok") and not pstatus.get("logged_in"):
        err += f" — log in with: {hint}"
    return err


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent provider layer.")
    parser.add_argument("--status", action="store_true",
                        help="Print provider status as JSON (all providers "
                             "unless --provider is given).")
    parser.add_argument("--provider", default=None,
                        help="Provider id, or 'auto' to show the resolution.")
    cli_args = parser.parse_args()
    if cli_args.status:
        if cli_args.provider in (None, "all"):
            print(json.dumps({p: status(p) for p in PROVIDERS}, indent=2))
        elif cli_args.provider == "auto":
            chosen, s = resolve_provider("auto")
            print(json.dumps({"auto": chosen, "status": s}, indent=2))
        else:
            print(json.dumps(status(cli_args.provider), indent=2))
        sys.exit(0)
    parser.print_help()
