"""How the prompt reaches the agent CLI, per provider (A7 step 1).

Until A7 every provider took its prompt on stdin, so `run()` always piped
it. Grok cannot: `grok -p -` treats the `-` as a literal prompt, and the
only headless route in is `--prompt-file <path>`. `run()` therefore picks
a delivery mode from `PROMPT_DELIVERY` — and the file mode has a failure
shape stdin never had: prompt text left behind on disk.

These tests stand in a Python "agent" for the real CLI. They pin:
  - stdin providers are UNCHANGED (the A0 bar for step 1),
  - a file provider gets a readable path in argv and NO stdin to block on,
  - the temp file is unlinked on every exit path, timeout included.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

import _util  # noqa: F401
import agent_runner

# Reads the prompt off stdin, the way claude -p / codex exec - do.
_ECHO_STDIN = r"""
import sys
sys.stdout.write("GOT:%s\n" % sys.stdin.read().strip())
"""

# Reads the prompt from the path handed to it in argv, the way grok's
# --prompt-file does, and reports what stdin looked like.
_ECHO_FILE = r"""
import sys
path = sys.argv[1]
sys.stdout.write("PATH:%s\n" % path)
with open(path, encoding="utf-8") as fh:
    sys.stdout.write("GOT:%s\n" % fh.read().strip())
sys.stdout.write("STDIN:%r\n" % sys.stdin.read())
"""

# Never exits on its own: proves the temp file is removed on the timeout
# path too, not just after a clean return.
_HANG = r"""
import sys, time
sys.stdout.write("PATH:%s\n" % sys.argv[1])
sys.stdout.flush()
time.sleep(300)
"""

PROMPT = "ingest this transcript"


class _FakeProvider:
    """Register a throwaway provider whose 'CLI' is this interpreter."""

    def __init__(self, provider: str, delivery: str, code: str) -> None:
        self.provider, self.delivery, self.code = provider, delivery, code

    def __enter__(self):
        self._saved_resolve = agent_runner.resolve_agent_bin
        self._saved_scrub = agent_runner.scrub_env
        self._saved_check = agent_runner._check_provider
        agent_runner.resolve_agent_bin = lambda provider=None: sys.executable
        agent_runner.scrub_env = lambda provider=None: os.environ.copy()
        agent_runner._check_provider = lambda provider: None
        agent_runner.PROMPT_DELIVERY[self.provider] = self.delivery
        agent_runner._ARGV_BUILDERS[self.provider] = (
            lambda bin_path, cwd, add_dirs, allowed_tools, prompt_file=None:
            [bin_path, "-c", self.code]
            + ([prompt_file] if prompt_file else [])
        )
        return self

    def __exit__(self, *exc):
        agent_runner.resolve_agent_bin = self._saved_resolve
        agent_runner.scrub_env = self._saved_scrub
        agent_runner._check_provider = self._saved_check
        agent_runner.PROMPT_DELIVERY.pop(self.provider, None)
        agent_runner._ARGV_BUILDERS.pop(self.provider, None)


def _field(output: str, name: str) -> str:
    m = re.search(rf"^{name}:(.*)$", output, flags=re.MULTILINE)
    assert m, f"fake agent never emitted {name}: — got {output!r}"
    return m.group(1)


class PromptDelivery(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="riverfed-delivery-test-"))
        self.addCleanup(lambda: [p.unlink() for p in self.tmp.glob("*")]
                        and None)
        self.addCleanup(self.tmp.rmdir)

    # ---- the A0 bar: stdin providers are untouched -------------------

    def test_pre_a7_providers_still_deliver_on_stdin(self) -> None:
        """The A0 bar for A7 step 1: claude-code and codex must not have
        been moved onto file delivery by the refactor that introduced it.
        Named explicitly rather than looped over PROVIDERS — a provider
        added later is allowed to choose either mode."""
        for provider in ("claude-code", "codex"):
            self.assertEqual(agent_runner.PROMPT_DELIVERY[provider], "stdin",
                             f"{provider} changed delivery mode")

    def test_stdin_delivery_capture_mode(self) -> None:
        with _FakeProvider("fake-stdin", "stdin", _ECHO_STDIN):
            res = agent_runner.run(PROMPT, cwd=self.tmp, timeout=30,
                                   provider="fake-stdin")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(_field(res.output, "GOT"), PROMPT)

    def test_stdin_delivery_streaming_mode(self) -> None:
        lines: list[str] = []
        with _FakeProvider("fake-stdin", "stdin", _ECHO_STDIN):
            res = agent_runner.run(PROMPT, cwd=self.tmp, timeout=30,
                                   on_line=lines.append, provider="fake-stdin")
        self.assertEqual(res.returncode, 0, res.output)
        self.assertEqual(_field("\n".join(lines), "GOT"), PROMPT)

    # ---- file delivery -----------------------------------------------

    def test_file_delivery_hands_the_agent_a_readable_path(self) -> None:
        with _FakeProvider("fake-file", "file", _ECHO_FILE):
            res = agent_runner.run(PROMPT, cwd=self.tmp, timeout=30,
                                   provider="fake-file")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(_field(res.output, "GOT"), PROMPT)

    def test_file_delivery_gives_the_child_no_stdin_to_block_on(self) -> None:
        """DEVNULL, not an open pipe: a CLI that reads stdin at startup must
        see EOF immediately rather than wait for a write that never comes."""
        with _FakeProvider("fake-file", "file", _ECHO_FILE):
            res = agent_runner.run(PROMPT, cwd=self.tmp, timeout=30,
                                   provider="fake-file")
        self.assertEqual(_field(res.output, "STDIN"), "''")

    def test_file_delivery_cleans_up_after_a_clean_run(self) -> None:
        with _FakeProvider("fake-file", "file", _ECHO_FILE):
            res = agent_runner.run(PROMPT, cwd=self.tmp, timeout=30,
                                   provider="fake-file")
        leaked = Path(_field(res.output, "PATH"))
        self.assertFalse(leaked.exists(),
                         f"prompt file survived a clean run: {leaked}")

    def test_file_delivery_cleans_up_after_a_timeout(self) -> None:
        lines: list[str] = []
        with _FakeProvider("fake-file", "file", _HANG):
            res = agent_runner.run(PROMPT, cwd=self.tmp, timeout=3,
                                   on_line=lines.append, provider="fake-file")
        self.assertTrue(res.timed_out)
        leaked = Path(_field("\n".join(lines), "PATH"))
        self.assertFalse(leaked.exists(),
                         f"prompt file survived a timeout: {leaked}")


if __name__ == "__main__":
    unittest.main()
