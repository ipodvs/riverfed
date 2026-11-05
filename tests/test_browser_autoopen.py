"""Automated restarts must not pop browser windows.

The launchd job and the watchdogs restart the server with no terminal
attached. Before this guard every restart called webbrowser.open, so a
server that crashed hourly stacked up new browser windows all day.
"""
from __future__ import annotations

import io
import os
import unittest
from unittest import mock

import _util  # noqa: F401  (path bootstrap)
import server


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


class ShouldOpenBrowser(unittest.TestCase):
    def setUp(self):
        env = {k: v for k, v in os.environ.items() if k != "RIVERFED_NO_BROWSER"}
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_terminal_start_opens_the_page(self):
        with mock.patch.object(server.sys, "stdin", _Tty()):
            self.assertTrue(server.should_open_browser())

    def test_background_start_does_not(self):
        # launchd / nohup / watchdog: stdin is /dev/null or a pipe.
        with mock.patch.object(server.sys, "stdin", io.StringIO()):
            self.assertFalse(server.should_open_browser())

    def test_windowless_start_does_not(self):
        # pythonw.exe via start.vbs: no stdin at all.
        with mock.patch.object(server.sys, "stdin", None):
            self.assertFalse(server.should_open_browser())

    def test_env_opt_out_wins_over_terminal(self):
        with mock.patch.dict(os.environ, {"RIVERFED_NO_BROWSER": "1"}), \
             mock.patch.object(server.sys, "stdin", _Tty()):
            self.assertFalse(server.should_open_browser())

    def test_no_timer_when_gated(self):
        with mock.patch.object(server, "should_open_browser", return_value=False), \
             mock.patch.object(server.threading, "Timer") as timer:
            server.open_browser_when_ready("http://127.0.0.1:8765/")
        timer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
