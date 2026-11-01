"""Grok argv and registration (A7 step 2).

Three of grok's flags are load-bearing in ways the other providers' are
not, and each guards a failure that is silent rather than loud:

  --sandbox off   grok's sandbox is off by default, but --sandbox also
                  reads GROK_SANDBOX from the environment, and the
                  `workspace` profile confines writes to cwd + /tmp —
                  which would break every vault write with no error we'd
                  recognise as a permissions problem.
  --no-leader     under leader mode ([cli] use_leader) the real agent
                  runs OUTSIDE our process tree, so _kill_tree() reaps a
                  client and leaves the worker running — voiding the
                  wall-clock timeout the 2026-08-05 hang fix added.
  --prompt-file   grok has no stdin route at all (`grok -p -` reads the
                  "-" as a literal prompt).

So these are pinned as tests, not left to the argv builder's comments.
"""
from __future__ import annotations

import os
import unittest

import _util  # noqa: F401
import agent_runner


def _argv(prompt_file: str | None = "/tmp/prompt.md",
          cwd: str = "/proj",
          add_dirs=(), allowed_tools: str | None = None) -> list[str]:
    return agent_runner._build_grok_argv(
        "grok", cwd, add_dirs, allowed_tools, prompt_file)


class GrokArgv(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = os.environ.pop("GROK_MODEL", None)
        self.addCleanup(
            lambda: os.environ.__setitem__("GROK_MODEL", self._saved)
            if self._saved is not None else None)

    def test_the_three_load_bearing_flags_are_present(self) -> None:
        argv = _argv()
        self.assertIn("--prompt-file", argv)
        self.assertEqual(argv[argv.index("--prompt-file") + 1],
                         "/tmp/prompt.md")
        self.assertEqual(argv[argv.index("--sandbox") + 1], "off")
        self.assertIn("--no-leader", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1],
                         "bypassPermissions")

    def test_cwd_is_passed_explicitly(self) -> None:
        self.assertEqual(_argv(cwd="/vaults/wiki")[
            _argv(cwd="/vaults/wiki").index("--cwd") + 1], "/vaults/wiki")

    def test_missing_prompt_file_fails_loudly(self) -> None:
        """run() must deliver by file; a None here means PROMPT_DELIVERY
        was misconfigured, and a prompt-less grok would sit interactive."""
        with self.assertRaisesRegex(RuntimeError, "--prompt-file"):
            _argv(prompt_file=None)

    def test_add_dirs_and_allowed_tools_are_ignored(self) -> None:
        """Neither maps onto grok: with the sandbox off there is nothing to
        grant, and its tool IDs are its own (run_terminal_cmd,
        search_replace, read_file), so Claude's vocabulary would mislead."""
        argv = _argv(add_dirs=["/v/root", "/v/out"],
                     allowed_tools="Read,Write,Edit")
        self.assertNotIn("--add-dir", argv)
        self.assertNotIn("--allow", argv)
        self.assertNotIn("--allowedTools", argv)
        self.assertNotIn("/v/root", argv)

    def test_model_pin_is_opt_in(self) -> None:
        self.assertNotIn("--model", _argv())
        os.environ["GROK_MODEL"] = "grok-4.5"
        try:
            argv = _argv()
        finally:
            os.environ.pop("GROK_MODEL", None)
        self.assertEqual(argv[argv.index("--model") + 1], "grok-4.5")


class GrokRegistration(unittest.TestCase):
    def test_grok_is_registered_everywhere_a_provider_must_be(self) -> None:
        self.assertIn("grok", agent_runner.PROVIDERS)
        for table in (agent_runner.DISPLAY_NAMES, agent_runner.LOGIN_HINTS,
                      agent_runner.CMD_LABELS, agent_runner._SCRUB_VARS,
                      agent_runner._ARGV_BUILDERS, agent_runner._STATUS_FNS,
                      agent_runner.PROMPT_DELIVERY):
            self.assertIn("grok", table)

    def test_auto_order_puts_grok_ahead_of_codex(self) -> None:
        """Decided 2026-08-15: auto falls through to grok before codex,
        because the usual trigger is a Claude usage limit mid-queue and
        grok can see frames where codex only gets OCR text."""
        order = list(agent_runner.PROVIDERS)
        self.assertEqual(order[0], "claude-code")
        self.assertLess(order.index("grok"), order.index("codex"))

    def test_grok_delivers_its_prompt_by_file(self) -> None:
        self.assertEqual(agent_runner.PROMPT_DELIVERY["grok"], "file")

    def test_sandbox_and_agent_env_are_scrubbed(self) -> None:
        """GROK_SANDBOX would pick a write-confining profile; GROK_AGENT
        would swap the agent profile out from under the pipeline."""
        for var in ("GROK_SANDBOX", "GROK_AGENT"):
            self.assertIn(var, agent_runner._SCRUB_VARS["grok"])
        os.environ["GROK_SANDBOX"] = "workspace"
        self.addCleanup(os.environ.pop, "GROK_SANDBOX", None)
        self.assertNotIn("GROK_SANDBOX", agent_runner.scrub_env("grok"))

    def test_provider_help_lists_every_provider(self) -> None:
        """The six studio scripts used to hardcode this list; A7 derives it
        so a fourth provider never needs eight argparse edits."""
        text = agent_runner.provider_arg_help("run the ingest on")
        for provider in agent_runner.PROVIDERS:
            self.assertIn(provider, text)


if __name__ == "__main__":
    unittest.main()
