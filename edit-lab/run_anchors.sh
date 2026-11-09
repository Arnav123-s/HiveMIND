#!/bin/bash
# Anchor reproductions: base + rejected edits, unmodified harness, copied tree.
cd ~/workspace/edit-lab/tree || exit 1
export HF_HOME=~/workspace/edit-lab/hf
export AGENT_TEAM_ENGINE=hf
export HF_HUB_OFFLINE=1
PY=~/workspace/edit-lab/venv/bin/python
R=~/workspace/edit-lab/results

echo "=== anchor 1: base coordinator ==="
$PY training/observe.py --only coordinator --tag anchor_base_coord --no-adapters > $R/anchor_base_coord.log 2>&1
echo "exit=$?"

echo "=== anchor 2: base researcher ==="
$PY training/observe.py --only researcher --tag anchor_base_res --no-adapters > $R/anchor_base_res.log 2>&1
echo "exit=$?"

echo "=== anchor 3: rejected coordinator (original adapter) ==="
AGENT_TEAM_ADAPTERS=~/workspace/edit-lab/candidates/orig-rejected \
  $PY training/observe.py --only coordinator --tag anchor_rej_coord > $R/anchor_rej_coord.log 2>&1
echo "exit=$?"

echo "=== anchor 4: original researcher (repo adapters) ==="
$PY training/observe.py --only researcher --tag anchor_orig_res > $R/anchor_orig_res.log 2>&1
echo "exit=$?"

echo "ANCHORS_DONE"
