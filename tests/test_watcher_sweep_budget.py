"""A watcher sweep must finish on its own and not get stuck on one video.

Since 2026-10-30 every sweep tried the same slow videos first, ran past the
server's 45-minute job cap, got killed before writing last_sweep, and started
over after the next restart. The sweep now stops starting conversions once a
new one could overrun its budget, and skips a video after three failed tries.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _util  # noqa: F401  (path bootstrap)

import sys
sys.path.insert(0, str(_util.PROJECT_DIR))
import watcher  # noqa: E402
from _wikis import Vault  # noqa: E402


def _video(vid):
    return {"id": vid, "title": f"Video {vid}",
            "url": f"https://www.youtube.com/watch?v={vid}"}


class SweepBudget(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp(prefix="riverfed-test-watcher-"))
        self.vault = Vault(slug="t", root=root, output=root / "output")
        watcher.save_subs(self.vault, {
            "subscriptions": [{"id": "@chan", "title": "Chan", "seen_ids": []}],
            "last_sweep": None, "history": []})
        self.new = [_video("aaa"), _video("bbb")]

    def _discover(self, vault):
        data = watcher.load_subs(vault)
        seen = set(data["subscriptions"][0].get("seen_ids") or [])
        return [{"sub": "@chan", "title": "Chan", "auto_ingest": False,
                 "frames": False,
                 "new": [v for v in self.new if v["id"] not in seen]}]

    def _sweep(self, run, budget=watcher.SWEEP_BUDGET_SEC):
        with mock.patch.object(watcher, "discover", self._discover), \
             mock.patch.object(watcher.subprocess, "run", run):
            return watcher.run_sweep(self.vault, budget_sec=budget)

    def test_no_budget_left_defers_and_still_records_the_sweep(self):
        run = mock.Mock()
        summary = self._sweep(run, budget=watcher.CONVERT_TIMEOUT_SEC - 1)
        run.assert_not_called()
        self.assertEqual(summary["deferred"], ["aaa", "bbb"])
        self.assertIsNotNone(watcher.load_subs(self.vault)["last_sweep"])

    def test_hanging_video_is_skipped_after_three_tries(self):
        def run(cmd, **kw):
            if "aaa" in cmd[3]:
                raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
            return subprocess.CompletedProcess(cmd, 0, "", "")

        first = self._sweep(run)
        self.assertEqual([c["id"] for c in first["converted"]], ["bbb"])
        self.assertIn("attempt 1 of 3", first["errors"][0])
        self._sweep(run)
        third = self._sweep(run)
        self.assertIn("skipped after 3 attempts", third["errors"][0])
        sub = watcher.load_subs(self.vault)["subscriptions"][0]
        self.assertIn("aaa", sub["seen_ids"])
        self.assertEqual(sub["failures"], {})
        self.assertEqual(self._discover(self.vault)[0]["new"], [])

    def test_previously_failing_videos_go_last(self):
        data = watcher.load_subs(self.vault)
        data["subscriptions"][0]["failures"] = {"aaa": 1}
        watcher.save_subs(self.vault, data)
        order = []

        def run(cmd, **kw):
            order.append(cmd[3].rsplit("=", 1)[1])
            return subprocess.CompletedProcess(cmd, 0, "", "")

        self._sweep(run)
        self.assertEqual(order, ["bbb", "aaa"])
        sub = watcher.load_subs(self.vault)["subscriptions"][0]
        self.assertEqual(sub["failures"], {})


if __name__ == "__main__":
    unittest.main()
