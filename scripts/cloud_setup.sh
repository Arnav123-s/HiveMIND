#!/usr/bin/env bash
# cloud_setup.sh: put HiveMIND on a fresh cloud VM (a Claude Code cloud session, or any Linux box) so work can go on.
# Run from anywhere:   bash scripts/cloud_setup.sh          (everything: about 20 minutes, ~10 GB of models later)
#                      bash scripts/cloud_setup.sh --light  (only the growing hive: torch + a few packages, ~3 minutes)
# Idempotent: each step is skipped when it is already done. Nothing logs in, uses a token or costs money.
# Steps: 1 a venv in .venv  2 packages (CPU torch)  3 llama.cpp + browser + cells (full only)
#        4 the grown hive from GitHub (branch hive-seed / release hive-state)  5 the tests
# No always-on service is installed (cloud VMs have no systemd); start things with scripts/resume.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
LIGHT=0; [ "${1:-}" = "--light" ] && LIGHT=1
PYTHON="${PYTHON:-$(command -v python3.13 || command -v python3)}"
say() { printf '\n== cloud_setup: %s\n' "$*"; }

say "1. Python environment (.venv) with $($PYTHON --version)"
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
PY=.venv/bin/python
$PY -m pip install -q --upgrade pip

say "2. packages"
$PY -c "import torch" 2>/dev/null || $PY -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu || {
    # a cloud environment that lets only package registries through refuses download.pytorch.org (seen 2026-11-11):
    # PyPI's build is several GB bigger (it carries GPU libraries it never uses here) and runs on the CPU all the same
    echo "cloud_setup: the CPU build's host is not reachable here; taking torch from PyPI instead"
    $PY -m pip install -q torch
}
if [ "$LIGHT" = 1 ]; then
    # transformers: the growing hive does not use it, the tests of step 5 import it (team/llm.py)
    $PY -m pip install -q numpy tokenizers requests huggingface_hub pyarrow beautifulsoup4 lxml psutil pytest pyyaml \
        "$(grep '^transformers==' requirements.txt || echo transformers)"
else
    $PY -m pip install -q -r requirements.txt
    say "3. llama.cpp for this CPU (about 10 minutes the first time), the browser, the cells"
    $PY -c "import llama_cpp" 2>/dev/null || CMAKE_ARGS="-DGGML_NATIVE=ON" $PY -m pip install -q llama-cpp-python==0.3.36
    $PY -m playwright install chromium || echo "cloud_setup: browser install failed; the web specialist will not work"
    $PY training/cells_build.py
fi

say "4. the grown hive from GitHub"
$PY training/hive_state.py pull || echo "cloud_setup: the grown hive could not be fetched (see HANDOFF.md)"

say "5. tests"
$PY -m pytest -q tests/test_spawn.py || echo "cloud_setup: some tests failed; read the output above"

say "done. Next:  bash scripts/resume.sh status    (then: grow | exam | ask \"a task\")"
