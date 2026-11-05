#!/usr/bin/env python3
"""Shared subprocess runner: line-streaming + hard timeout + process-TREE kill.

Why this exists: `subprocess.run(..., timeout=N)` on Windows kills only the
direct child on timeout. Our CLIs are .CMD shims (marp.CMD, claude.CMD) that
spawn node, which spawns chromium — so a timeout killed the shim and left the
real work orphaned. That's how a marp render once survived for 125 minutes
and silently blocked later renders. `run_streaming` kills the whole tree
(taskkill /T /F on Windows) so a timed-out job is actually dead.

Used by jobs.py (the server's async job queue) and studio_marp.py (renders).
"""
from __future__ import annotations

import subprocess
import sys
import threading


def kill_tree(pid: int, creationflags: int = 0) -> None:
    """Kill a process and all of its descendants."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            creationflags=creationflags,
        )
    else:
        import os
        import signal
        try:
            pgid = os.getpgid(pid)
        except Exception:
            return
        try:
            if pgid == os.getpgrp():
                # The child shares OUR group (it was not started by
                # run_streaming). killpg here would SIGKILL the caller too —
                # that is how a timed-out watcher sweep took the server down
                # every 50 minutes. Kill only the child.
                os.kill(pid, signal.SIGKILL)
            else:
                os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass


def run_streaming(
    cmd: list[str],
    *,
    cwd: str | None = None,
    timeout: float | None = None,
    on_line=None,
    env: dict | None = None,
    creationflags: int = 0,
    stdin_text: str | None = None,
) -> tuple[int, list[str], list[str], bool]:
    """Run `cmd`, streaming output line-by-line.

    Returns (returncode, stdout_lines, stderr_lines, timed_out).
    - on_line(line) is called for every line of BOTH streams as it arrives
      (stderr is where our scripts print progress; stdout carries the
      machine-parsed contract lines like RENDERED:<fmt>:<path>).
    - On timeout the entire process tree is killed and timed_out=True;
      whatever output arrived before the kill is still returned.
    """
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        env=env,
        creationflags=creationflags,
        # POSIX: the child leads its own process group, so kill_tree's killpg
        # reaches the child's descendants and never the caller.
        start_new_session=sys.platform != "win32",
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def _reader(stream, sink):
        try:
            for line in stream:
                line = line.rstrip("\r\n")
                sink.append(line)
                if on_line is not None and line.strip():
                    try:
                        on_line(line)
                    except Exception:
                        pass  # a broken progress callback must not kill the job
        except (ValueError, OSError):
            pass  # stream closed during kill
        finally:
            try:
                stream.close()
            except Exception:
                pass

    t_out = threading.Thread(target=_reader, args=(proc.stdout, stdout_lines), daemon=True)
    t_err = threading.Thread(target=_reader, args=(proc.stderr, stderr_lines), daemon=True)
    t_out.start()
    t_err.start()

    if stdin_text is not None:
        try:
            proc.stdin.write(stdin_text)
            proc.stdin.close()
        except (OSError, ValueError):
            pass

    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(proc.pid, creationflags=creationflags)
        proc.wait()

    t_out.join(timeout=10)
    t_err.join(timeout=10)
    return proc.returncode if proc.returncode is not None else -1, stdout_lines, stderr_lines, timed_out
