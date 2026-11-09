#!/bin/bash
# Micro-specialist phase: train the 5 coordinator micro cells
# (checkpointed, auto-resume), merge composite v1, eval it.
# Idempotent: skips any leg whose output already exists.
set -u
EL=~/workspace/edit-lab
VENV=$EL/venv/bin/python
export HF_HOME=$EL/hf HF_HUB_OFFLINE=1 AGENT_TEAM_ENGINE=hf
cd $EL/tree || exit 1

train_until_done() {  # $1=name $2=datafile $3=outdir $4=ckptdir $5..=extra args
  local name=$1 data=$2 out=$3 ckpt=$4; shift 4
  if [ -f "$out/training_meta.json" ]; then echo "$name already trained"; return 0; fi
  local attempt=1
  while [ ! -f "$out/training_meta.json" ] && [ $attempt -le 10 ]; do
    echo "--- $name attempt $attempt $(date +%T) ---"
    $VENV -u $EL/train_ckpt.py coordinator --data "$data" --epochs 1 --rank 4 --alpha 8 \
      --lr 5e-4 --save-every 2 --ckpt "$ckpt" --resume --out "$out" "$@" \
      >> $EL/results/micro_$name.log 2>&1
    echo "$name attempt $attempt exit=$?"
    attempt=$((attempt+1)); sleep 5
  done
  [ -f "$out/training_meta.json" ]
}

for cell in size_band pick_researcher pick_browser pick_coder for_each; do
  train_until_done "$cell" "$EL/data/micro/$cell.jsonl" \
    "$EL/candsets/micro-$cell/coordinator" "$EL/ckpts/micro-$cell" \
    || { echo "MICRO TRAIN FAILED: $cell"; exit 1; }
done
echo "ALL MICRO TRAINS DONE"

# composite v1: 5 micro cells @1.0 + specialized monolith @0.25 (style anchor)
if [ ! -f $EL/candsets/coord-composite-v1/coordinator/adapter_model.safetensors ]; then
  $VENV $EL/merge_n.py $EL/candsets/coord-composite-v1/coordinator \
    $EL/candsets/micro-size_band/coordinator:1.0 \
    $EL/candsets/micro-pick_researcher/coordinator:1.0 \
    $EL/candsets/micro-pick_browser/coordinator:1.0 \
    $EL/candsets/micro-pick_coder/coordinator:1.0 \
    $EL/candsets/micro-for_each/coordinator:1.0 \
    $EL/candsets/coord-spec/coordinator:0.25 || exit 1
fi
echo "COMPOSITE V1 BUILT"

if [ ! -f $EL/results/coord_composite_v1.json ]; then
  AGENT_TEAM_ADAPTERS=$EL/candsets/coord-composite-v1 \
    $VENV -u training/observe.py --only coordinator --tag coord_composite_v1 \
    > $EL/results/coord_composite_v1.log 2>&1
  echo "composite eval exit=$?"
  cp -n training/reports/coord_composite_v1.json $EL/results/ 2>/dev/null
fi
echo "MICRO PHASE DONE"
