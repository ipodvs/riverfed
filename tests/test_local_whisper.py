"""Local whisper.cpp setup, checksums, output parsing, and runner wiring."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import _util  # noqa: F401
import local_whisper


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int = -1) -> bytes:
        if self.offset >= len(self.body):
            return b""
        if size < 0:
            size = len(self.body) - self.offset
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class ModelInstall(unittest.TestCase):
    def test_download_is_checksum_verified_and_atomic(self):
        payload = b"small-model-fixture"
        spec = local_whisper.ModelSpec(
            name="fixture",
            filename="fixture.bin",
            url="https://example.test/fixture.bin",
            sha256=hashlib.sha256(payload).hexdigest(),
            bytes=len(payload),
            display_size="19 bytes",
            purpose="test",
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            opener = Mock(return_value=FakeResponse(payload))
            with patch.dict(
                local_whisper.MODEL_CATALOG, {"fixture": spec}, clear=True
            ):
                with patch("local_whisper.cache_dir", return_value=root):
                    path = local_whisper.install_model(
                        "fixture", opener=opener
                    )
            self.assertEqual(path.read_bytes(), payload)
            self.assertFalse(path.with_suffix(".bin.part").exists())
            opener.assert_called_once()

    def test_valid_existing_model_is_idempotent(self):
        payload = b"already-here"
        spec = local_whisper.ModelSpec(
            name="fixture",
            filename="fixture.bin",
            url="https://example.test/fixture.bin",
            sha256=hashlib.sha256(payload).hexdigest(),
            bytes=len(payload),
            display_size="12 bytes",
            purpose="test",
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "models" / spec.filename
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            opener = Mock()
            with patch.dict(
                local_whisper.MODEL_CATALOG, {"fixture": spec}, clear=True
            ):
                with patch("local_whisper.cache_dir", return_value=root):
                    self.assertEqual(
                        local_whisper.install_model(
                            "fixture", opener=opener
                        ),
                        target,
                    )
            opener.assert_not_called()


class WhisperOutput(unittest.TestCase):
    def test_timestamps_and_language_are_preserved(self):
        text, language, count = local_whisper.parse_output(
            {
                "result": {"language": "es"},
                "transcription": [
                    {
                        "timestamps": {
                            "from": "00:00:00,000",
                            "to": "00:00:04,200",
                        },
                        "text": " Hola mundo ",
                    },
                    {
                        "timestamps": {
                            "from": "00:00:04,200",
                            "to": "00:00:08,000",
                        },
                        "text": "Segunda frase",
                    },
                ],
            }
        )
        self.assertEqual(language, "es")
        self.assertEqual(count, 2)
        self.assertIn("[00:00:00.000 - 00:00:04.200] Hola mundo", text)
        self.assertEqual(local_whisper.content_word_count(text), 4)

    @patch("local_whisper.binary_version", return_value="1.9.1")
    @patch("local_whisper.resolve_binary", return_value=Path("/bin/echo"))
    @patch("local_whisper.readiness", return_value=(True, ""))
    def test_runner_uses_json_full_and_returns_provenance(
        self, _ready, _binary, _version
    ):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            wav = root / "audio.wav"
            wav.write_bytes(b"RIFF-fixture")
            model = root / "ggml-tiny.bin"
            model.write_bytes(b"model")

            def fake_run(command, show_progress=False):
                self.assertTrue(show_progress)
                self.assertIn("--output-json-full", command)
                prefix = Path(command[command.index("--output-file") + 1])
                prefix.with_suffix(".json").write_text(
                    json.dumps(
                        {
                            "result": {"language": "en"},
                            "transcription": [
                                {
                                    "timestamps": {
                                        "from": "00:00:00,000",
                                        "to": "00:00:02,000",
                                    },
                                    "text": "A local transcript",
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                return 0, ""

            with patch("local_whisper.model_path", return_value=model):
                with patch("local_whisper._run_cli", side_effect=fake_run):
                    result = local_whisper.transcribe_wav(
                        wav,
                        model_name="tiny",
                        output_dir=root / "result",
                    )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.language, "en")
        self.assertEqual(result.model, "tiny")
        self.assertEqual(result.engine, "whisper.cpp")
        self.assertEqual(result.engine_version, "1.9.1")
        self.assertEqual(result.segment_count, 1)


class SetupScript(unittest.TestCase):
    def test_setup_uses_the_shared_whisper_version_pin(self):
        self.assertEqual(local_whisper.WHISPER_CPP_VERSION, "1.9.2")
        script = (local_whisper.PROJECT_DIR / "setup.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("local_whisper.WHISPER_CPP_VERSION", script)

    def test_setup_shell_is_valid_and_documents_model_sizes(self):
        script = local_whisper.PROJECT_DIR / "setup.sh"
        subprocess.run(["bash", "-n", str(script)], check=True)
        help_result = subprocess.run(
            ["bash", str(script), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("75 MiB", help_result.stdout)
        self.assertIn("547 MiB", help_result.stdout)
        self.assertIn("--skip-whisper", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
