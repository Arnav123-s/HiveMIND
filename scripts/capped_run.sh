#!/bin/bash
# Run a command at low priority inside a memory-capped cgroup scope, so that when the trainer outgrows the runner the
# kernel kills the trainer (the step ends, the slice is lost cleanly) and not the runner agent (g38-g56: 2-4 of 20
# slices a generation ended in "the hosted runner lost communication", no log, a step that never ended).
#
#   scripts/capped_run.sh [--timeout SECONDS] -- command args...
#   scripts/capped_run.sh --limits TOTAL_MB       prints "HIGH_MB MAX_MB" (or "none") and exits
#
# Limits, from the machine's total memory (free -m): Max = total - 1200 MB (the OS, the runner agent and its
# services keep 1.2 GB that the trainer cannot take); High = Max - 512 MB (above it the kernel throttles and reclaims
# the trainer hard before it ever reaches Max). Swap for the trainer is 0: a cgroup that swaps thrashes the disk and
# starves the agent, which is the failure itself. A machine under 3000 MB gets no cap.
# If sudo, systemd-run or the scope does not start (a probe runs first), the command runs plain, still niced, so a
# generation never breaks. The exit status is the command's (137 for a kill by the kernel or by the timeout's -k).
# `timeout` runs inside the scope, as the same user, so it can end what it started.

limits() {
  local total=$1 max high
  if ! [[ "$total" =~ ^[0-9]+$ ]] || [ "$total" -lt 3000 ]; then echo none; return; fi
  max=$(( total - 1200 )); high=$(( max - 512 ))
  echo "$high $max"
}

if [ "$1" = "--limits" ]; then limits "$2"; exit 0; fi

T=""
if [ "$1" = "--timeout" ]; then T=$2; shift 2; fi
[ "$1" = "--" ] && shift
[ $# -gt 0 ] || { echo "usage: capped_run.sh [--timeout S] -- command..." >&2; exit 2; }

pre=(nice -n 10)
command -v ionice >/dev/null 2>&1 && ionice -c3 true >/dev/null 2>&1 && pre=(nice -n 10 ionice -c3)
run=("$@")
[ -n "$T" ] && run=(timeout -k 60 "$T" "$@")

TOTAL=$(free -m 2>/dev/null | awk '/^Mem:/ {print $2}')
read -r HIGH MAX <<< "$(limits "$TOTAL")"
if [ "$HIGH" != none ] && [ -n "$HIGH" ] && command -v systemd-run >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1; then
  scope=(sudo -n -E env "PATH=$PATH" "HOME=$HOME" systemd-run --scope --quiet --uid="$(id -u)" --gid="$(id -g)"
         -p "MemoryHigh=${HIGH}M" -p "MemoryMax=${MAX}M" -p MemorySwapMax=0)
  if "${scope[@]}" true >/dev/null 2>&1; then
    echo "capped_run: memory scope High=${HIGH}M Max=${MAX}M (total ${TOTAL}M), swap 0, nice 10"
    exec "${scope[@]}" "${pre[@]}" "${run[@]}"
  fi
  echo "capped_run: ::warning::could not start a memory scope; running without the cap" >&2
else
  echo "capped_run: no memory cap (limits=${HIGH:-none}, systemd-run/sudo missing); running niced" >&2
fi
exec "${pre[@]}" "${run[@]}"
