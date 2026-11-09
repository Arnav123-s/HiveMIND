#!/usr/bin/env bash
# Score every specialist on the held-out evals: edited weights vs base weights (same improved design).
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
AGENT_TEAM_ENGINE=hf $PY training/observe.py --tag trained --live --only coordinator researcher_plan researcher_extract verifier writer browser browser_live
AGENT_TEAM_ENGINE=hf $PY training/observe.py --tag base_tools --no-adapters --live --only browser browser_live coder
AGENT_TEAM_ENGINE=hf AGENT_TEAM_CODER=Qwen/Qwen2.5-Coder-3B-Instruct $PY training/observe.py --tag coder3b --only coder
$PY training/compare.py base base_tools trained coder3b
