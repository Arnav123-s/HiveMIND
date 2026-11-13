#!/usr/bin/env bash
# Muse's work - Muse's side. Continuous mill loop.
# Arnav's sprint directive (2026-11-12): no batching, no breaks - the mill
# runs continuously through Sun Nov 15, 2026, then stops itself.
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
while true; do
  today=$(TZ=America/Los_Angeles date +%F)
  if [[ "$today" > "2026-11-15" ]]; then
    echo "[mill-loop] sprint window over ($today); exiting"
    exit 0
  fi
  # Yield the lab while the ladder, a growth cycle, or another experiment driver owns it.
  if pgrep -f 'run_scale_ladder|growth_cycle|run_round2|run_jepa' >/dev/null 2>&1; then
    sleep 60
    continue
  fi
  python3 mill/screen.py >> mill/mill-loop.log 2>&1
  sleep 10
done
