#!/usr/bin/env bash
# After the cell pipelines (each stream starts as soon as its inputs are ready; 2 threads each on 4 cores):
#  stream 1 (after the incumbents run): element_match, the smaller cell inside pick_element
#  stream 2 (after pipeline B): factory (clone for a new skill) -> gate -> layer-cut base -> its evaluation
#  then, on a quiet CPU: llama.cpp accuracy + latency of every cell, the organizers, and the comparison
cd "$(dirname "$0")/.."
R=training/reports/cells
(while pgrep -f "training/cells_[i]ncumbents.py" > /dev/null; do sleep 30; done
 CELLS_THREADS=2 AGENT_TEAM_THREADS=2 .venv/bin/python training/cells_pipeline.py element_match > $R/pipeline_C.log 2>&1) &
P1=$!
(until grep -q '=== orders_signup finished' $R/pipeline_B.log; do sleep 30; done
 export CELLS_THREADS=2 AGENT_TEAM_THREADS=2
 .venv/bin/python training/cells_factory.py licence_open --steps 60 > $R/factory.log 2>&1
 .venv/bin/python training/cells_promote.py licence_open --no-runtime >> $R/factory.log 2>&1
 .venv/bin/python training/cells_pipeline.py gate > $R/pipeline_gate.log 2>&1
 .venv/bin/python training/cells_cut.py 25,26,7,9,22,5,4,21 > $R/cut.log 2>&1
 .venv/bin/python training/cells_cut_eval.py route_step next_move quote_pick orders_spend >> $R/cut.log 2>&1) &
P2=$!
wait $P1 $P2
.venv/bin/python training/cells_promote.py --retime > $R/retime.log 2>&1   # quiet CPU: latency is real
.venv/bin/python training/cells_compare.py > $R/compare.log 2>&1
echo "after: done"
