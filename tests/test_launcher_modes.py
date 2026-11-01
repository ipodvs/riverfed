"""POSIX launchers must stay executable in Git.

A fresh clone runs `./setup.sh` and double-clicks the `.command` files; a
rewrite that drops the executable bit turns both into "permission denied"
for every new user while the tests stay green.
"""
from __future__ import annotations

import shutil
import subprocess
import unittest

import _util

PROJECT_DIR = _util.PROJECT_DIR


class LauncherModes(unittest.TestCase):
    def test_posix_launchers_are_executable_in_the_index(self):
        if not shutil.which("git") or not (PROJECT_DIR / ".git").exists():
            self.skipTest("not a git checkout")
        out = subprocess.run(
            ["git", "ls-files", "-s", "--", "*.command", "setup.sh"],
            cwd=PROJECT_DIR, capture_output=True, text=True, check=True,
        ).stdout
        modes = {line.split("\t", 1)[1]: line.split()[0]
                 for line in out.splitlines() if "\t" in line}
        self.assertIn("setup.sh", modes)
        not_exec = sorted(p for p, m in modes.items() if m != "100755")
        self.assertEqual(
            not_exec, [],
            f"launchers lost their executable bit: {not_exec}. "
            "Fix with `git update-index --chmod=+x <file>`.")


if __name__ == "__main__":
    unittest.main()
