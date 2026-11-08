#!/usr/bin/env bash
# Engine v2 measurements (llama.cpp, 4-bit) vs the PyTorch results already in reports/.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
ALL="coordinator researcher_plan researcher_extract verifier writer browser browser_live coder"
# 1. bigger brain: Qwen3-4B for every role, Qwen2.5-Coder-7B for code
AGENT_TEAM_ENGINE=gguf $PY training/observe.py --tag v2_4b --live --only $ALL
# 2. small fast model + each specialist's own weight edit, on llama.cpp
AGENT_TEAM_ENGINE=gguf AGENT_TEAM_ROSTER='{"browser":"fast+browser","verifier":"fast+verifier","writer":"fast+writer"}' \
  $PY training/observe.py --tag v2_fast_edits --live --only browser browser_live verifier writer
# 3. base weights with the improved design (PyTorch) - separates design gains from weight gains
AGENT_TEAM_ENGINE=hf $PY training/observe.py --tag base_tools --no-adapters --live --only browser browser_live coder
$PY training/compare.py base base_tools trained v2_4b v2_fast_edits
