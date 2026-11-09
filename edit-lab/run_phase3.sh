#!/bin/bash
# Phase 3: SPECIALIZED retrains (Arnav's steering: fix the specific
# failure, not generic dose changes), each followed by its eval.
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results
D=~/workspace/edit-lab/data
CS=~/workspace/edit-lab/candsets

echo "=== phase3a: train coordinator specialized ==="
$PY training/train_lora.py coordinator \
  --data $D/coordinator_specialized.jsonl \
  --epochs 2 --rank 16 --alpha 32 --lr 2e-4 \
  --out $CS/coord-spec/coordinator > $R/train_coord_spec.log 2>&1
echo "exit=$?"

echo "=== phase3b: eval coordinator specialized ==="
AGENT_TEAM_ADAPTERS=$CS/coord-spec \
  $PY training/observe.py --only coordinator --tag coord_spec > $R/coord_spec.log 2>&1
echo "exit=$?"

echo "=== phase3c: train researcher specialized (1 epoch, lr 1e-4) ==="
$PY training/train_lora.py researcher \
  --data $D/researcher_specialized.jsonl \
  --epochs 1 --rank 16 --alpha 32 --lr 1e-4 \
  --out $CS/res-spec/researcher > $R/train_res_spec.log 2>&1
echo "exit=$?"

echo "=== phase3d: eval researcher specialized ==="
AGENT_TEAM_ADAPTERS=$CS/res-spec \
  $PY training/observe.py --only researcher_plan researcher_extract \
  --tag res_spec > $R/res_spec.log 2>&1
echo "exit=$?"

echo "PHASE3_DONE"
