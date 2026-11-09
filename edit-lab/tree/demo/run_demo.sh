#!/usr/bin/env bash
# Runs the end-to-end demo: one prompt (demo/TASK.md) to the whole team.
# Trace, files, screenshots, report and a memory log land in demo/run/.
set -uo pipefail
cd "$(dirname "$0")/.."
rm -rf demo/run.prev; [ -d demo/run ] && mv demo/run demo/run.prev
mkdir -p demo/run
base=$(free -m | awk '/Mem:/{print $3}')
( peak=$base; while true; do u=$(free -m | awk '/Mem:/{print $3}'); [ "$u" -gt "$peak" ] && peak=$u;
  echo "baseline_used_mb=$base peak_used_mb=$peak team_peak_mb=$((peak-base))" > demo/run/memory.txt; sleep 5; done ) &
sampler=$!
start=$(date +%s)
.venv/bin/python -m team --file demo/TASK.md --run-dir demo/run --approve never
echo "wall_seconds=$(( $(date +%s) - start ))" >> demo/run/memory.txt
kill $sampler
