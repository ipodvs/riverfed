"""Server gates ingest on the same source-readiness data shown in the editor."""
from __future__ import annotations

import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest import mock

import _util  # noqa: F401  (path bootstrap)
import server


class PendingPayload(unittest.TestCase):
    @mock.patch("server.subprocess.run")
    def test_structured_scanner_output_is_returned(self, run):
        payload = {
            "pending": [{"filename": "ready.md"}],
            "count": 1,
            "ready_count": 1,
            "blocked_count": 0,
        }
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(payload), stderr=""
        )

        result = server._pending_payload(SimpleNamespace(slug="wiki"))

        self.assertEqual(payload, result)
        self.assertIn("--json", run.call_args.args[0])

    @mock.patch("server.subprocess.run")
    def test_scanner_error_is_not_silently_treated_as_empty(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout=json.dumps({"error": "model unavailable"}),
            stderr="",
        )

        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            server._pending_payload(SimpleNamespace(slug="wiki"))


class IngestPreflight(unittest.TestCase):
    @mock.patch("server.JOBS.submit")
    @mock.patch("server._pending_payload")
    def test_blocked_sources_stop_before_agent_job(self, pending, submit):
        pending.return_value = {
            "pending": [{"filename": "failed.md"}],
            "count": 1,
            "ready_count": 0,
            "blocked_count": 1,
        }

        result = server.submit_ingest_job(
            SimpleNamespace(slug="wiki", display_name=lambda: "Riverfed")
        )

        self.assertFalse(result["success"])
        self.assertEqual("sources_need_recovery", result["code"])
        self.assertIn("1 source", result["error"])
        submit.assert_not_called()

    @mock.patch("server.JOBS.submit")
    @mock.patch("server._pending_payload")
    def test_empty_queue_has_a_distinct_failure(self, pending, submit):
        pending.return_value = {
            "pending": [],
            "count": 0,
            "ready_count": 0,
            "blocked_count": 0,
        }

        result = server.submit_ingest_job(
            SimpleNamespace(slug="wiki", display_name=lambda: "Riverfed")
        )

        self.assertFalse(result["success"])
        self.assertEqual("no_ready_sources", result["code"])
        submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
