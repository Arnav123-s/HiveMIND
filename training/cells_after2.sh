#!/usr/bin/env bash
# Continues the chain of training/cells_after.sh (whose two streams keep running):
#  stream 3 (after stream 2): the factory makes two new skills' cells by cloning (orders_any, licence_open)
#  then, once every stream is done, on a quiet CPU: llama.cpp accuracy + latency of every cell, organizers, comparison
cd "$(dirname "$0")/.."
R=training/reports/cells
S1=${1:?stream 1 pid}; S2=${2:?stream 2 pid}
(while kill -0 $S2 2>/dev/null; do sleep 30; done
 export CELLS_THREADS=2 AGENT_TEAM_THREADS=2
 for k in orders_any licence_open; do
   .venv/bin/python training/cells_factory.py $k --steps 60 > $R/factory_$k.log 2>&1
   .venv/bin/python training/cells_promote.py $k --no-runtime >> $R/factory_$k.log 2>&1
 done) &
P3=$!
wait $P3
while kill -0 $S1 2>/dev/null; do sleep 30; done
.venv/bin/python training/cells_promote.py --retime > $R/retime.log 2>&1   # quiet CPU: latency is real
.venv/bin/python training/cells_compare.py > $R/compare.log 2>&1
echo "after: done"
