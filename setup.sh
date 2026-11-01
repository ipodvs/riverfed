#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

WHISPER_MODEL="tiny"
SKIP_WHISPER=0
RUN_SMOKE=1
SKIP_PYTHON_DEPS=0

usage() {
    echo "Usage: ./setup.sh [options]"
    echo ""
    echo "Options:"
    echo "  --whisper-model tiny|large-v3-turbo-q5_0"
    echo "      tiny: 75 MiB setup/smoke model (default)"
    echo "      large-v3-turbo-q5_0: 547 MiB production multilingual model"
    echo "  --skip-whisper       Set up the app without local transcription"
    echo "  --no-smoke-test      Skip the one-second local Whisper smoke test"
    echo "  --skip-python-deps   Reuse an existing .venv without pip install"
    echo "  -h, --help           Show this help"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --whisper-model)
            if [ "$#" -lt 2 ]; then
                echo "Error: --whisper-model requires a value" >&2
                exit 2
            fi
            WHISPER_MODEL="$2"
            shift 2
            ;;
        --skip-whisper)
            SKIP_WHISPER=1
            shift
            ;;
        --no-smoke-test)
            RUN_SMOKE=0
            shift
            ;;
        --skip-python-deps)
            SKIP_PYTHON_DEPS=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$WHISPER_MODEL" in
    tiny|large-v3-turbo-q5_0)
        ;;
    *)
        echo "Error: unsupported Whisper model: $WHISPER_MODEL" >&2
        exit 2
        ;;
esac

select_python() {
    for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
        if ! command -v "$candidate" >/dev/null 2>&1; then
            continue
        fi
        if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

PYTHON_BIN="$(select_python || true)"
if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.10 or newer is required." >&2
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "Install it with: brew install python@3.13" >&2
    fi
    exit 1
fi

echo "Riverfed clean-machine setup"
echo "  project: $(pwd)"
echo "  Python: $("$PYTHON_BIN" --version 2>&1)"
echo "  platform: $(uname -s) $(uname -m)"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating .venv..."
    "$PYTHON_BIN" -m venv .venv
else
    echo "Reusing existing .venv."
fi

VENV_PY=".venv/bin/python"
if [ "$SKIP_PYTHON_DEPS" -eq 0 ]; then
    echo "Installing Python dependencies..."
    "$VENV_PY" -m pip install --upgrade pip
    "$VENV_PY" -m pip install -r requirements.txt
else
    echo "Skipping Python dependency installation."
fi

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example."
else
    echo "Keeping existing .env."
fi

mkdir -p "${RIVERFED_VAULTS_DIR:-$HOME/RiverfedVaults}"

if [ "$SKIP_WHISPER" -eq 0 ]; then
    EXPECTED_WHISPER_VERSION="$(
        "$VENV_PY" -c 'import local_whisper; print(local_whisper.WHISPER_CPP_VERSION)'
    )"
    if ! command -v whisper-cli >/dev/null 2>&1; then
        if [ "$(uname -s)" != "Darwin" ]; then
            echo "Error: automatic whisper.cpp installation currently targets macOS." >&2
            echo "Install whisper-cli $EXPECTED_WHISPER_VERSION, then re-run setup." >&2
            exit 1
        fi
        if ! command -v brew >/dev/null 2>&1; then
            echo "Error: Homebrew is required to install whisper.cpp on a clean Mac." >&2
            echo "Install Homebrew from https://brew.sh, then re-run setup." >&2
            exit 1
        fi
        echo "Installing Homebrew whisper-cpp $EXPECTED_WHISPER_VERSION..."
        brew install whisper-cpp
    else
        echo "Reusing $(command -v whisper-cli)."
    fi

    WHISPER_VERSION="$(
        "$VENV_PY" -c 'import local_whisper; p=local_whisper.resolve_binary(); print(local_whisper.binary_version(p) if p else "missing")'
    )"
    if [ "$WHISPER_VERSION" != "$EXPECTED_WHISPER_VERSION" ]; then
        echo "Error: whisper.cpp version $EXPECTED_WHISPER_VERSION is required; found $WHISPER_VERSION." >&2
        echo "This pin prevents an unreviewed binary upgrade. Update the repository pin deliberately." >&2
        exit 1
    fi
    echo "whisper.cpp version: $WHISPER_VERSION"

    "$VENV_PY" local_whisper.py install-model --model "$WHISPER_MODEL"
    if [ "$RUN_SMOKE" -eq 1 ]; then
        "$VENV_PY" local_whisper.py smoke-test --model "$WHISPER_MODEL"
    fi
else
    echo "Skipping local Whisper installation."
fi

echo ""
echo "Setup complete."
echo "Start the app with: ./serve.command"
echo "Then open: http://127.0.0.1:8765/"
if [ "$WHISPER_MODEL" = "tiny" ] && [ "$SKIP_WHISPER" -eq 0 ]; then
    echo ""
    echo "The 75 MiB tiny model proves the offline path."
    echo "For production quality, install the 547 MiB multilingual model explicitly:"
    echo "  ./setup.sh --whisper-model large-v3-turbo-q5_0 --skip-python-deps"
fi
