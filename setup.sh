#!/bin/sh
# setup.sh: put HiveMIND on this device and leave it running. Linux and macOS. (Windows: the same steps are in the
# README under "Install".) Run it from the folder it is in:   sh setup.sh
# What it does, in order; each step is skipped if it is already done:
#   1. a Python environment in .venv and the packages (CPU builds; no GPU is used)
#   2. llama.cpp compiled for this CPU (needs a C++ compiler and cmake; about 10 minutes)
#   3. the browser the web specialist drives
#   4. the cells built for llama.cpp
#   5. the tests
#   6. the always-on agent installed, so it starts with the device. Whenever the device is idle it goes on by
#      itself: it harvests text, grows cells, sends roles to school, and keeps only what measures better.
# Nothing here logs in anywhere, uses a token or costs money. Models come from Hugging Face on first use (about 10 GB).
set -e
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
[ -d .venv ] || "$PYTHON" -m venv .venv
PY=.venv/bin/python
$PY -c "import torch" 2>/dev/null || $PY -m pip install torch --index-url https://download.pytorch.org/whl/cpu
$PY -m pip install -q -r requirements.txt
$PY -c "import llama_cpp" 2>/dev/null || CMAKE_ARGS="-DGGML_NATIVE=ON" $PY -m pip install llama-cpp-python==0.3.36
$PY -m playwright install chromium
$PY training/cells_build.py
# the hive as it has grown on GitHub (bodies, cells, harvested text); a hive here that is as big or bigger is left alone
$PY training/hive_state.py pull || echo "setup: the grown hive could not be fetched; the hive here starts from what it has"
$PY -m pytest -q tests || echo "setup: some tests failed on this device; the hive is still installed, see the output above"
if [ "${HIVE_NO_SERVICE:-0}" != "1" ]; then
    $PY -m team install
    echo "setup: the always-on agent is installed. Talk to the hive with ./hive ; its log is memory/serve.log"
fi
