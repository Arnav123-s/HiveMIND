#!/bin/bash
# Strength-sweep runs: s=0.5 for both roles, unmodified harness, copied tree.
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results

echo "=== sweep 1: coordinator s=0.5 ==="
AGENT_TEAM_ADAPTERS=~/workspace/edit-lab/candidates/coord-s50 \
  $PY training/observe.py --only coordinator --tag coord_s50 > $R/coord_s50.log 2>&1
echo "exit=$?"

echo "=== sweep 2: researcher s=0.5 ==="
AGENT_TEAM_ADAPTERS=~/workspace/edit-lab/candidates/res-s50 \
  $PY training/observe.py --only researcher_plan researcher_extract --tag res_s50 > $R/res_s50.log 2>&1
echo "exit=$?"

echo "SWEEP_DONE"
