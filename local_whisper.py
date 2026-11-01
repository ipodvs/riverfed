"""Local, API-key-free speech-to-text through whisper.cpp.

The model files live in a user cache, never in the repository. Downloads are
pinned to immutable Hugging Face revisions and verified with SHA-256 before
an atomic rename makes them available to conversion jobs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


PROJECT_DIR = Path(__file__).resolve().parent
WHISPER_CPP_VERSION = "1.9.2"
SMOKE_MODEL = "tiny"
PRODUCTION_MODEL = "large-v3-turbo-q5_0"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    filename: str
    url: str
    sha256: str
    bytes: int
    display_size: str
    purpose: str


MODEL_CATALOG = {
    SMOKE_MODEL: ModelSpec(
        name=SMOKE_MODEL,
        filename="ggml-tiny.bin",
        url=(
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/"
            "c521a4b02f422512d734391fdf08bb08c0862f68/ggml-tiny.bin"
            "?download=true"
        ),
        sha256=(
            "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21"
        ),
        bytes=77_691_713,
        display_size="75 MiB",
        purpose="setup smoke tests and low-disk fallback",
    ),
    PRODUCTION_MODEL: ModelSpec(
        name=PRODUCTION_MODEL,
        filename="ggml-large-v3-turbo-q5_0.bin",
        url=(
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/"
            "98aa99a0a9db05ae2342309f5096248665f7cba3/"
            "ggml-large-v3-turbo-q5_0.bin?download=true"
        ),
        sha256=(
            "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2"
        ),
        bytes=574_041_195,
        display_size="547 MiB",
        purpose="production multilingual transcription",
    ),
}


@dataclass(frozen=True)
class LocalTranscript:
    text: str
    language: str
    model: str
    engine: str
    engine_version: str
    segment_count: int


def _project_env_value(name: str) -> str:
    direct = (os.environ.get(name) or "").strip()
    if direct:
        return direct
    env_file = PROJECT_DIR / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() != name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value.strip()
    return ""


def cache_dir() -> Path:
    override = _project_env_value("RIVERFED_WHISPER_DIR")
    if override:
        return Path(override).expanduser()
    if platform.system() == "Darwin":
        return (
            Path.home() / "Library" / "Caches" / "Riverfed" / "whisper.cpp"
        )
    xdg = (os.environ.get("XDG_CACHE_HOME") or "").strip()
    root = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
    return root / "riverfed" / "whisper.cpp"


def model_path(name: str) -> Path:
    try:
        spec = MODEL_CATALOG[name]
    except KeyError as exc:
        options = ", ".join(sorted(MODEL_CATALOG))
        raise ValueError(f"unknown Whisper model {name!r}; choose {options}") from exc
    return cache_dir() / "models" / spec.filename


def selected_model_name() -> str:
    explicit = _project_env_value("RIVERFED_WHISPER_MODEL")
    if explicit:
        if explicit not in MODEL_CATALOG:
            options = ", ".join(sorted(MODEL_CATALOG))
            raise ValueError(
                f"RIVERFED_WHISPER_MODEL={explicit!r} is unsupported; choose {options}"
            )
        return explicit
    if model_path(PRODUCTION_MODEL).is_file():
        return PRODUCTION_MODEL
    if model_path(SMOKE_MODEL).is_file():
        return SMOKE_MODEL
    return PRODUCTION_MODEL


def resolve_binary() -> Path | None:
    override = _project_env_value("WHISPER_CPP_BIN")
    candidates: list[str | Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    for name in ("whisper-cli", "whisper-cpp"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates.extend(
        (
            Path("/opt/homebrew/bin/whisper-cli"),
            Path("/usr/local/bin/whisper-cli"),
        )
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
    return None


def binary_version(binary: Path) -> str:
    try:
        proc = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    output = f"{proc.stdout}\n{proc.stderr}"
    match = re.search(r"(?:version[: ]+|whisper\.cpp version[: ]+)(v?[0-9.]+)", output)
    return match.group(1).lstrip("v") if match else "unknown"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(path: Path, spec: ModelSpec) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"model is not installed: {path}"
    actual_size = path.stat().st_size
    if actual_size != spec.bytes:
        return (
            False,
            f"model size mismatch: expected {spec.bytes}, found {actual_size}",
        )
    actual_hash = sha256_file(path)
    if actual_hash != spec.sha256:
        return (
            False,
            f"model checksum mismatch: expected {spec.sha256}, found {actual_hash}",
        )
    return True, ""


def install_model(
    name: str,
    *,
    repair: bool = False,
    opener: Callable = urllib.request.urlopen,
) -> Path:
    if name not in MODEL_CATALOG:
        options = ", ".join(sorted(MODEL_CATALOG))
        raise ValueError(f"unknown Whisper model {name!r}; choose {options}")
    spec = MODEL_CATALOG[name]
    target = model_path(name)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        valid, reason = verify_model(target, spec)
        if valid:
            print(
                f"Whisper model ready: {name} ({spec.display_size}) at {target}"
            )
            return target
        if not repair:
            raise RuntimeError(
                f"{reason}. Re-run with --repair to preserve and replace it."
            )
        backup = target.with_name(f"{target.name}.corrupt")
        suffix = 2
        while backup.exists():
            backup = target.with_name(f"{target.name}.corrupt-{suffix}")
            suffix += 1
        target.replace(backup)
        print(f"Preserved invalid model as {backup}", file=sys.stderr)

    partial = target.with_suffix(f"{target.suffix}.part")
    if partial.exists():
        partial.unlink()
    print(
        f"Downloading Whisper model {name}: {spec.display_size}\n"
        f"  {spec.url}\n"
        f"  destination: {target}"
    )
    request = urllib.request.Request(
        spec.url, headers={"User-Agent": "Riverfed/1.0"}
    )
    digest = hashlib.sha256()
    received = 0
    last_percent = -5
    try:
        with opener(request, timeout=60) as response, partial.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                percent = int(received * 100 / spec.bytes)
                if percent >= last_percent + 5:
                    print(
                        f"  model download: {min(percent, 100)}% "
                        f"({received / (1024 * 1024):.1f} MiB)",
                        file=sys.stderr,
                    )
                    last_percent = percent
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    if received != spec.bytes:
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"model download size mismatch: expected {spec.bytes}, got {received}"
        )
    actual_hash = digest.hexdigest()
    if actual_hash != spec.sha256:
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"model checksum mismatch: expected {spec.sha256}, got {actual_hash}"
        )
    os.replace(partial, target)
    print(f"Verified SHA-256 and installed {target}")
    return target


def readiness(model_name: str | None = None) -> tuple[bool, str]:
    binary = resolve_binary()
    if binary is None:
        return (
            False,
            "whisper-cli is not installed; run ./setup.sh "
            f"--whisper-model {SMOKE_MODEL}",
        )
    name = model_name or selected_model_name()
    spec = MODEL_CATALOG[name]
    valid, reason = verify_model(model_path(name), spec)
    if not valid:
        return (
            False,
            f"{reason}; run ./setup.sh --whisper-model {name}",
        )
    return True, ""


def _timestamp(value: str) -> str:
    return value.replace(",", ".").strip()


def parse_output(data: dict) -> tuple[str, str, int]:
    result = data.get("result") or {}
    language = str(result.get("language") or data.get("language") or "").strip()
    segments = data.get("transcription") or data.get("segments") or []
    lines: list[str] = []
    for segment in segments:
        text = re.sub(r"\s+", " ", str(segment.get("text") or "")).strip()
        if not text:
            continue
        timestamps = segment.get("timestamps") or {}
        start = _timestamp(str(timestamps.get("from") or ""))
        end = _timestamp(str(timestamps.get("to") or ""))
        if start and end:
            lines.append(f"[{start} - {end}] {text}")
        else:
            lines.append(text)
    if not lines:
        plain = str(data.get("text") or result.get("text") or "").strip()
        if plain:
            lines.append(re.sub(r"\s+", " ", plain))
    return "\n".join(lines).strip(), language, len(lines)


def content_word_count(text: str) -> int:
    """Count spoken words without letting timestamp labels satisfy a guard."""
    without_timestamps = re.sub(
        r"^\[[0-9:.,]+\s+-\s+[0-9:.,]+\]\s*",
        "",
        text,
        flags=re.MULTILINE,
    )
    return len(without_timestamps.split())


def _run_cli(
    command: list[str], *, show_progress: bool
) -> tuple[int, str]:
    """Run whisper-cli while keeping transcript text out of the job log."""
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    recent: deque[str] = deque(maxlen=20)
    last_progress = -5
    assert proc.stdout is not None
    with proc.stdout:
        for raw in proc.stdout:
            line = raw.strip()
            if not line:
                continue
            recent.append(line)
            match = re.search(r"progress\s*=\s*([0-9]+)%", line)
            if show_progress and match:
                percent = int(match.group(1))
                if percent >= last_progress + 5:
                    print(
                        f"  local Whisper progress: {min(percent, 100)}%",
                        file=sys.stderr,
                    )
                    last_progress = percent
    return proc.wait(), "\n".join(recent)


def transcribe_wav(
    wav_path: Path,
    *,
    model_name: str | None = None,
    output_dir: Path | None = None,
) -> LocalTranscript | None:
    name = model_name or selected_model_name()
    ready, reason = readiness(name)
    if not ready:
        raise RuntimeError(reason)
    binary = resolve_binary()
    assert binary is not None
    model = model_path(name)

    owned_dir: tempfile.TemporaryDirectory[str] | None = None
    if output_dir is None:
        owned_dir = tempfile.TemporaryDirectory(prefix="riverfed-whisper-result-")
        output_dir = Path(owned_dir.name)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "transcript"
    command = [
        str(binary),
        "--model", str(model),
        "--file", str(wav_path),
        "--language", "auto",
        "--output-json-full",
        "--output-file", str(prefix),
        "--print-progress",
    ]
    version = binary_version(binary)
    print(
        f"  local Whisper: engine whisper.cpp {version}, model {name}, "
        "language auto",
        file=sys.stderr,
    )
    try:
        returncode, detail = _run_cli(command, show_progress=True)
        if returncode != 0:
            raise RuntimeError(
                f"whisper-cli exited with status {returncode}: {detail[-500:]}"
            )
        json_path = prefix.with_suffix(".json")
        if not json_path.is_file():
            raise RuntimeError(
                f"whisper-cli produced no JSON transcript at {json_path}"
            )
        data = json.loads(json_path.read_text(encoding="utf-8"))
        text, language, segment_count = parse_output(data)
        if not text:
            return None
        return LocalTranscript(
            text=text,
            language=language,
            model=name,
            engine="whisper.cpp",
            engine_version=version,
            segment_count=segment_count,
        )
    finally:
        if owned_dir is not None:
            owned_dir.cleanup()


def smoke_test(model_name: str = SMOKE_MODEL) -> None:
    ready, reason = readiness(model_name)
    if not ready:
        raise RuntimeError(reason)
    with tempfile.TemporaryDirectory(prefix="riverfed-whisper-smoke-") as raw:
        root = Path(raw)
        wav_path = root / "silence.wav"
        with wave.open(str(wav_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16_000)
            handle.writeframes(b"\x00\x00" * 16_000)
        binary = resolve_binary()
        assert binary is not None
        prefix = root / "smoke"
        returncode, detail = _run_cli(
            [
                str(binary),
                "--model", str(model_path(model_name)),
                "--file", str(wav_path),
                "--language", "auto",
                "--output-json-full",
                "--output-file", str(prefix),
                "--no-prints",
            ],
            show_progress=False,
        )
        if returncode != 0 or not prefix.with_suffix(".json").is_file():
            raise RuntimeError(
                "whisper.cpp smoke test failed to load the model and emit JSON: "
                f"{detail[-500:]}"
            )
    print(
        f"whisper.cpp smoke test passed with {model_name} "
        f"({MODEL_CATALOG[model_name].display_size})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install and verify Riverfed local Whisper models."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install-model")
    install.add_argument("--model", choices=sorted(MODEL_CATALOG), required=True)
    install.add_argument("--repair", action="store_true")
    smoke = sub.add_parser("smoke-test")
    smoke.add_argument("--model", choices=sorted(MODEL_CATALOG), default=SMOKE_MODEL)
    sub.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.command == "install-model":
            install_model(args.model, repair=args.repair)
        elif args.command == "smoke-test":
            smoke_test(args.model)
        else:
            name = selected_model_name()
            ready, reason = readiness(name)
            binary = resolve_binary()
            print(f"binary: {binary or 'missing'}")
            print(f"model: {name} ({model_path(name)})")
            print(f"status: {'ready' if ready else reason}")
            return 0 if ready else 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
