#!/bin/bash
# Phase 3R (recovery): the first coordinator training was SIGKILLed
# (exit 137, OOM under shared-cell pressure) after step 10/28.
# Leaner doses, same targets:
#  - coordinator specialized: 1 epoch over the 56-row set (14 steps)
#  - researcher gentle: 71 rows (extract x1 + plan x1), 1 epoch, lr 1e-4
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results
D=~/workspace/edit-lab/data
CS=~/workspace/edit-lab/candsets

echo "=== phase3Ra: train coordinator specialized (1 epoch) ==="
$PY -u training/train_lora.py coordinator \
  --data $D/coordinator_specialized.jsonl \
  --epochs 1 --rank 16 --alpha 32 --lr 2e-4 \
  --out $CS/coord-spec/coordinator > $R/train_coord_spec1.log 2>&1
echo "exit=$?"

echo "=== phase3Rb: eval coordinator specialized ==="
AGENT_TEAM_ADAPTERS=$CS/coord-spec \
  $PY -u training/observe.py --only coordinator --tag coord_spec1 > $R/coord_spec1.log 2>&1
echo "exit=$?"

echo "=== phase3Rc: train researcher gentle (1 epoch, lr 1e-4) ==="
$PY -u training/train_lora.py researcher \
  --data $D/researcher_gentle.jsonl \
  --epochs 1 --rank 16 --alpha 32 --lr 1e-4 \
  --out $CS/res-spec/researcher > $R/train_res_spec.log 2>&1
echo "exit=$?"

echo "=== phase3Rd: eval researcher gentle ==="
AGENT_TEAM_ADAPTERS=$CS/res-spec \
  $PY -u training/observe.py --only researcher_plan researcher_extract \
  --tag res_spec > $R/res_spec.log 2>&1
echo "exit=$?"

echo "PHASE3R_DONE"
