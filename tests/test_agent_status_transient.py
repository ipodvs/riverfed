"""A transient provider-probe failure (timeout/spawn error, common right after
a heavy ingest) must not flip a known-good agent to 'not ready' and cache that
false negative — that greyed out the 'Run review now' button for ~20s after a
successful ingest. A REAL logout (clean, non-exception negative) must still
propagate.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "wiki" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import agent_runner  # noqa: E402


class _Probe:
    """Swap agent_runner.probe with a scripted sequence of behaviours."""

    def __init__(self, script) -> None:
        self._script = list(script)
        self._saved = None

    def __enter__(self):
        self._saved = agent_runner.probe
        agent_runner.resolve_agent_bin = lambda provider="claude-code": "/usr/bin/true"

        def fake(args, *, timeout=10, provider="claude-code"):
            behaviour = self._script.pop(0)
            if behaviour == "timeout":
                raise subprocess.TimeoutExpired(cmd=str(args), timeout=timeout)
            if isinstance(behaviour, tuple):
                rc, out = behaviour
                return subprocess.CompletedProcess(args, rc, out, "")
            raise AssertionError(f"unexpected behaviour {behaviour!r}")

        agent_runner.probe = fake
        agent_runner._STATUS_CACHE.clear()
        return self

    def __exit__(self, *exc):
        agent_runner.probe = self._saved


class AgentStatusTransient(unittest.TestCase):
    def _logged_in_pair(self):
        # --version ok, then auth status JSON with loggedIn true
        return [(0, "claude 2.1.202"), (0, '{"loggedIn": true, "email": "a@b.co"}')]

    def test_transient_timeout_keeps_last_known_good(self) -> None:
        script = self._logged_in_pair() + ["timeout"]  # good probe, then a --version timeout
        with _Probe(script):
            good = agent_runner.status("claude-code")
            self.assertTrue(good["ok"] and good["logged_in"])
            # a transient blip must NOT report not-ready
            blip = agent_runner.status("claude-code")
            self.assertTrue(blip["logged_in"], "transient timeout wrongly flipped to not-ready")
            self.assertEqual(blip["account"], "a@b.co")

    def test_transient_blip_is_not_cached(self) -> None:
        # good, then timeout, then good again — the blip in the middle must not
        # be cached, so a ttl read right after still serves good.
        script = self._logged_in_pair() + ["timeout"] + self._logged_in_pair()
        with _Probe(script):
            agent_runner.status("claude-code")
            agent_runner.status("claude-code")             # transient
            after = agent_runner.status("claude-code", ttl=60)
            self.assertTrue(after["logged_in"])

    def test_real_logout_still_propagates(self) -> None:
        # good first, then a CLEAN 'not logged in' (loggedIn false, no exception)
        script = self._logged_in_pair() + [(0, "claude 2.1.202"), (0, '{"loggedIn": false}')]
        with _Probe(script):
            agent_runner.status("claude-code")
            out = agent_runner.status("claude-code")
            self.assertFalse(out["logged_in"], "a real logout must still be reported")


if __name__ == "__main__":
    unittest.main()
