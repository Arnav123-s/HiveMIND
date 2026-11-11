#!/usr/bin/env bash
# resume.sh: start HiveMIND's work again on a machine set up by scripts/cloud_setup.sh.
#   bash scripts/resume.sh status        what is here: branch, hive size, last measurements, what is running
#   bash scripts/resume.sh grow [MIN]    the growing hive takes its turns in the background (budget MIN minutes,
#                                        default 100, under the 2-hour cut a cloud session puts on background jobs);
#                                        saved after every body's turn; log in logs/grow.log
#   bash scripts/resume.sh exam [N]      the working hive sits N fresh exam tasks (default 6) in the background;
#                                        log in logs/exam.log, result in training/reports/exams/
#   bash scripts/resume.sh ask "TASK"    the working hive does one task now (in the foreground)
#   bash scripts/resume.sh stop          stop what this script started
# Never run two trainings at once on a 4-core machine (a 6-minute run took an hour). Nothing here pushes to GitHub:
# a session saves the hive with `python training/hive_state.py save` only when Arnav says so.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; [ -x "$PY" ] || { echo "run scripts/cloud_setup.sh first"; exit 1; }
mkdir -p logs
running() { [ -f "logs/$1.pid" ] && kill -0 "$(cat "logs/$1.pid")" 2>/dev/null; }
start() {  # name, command...
    local name=$1; shift
    if running grow || running exam; then echo "something is already running (bash scripts/resume.sh status)"; exit 1; fi
    nohup "$@" > "logs/$name.log" 2>&1 & echo $! > "logs/$name.pid"
    echo "$name started (pid $!); follow it with: tail -f logs/$name.log"
}
case "${1:-status}" in
  status)
    echo "branch: $(git rev-parse --abbrev-ref HEAD) at $(git log -1 --format='%h %s' | cut -c1-90)"
    du -sh cells/scratch 2>/dev/null | sed 's/^/grown hive on disk: /' || echo "no grown hive here"
    tail -n 2 training/reports/hive_growth.jsonl 2>/dev/null | cut -c1-200 | sed 's/^/growth: /' || true
    tail -n 2 training/reports/exams.jsonl 2>/dev/null | cut -c1-200 | sed 's/^/exam: /' || true
    for j in grow exam; do running $j && echo "running: $j (pid $(cat logs/$j.pid))"; done; true ;;
  grow)
    start grow $PY -m team body --minutes 10 --births 3 --budget "${2:-100}" ;;
  exam)
    [ -d cells/gguf ] || { echo "the working hive is not installed: bash scripts/cloud_setup.sh (without --light)"; exit 1; }
    start exam $PY training/exam.py sit --seed "${SEED:-$RANDOM}" --tasks "${2:-6}" ;;
  ask)
    shift; $PY -m team "$*" --approve never ;;
  stop)
    for j in grow exam; do running $j && kill "$(cat logs/$j.pid)" && echo "stopped $j"; rm -f logs/$j.pid; done; true ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
