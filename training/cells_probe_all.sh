#!/usr/bin/env bash
# Probe maps for every skill, one job at a time (4 cores: parallel jobs only slow each other down)
cd "$(dirname "$0")/.."
for s in "$@"; do
  .venv/bin/python training/cells.py probe "$s" 2>&1 | grep -v "Warning\|Loading\|detach\|attr\[k\]" > "training/reports/cells/probe_$s.txt"
  echo "done $s"
done
