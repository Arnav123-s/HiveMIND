#!/bin/bash
# Phase 2: base researcher (correct suite names) + coordinator s=0.5 sweep.
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results

echo "=== phase2a: base researcher (plan+extract, no adapters) ==="
$PY training/observe.py --only researcher_plan researcher_extract \
  --tag anchor_base_res2 --no-adapters > $R/anchor_base_res2.log 2>&1
echo "exit=$?"

echo "=== phase2b: coordinator s=0.5 ==="
AGENT_TEAM_ADAPTERS=~/workspace/edit-lab/candidates/coord-s50 \
  $PY training/observe.py --only coordinator --tag coord_s50 > $R/coord_s50.log 2>&1
echo "exit=$?"

echo "PHASE2_DONE"
