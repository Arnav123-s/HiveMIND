#!/bin/bash
# Muse's work, Muse's side. Run B driver: train with checkpoints, kill -9 at the
# step-20 checkpoint (simulated runtime restart), resume in a fresh process to step 40.
set -u
cd ~/workspace/edit-lab/bitnet-lab/compute
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
PY=~/workspace/edit-lab/fable-validation/venv/bin/python
CK=proof/ckptB.pt
rm -f "$CK" proof/runB1.log proof/runB2.log
$PY train_ckpt.py --arm layered_half --rope --seed 0 --steps 40 --minutes 60 \
  --tag proofB --batch 16 --held-n 32 --ckpt-every 10 --ckpt-path "$CK" > proof/runB1.log 2>&1 &
PID=$!
echo "B phase1 pid $PID"
for i in $(seq 1 600); do
  grep -q "CKPT step 20" proof/runB1.log 2>/dev/null && break
  kill -0 $PID 2>/dev/null || { echo "phase1 exited before ckpt20"; exit 1; }
  sleep 5
done
grep "CKPT" proof/runB1.log
sleep 2  # let it get partway into steps 21+ so the kill lands mid-training, not on a boundary
kill -9 $PID
wait $PID 2>/dev/null
echo "phase1 killed with -9; checkpoint on disk:"
ls -l "$CK" || { echo "NO CHECKPOINT SURVIVED KILL"; exit 1; }
$PY train_ckpt.py --arm layered_half --rope --seed 0 --steps 40 --minutes 60 \
  --tag proofB --batch 16 --held-n 32 --ckpt-every 10 --ckpt-path "$CK" --resume-from "$CK" \
  --series proof/runB-series.json > proof/runB2.log 2>&1
echo "phase2 exit=$?"
cat proof/runB2.log
ls -l "$CK" 2>/dev/null && echo "CKPT STILL PRESENT (bad)" || echo "CKPT RETIRED ON COMPLETION (good)"
