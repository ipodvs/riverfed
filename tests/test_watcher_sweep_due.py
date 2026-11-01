"""sweep_due_vaults() must be safe to call frequently (it's driven by both the
in-process cadence thread AND the launchd watchdog /watcher/tick): it sweeps a
subscribed vault only when its last sweep is older than the interval, debounces
in-flight sweeps, and never piles onto a busy convert lane. This is the
durability fix for the 2026-08-05 'auto-ingest went dark' incident.
"""
from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.argv = ["server.py"]
import server  # noqa: E402


def _iso(delta_sec: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_sec)).isoformat(timespec="seconds")


class SweepDue(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {
            "discover": server._wikis.discover_vaults,
            "load_subs": server._watcher.load_subs,
            "submit": server.submit_watcher_sweep,
            "lane_active": server.JOBS.lane_active,
        }
        server._last_sweep_attempt.clear()
        self.submitted: list[str] = []
        server.submit_watcher_sweep = lambda v: self.submitted.append(v.slug)
        server.JOBS.lane_active = lambda lane: None  # lane free
        server._wikis.discover_vaults = lambda: [types.SimpleNamespace(slug="wiki")]
        # default interval 360 min; make last_sweep configurable per test
        self._last_sweep = _iso(-10)  # 10s ago by default (recent)
        server._watcher.load_subs = lambda v: {
            "subscriptions": [{"id": "x"}], "last_sweep": self._last_sweep}

    def tearDown(self) -> None:
        server._wikis.discover_vaults = self._saved["discover"]
        server._watcher.load_subs = self._saved["load_subs"]
        server.submit_watcher_sweep = self._saved["submit"]
        server.JOBS.lane_active = self._saved["lane_active"]
        server._last_sweep_attempt.clear()

    def test_recent_sweep_is_skipped(self) -> None:
        self._last_sweep = _iso(-60)  # 1 min ago, interval is 6h
        self.assertEqual(server.sweep_due_vaults(), [])
        self.assertEqual(self.submitted, [])

    def test_overdue_sweep_fires(self) -> None:
        self._last_sweep = _iso(-7 * 3600)  # 7h ago > 6h interval
        self.assertEqual(server.sweep_due_vaults(), ["wiki"])
        self.assertEqual(self.submitted, ["wiki"])

    def test_never_swept_fires(self) -> None:
        self._last_sweep = None
        self.assertEqual(server.sweep_due_vaults(), ["wiki"])

    def test_inflight_debounce_prevents_double_submit(self) -> None:
        self._last_sweep = None  # overdue
        self.assertEqual(server.sweep_due_vaults(), ["wiki"])   # first fires
        # last_sweep hasn't updated yet (sweep still running); a second tick
        # must NOT resubmit within the in-flight grace window.
        self.assertEqual(server.sweep_due_vaults(), [])
        self.assertEqual(self.submitted, ["wiki"])

    def test_busy_convert_lane_defers(self) -> None:
        self._last_sweep = None  # overdue
        server.JOBS.lane_active = lambda lane: {"id": "abc", "kind": "convert"}
        self.assertEqual(server.sweep_due_vaults(), [])
        self.assertEqual(self.submitted, [])

    def test_force_ignores_interval(self) -> None:
        self._last_sweep = _iso(-30)  # recent
        self.assertEqual(server.sweep_due_vaults(force=True), ["wiki"])

    def test_no_subscriptions_never_sweeps(self) -> None:
        server._watcher.load_subs = lambda v: {"subscriptions": [], "last_sweep": None}
        self.assertEqual(server.sweep_due_vaults(), [])

    def test_iso_age_helper(self) -> None:
        import time
        now = time.time()
        self.assertEqual(server._iso_age_sec(None, now), float("inf"))
        self.assertLess(abs(server._iso_age_sec(_iso(-100), now) - 100), 5)


if __name__ == "__main__":
    unittest.main()
