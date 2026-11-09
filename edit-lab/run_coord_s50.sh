#!/bin/bash
# Coordinator strength sweep s=0.5 (restart-resilient: run detached).
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results

AGENT_TEAM_ADAPTERS=~/workspace/edit-lab/candidates/coord-s50 \
  $PY training/observe.py --only coordinator --tag coord_s50 > $R/coord_s50.log 2>&1
echo "exit=$?"
echo "COORD_S50_DONE"
