#!/usr/bin/env bash
# Runs the end-to-end demo: one prompt (demo/TASK.md) to the whole team.
# Trace, files, screenshots and report land in demo/run/.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m team --file demo/TASK.md --run-dir demo/run --approve never
