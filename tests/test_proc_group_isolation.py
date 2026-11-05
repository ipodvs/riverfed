"""A job timeout must kill the job, never the server.

run_streaming used to start children in the server's own process group, so
kill_tree's killpg on a timed-out watcher sweep SIGKILLed the server as well.
Under launchd that meant a crash, a watchdog restart and a fresh browser
window every 50 minutes.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest

import _util

from _proc import run_streaming

POSIX = sys.platform != "win32"


def _isolated(body: str) -> subprocess.CompletedProcess:
    """Run ``body`` in a throwaway session. If the group isolation regresses,
    the killpg hits that process instead of the test runner, and the test
    fails normally."""
    script = f"import subprocess, sys\nsys.path.insert(0, {str(_util.SCRIPTS_DIR)!r})\n" \
             + textwrap.dedent(body)
    return subprocess.run([sys.executable, "-c", script], capture_output=True,
                          text=True, timeout=60, start_new_session=True,
                          stdin=subprocess.DEVNULL)


@unittest.skipUnless(POSIX, "process groups are POSIX-only")
class ProcessGroupIsolation(unittest.TestCase):
    def test_child_gets_its_own_process_group(self):
        rc, out, _err, _t = run_streaming(
            [sys.executable, "-c", "import os; print(os.getpgrp())"], timeout=30)
        self.assertEqual(rc, 0)
        self.assertNotEqual(int(out[0]), os.getpgrp())

    def test_timeout_kills_the_child_and_spares_the_caller(self):
        proc = _isolated("""
            from _proc import run_streaming
            rc, _o, _e, timed_out = run_streaming(
                [sys.executable, "-c", "import time; time.sleep(60)"], timeout=0.5)
            print("alive", timed_out, rc)
        """)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("alive True -9", proc.stdout)

    def test_kill_tree_on_a_same_group_child_spares_the_caller(self):
        proc = _isolated("""
            from _proc import kill_tree
            child = subprocess.Popen([sys.executable, "-c",
                                      "import time; time.sleep(60)"])
            kill_tree(child.pid)
            child.wait(timeout=10)
            print("alive", child.returncode)
        """)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("alive -9", proc.stdout)


if __name__ == "__main__":
    unittest.main()
