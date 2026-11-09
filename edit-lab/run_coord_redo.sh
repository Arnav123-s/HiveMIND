#!/bin/bash
# Coordinator specialized redo with a checkpointing trainer + auto-resume.
# Waits until no other heavy python is running (one heavy process at a
# time on this shared cell), then trains; if the trainer is killed
# (OOM, exit 137), relaunches with --resume from the last checkpoint.
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results
D=~/workspace/edit-lab/data
CS=~/workspace/edit-lab/candsets
CK=~/workspace/edit-lab/ckpts/coord-spec

# wait for the machine to be free of other heavy python jobs
while pgrep -f "train_lora.py|observe.py" > /dev/null; do sleep 20; done
echo "machine free, starting coordinator redo"

attempt=0
while [ ! -f "$CS/coord-spec/coordinator/training_meta.json" ] && [ $attempt -lt 8 ]; do
  attempt=$((attempt+1))
  echo "=== train attempt $attempt ==="
  $PY -u ~/workspace/edit-lab/train_ckpt.py coordinator \
    --data $D/coordinator_specialized.jsonl \
    --epochs 1 --rank 16 --alpha 32 --lr 2e-4 \
    --save-every 2 --ckpt $CK --resume \
    --out $CS/coord-spec/coordinator >> $R/train_coord_ckpt.log 2>&1
  echo "attempt $attempt exit=$?"
  sleep 5
done

if [ -f "$CS/coord-spec/coordinator/training_meta.json" ]; then
  echo "=== eval coordinator specialized (checkpointed train) ==="
  AGENT_TEAM_ADAPTERS=$CS/coord-spec \
    $PY -u training/observe.py --only coordinator --tag coord_spec1 > $R/coord_spec1.log 2>&1
  echo "eval exit=$?"
else
  echo "TRAINING_FAILED_AFTER_ATTEMPTS"
fi
echo "COORD_REDO_DONE"
