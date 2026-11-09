#!/bin/bash
# Full remaining pipeline, idempotent and kill/restart-resilient.
# Legs skip themselves when their outputs already exist. Training uses
# the checkpointing trainer with an auto-resume loop (up to 10 tries).
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results
D=~/workspace/edit-lab/data
CS=~/workspace/edit-lab/candsets

train_until_done () {  # $1=specialist $2=data $3=epochs $4=lr $5=ckdir $6=outdir $7=logfile
  local n=0
  while [ ! -f "$6/training_meta.json" ] && [ $n -lt 10 ]; do
    n=$((n+1))
    echo "--- $1 train attempt $n $(date +%T) ---" >> "$7"
    $PY -u ~/workspace/edit-lab/train_ckpt.py "$1" \
      --data "$2" --epochs "$3" --rank 16 --alpha 32 --lr "$4" \
      --save-every 2 --ckpt "$5" --resume \
      --out "$6" >> "$7" 2>&1
    echo "--- $1 attempt $n exit=$? ---" >> "$7"
    sleep 5
  done
  [ -f "$6/training_meta.json" ]
}

echo "=== leg 1: coordinator specialized train ==="
train_until_done coordinator $D/coordinator_specialized.jsonl 1 2e-4 \
  ~/workspace/edit-lab/ckpts/coord-spec $CS/coord-spec/coordinator $R/train_coord_ckpt.log \
  && echo "coord train OK" || echo "COORD_TRAIN_FAILED"

if [ -f "$CS/coord-spec/coordinator/training_meta.json" ] && [ ! -f "$R/coord_spec1.json" ]; then
  echo "=== leg 2: coordinator eval ==="
  AGENT_TEAM_ADAPTERS=$CS/coord-spec \
    $PY -u training/observe.py --only coordinator --tag coord_spec1 > $R/coord_spec1.log 2>&1
  cp -n training/reports/coord_spec1.json $R/ 2>/dev/null
  echo "coord eval exit=$?"
fi

echo "=== leg 3: researcher gentle train (half set, compute-forced) ==="
train_until_done researcher $D/researcher_gentle_half.jsonl 1 1e-4 \
  ~/workspace/edit-lab/ckpts/res-spec2 $CS/res-spec2/researcher $R/train_res_ckpt2.log \
  && echo "res train OK" || echo "RES_TRAIN_FAILED"

if [ -f "$CS/res-spec2/researcher/training_meta.json" ] && [ ! -f "$R/res_spec.json" ]; then
  echo "=== leg 4: researcher eval ==="
  AGENT_TEAM_ADAPTERS=$CS/res-spec2 \
    $PY -u training/observe.py --only researcher_plan researcher_extract \
    --tag res_spec > $R/res_spec.log 2>&1
  cp -n training/reports/res_spec.json $R/ 2>/dev/null
  echo "res eval exit=$?"
fi

echo "ALL_LEGS_DONE"
