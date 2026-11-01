"""agent_runner.run() must enforce a hard wall-clock timeout and kill the
whole process tree — in BOTH run modes.

Regression for the 2026-08-05 hang: a claude child idled 41 min at 5s CPU
with stdout still open. Streaming mode's `for line in proc.stdout` blocks
while the pipe is open, so the old `proc.wait(timeout=)` (only reached after
EOF) never capped the hang and the per-transcript timeout never fired.

These tests stand in a Python "agent" for the real CLI: it emits one line,
spawns a grandchild that sleeps, then sleeps itself with stdout open — the
exact shape that used to hang forever.
"""
from __future__ import annotations

import os
import signal
import sys
import time
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "wiki" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import agent_runner  # noqa: E402

# A fake agent: print a grandchild PID line, fork a long-sleeping grandchild,
# then hang with stdout OPEN (never EOF). stdout is line-buffered/flushed so
# the parent sees the marker before the hang.
_FAKE_AGENT = r"""
import os, sys, time
r, w = os.pipe()
pid = os.fork()
if pid == 0:
    os.close(w)
    time.sleep(300)          # grandchild: outlives parent unless the tree is killed
    os._exit(0)
os.close(r)
sys.stdout.write("GRANDCHILD %d\n" % pid)
sys.stdout.flush()
time.sleep(300)              # parent hangs with stdout still open (no EOF)
"""


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class _FakeProvider:
    """Patch agent_runner so run() launches our fake agent instead of a CLI."""

    def __init__(self) -> None:
        self._saved: dict = {}

    def __enter__(self):
        self._saved = {
            "resolve_agent_bin": agent_runner.resolve_agent_bin,
            "_check_provider": agent_runner._check_provider,
            "scrub_env": agent_runner.scrub_env,
            "builder": agent_runner._ARGV_BUILDERS.get("claude-code"),
        }
        agent_runner.resolve_agent_bin = lambda provider="claude-code": sys.executable
        agent_runner._check_provider = lambda provider: None
        agent_runner.scrub_env = lambda provider="claude-code": os.environ.copy()
        agent_runner._ARGV_BUILDERS["claude-code"] = (
            lambda bin_path, cwd, add_dirs, allowed_tools, prompt_file=None:
            [bin_path, "-c", _FAKE_AGENT]
        )
        return self

    def __exit__(self, *exc):
        agent_runner.resolve_agent_bin = self._saved["resolve_agent_bin"]
        agent_runner._check_provider = self._saved["_check_provider"]
        agent_runner.scrub_env = self._saved["scrub_env"]
        agent_runner._ARGV_BUILDERS["claude-code"] = self._saved["builder"]


@unittest.skipIf(sys.platform == "win32", "POSIX process-group semantics")
class AgentRunnerTimeout(unittest.TestCase):
    def _grandchild_pid(self, output: str) -> int:
        for line in output.splitlines():
            if line.startswith("GRANDCHILD "):
                return int(line.split()[1])
        self.fail(f"fake agent never emitted its grandchild PID; got: {output!r}")

    def test_streaming_mode_caps_a_mid_stream_hang(self) -> None:
        lines: list[str] = []
        with _FakeProvider():
            t0 = time.time()
            res = agent_runner.run(
                "go", cwd=_SCRIPTS, timeout=3, on_line=lines.append,
            )
            elapsed = time.time() - t0

        self.assertTrue(res.timed_out, "hung stream must report timed_out")
        self.assertLess(elapsed, 15, f"timeout(3s) not enforced — took {elapsed:.1f}s")
        gc = self._grandchild_pid("\n".join(lines))
        time.sleep(0.5)
        self.assertFalse(_alive(gc), f"grandchild {gc} survived — tree not killed")

    def test_capture_mode_caps_a_hang_and_kills_tree(self) -> None:
        with _FakeProvider():
            t0 = time.time()
            res = agent_runner.run("go", cwd=_SCRIPTS, timeout=3)  # no on_line
            elapsed = time.time() - t0

        self.assertTrue(res.timed_out)
        self.assertLess(elapsed, 15, f"timeout(3s) not enforced — took {elapsed:.1f}s")
        gc = self._grandchild_pid(res.output)
        time.sleep(0.5)
        self.assertFalse(_alive(gc), f"grandchild {gc} survived — tree not killed")


if __name__ == "__main__":
    unittest.main()
