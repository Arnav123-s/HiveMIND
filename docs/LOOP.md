# The maintainer's loop

How the agent that maintains HiveMIND works, cycle after cycle, and what each cycle taught about working well. Read
this first in every cycle; add to it at the end of every cycle. `docs/loop_log.csv` holds one row per cycle, and the
dashboard "HiveMIND Progress" (claude.ai artifact Xi5BfLZnLLzvkhZJK72Hvr) draws it beside the hive's own scores.

## One cycle

0. **Read `docs/AGENTS.md` and the other agents' open pull requests.** Another agent works here too: merge `main`
   in if it moved, stay off what it owns, and add a log line when you start or change course.
1. **Read the newest results first.** The last generation's record (`training/reports/generations.jsonl`), every
   GitHub run since the last cycle, and the members' own programs in the pulse's `gate-work-*` artifacts.
2. **Group the failures by cause, not by task.** A cause that ends many tasks the same way on every turn is the
   one to fix first.
3. **Fix the cause where it lives.** The runtime (what a member's program runs in) before the orders, the orders
   before training.
4. **Prove it cheaply, then really.** Replay the members' real failing programs through the changed code (seconds),
   the test suite (a minute), then one whole run of the changed path (a re-sat exam or a generation).
5. **Ship.** Push, update the pull request; merge only with the owner's go-ahead.
6. **Record the cycle.** One row in `docs/loop_log.csv` (cycle id `A-<n>`, agent, session, branch, pull request,
   the run ids used), every run started in `docs/runs.csv` with its purpose, the dashboard's data refreshed, and below: what worked,
   what wasted time, and the rule that would have prevented the waste.

## Rules learned (newest last)

- **Read the members' programs, not the score.** Cycle 1: 32 tasks' programs showed five causes in twenty minutes;
  the score alone said only "hard tasks fail".
- **Replay real failures before running anything big.** Cycle 1: the members' own failing programs, run unchanged
  through the new runtime, proved four fixes in seconds.
- **Before dispatching a workflow, check what each input really does, and that the run it points at holds what is
  needed.** Cycle 1 lost two runs: a re-sit with `cells_from_run` still waited two hours for practice (fixed in the
  workflow), and one pointed at a cancelled run with no cells. List the target run's artifacts first.
- **A trial (`trial: 1`) grows no trunk.** To re-sit a line generation exactly, sit it locally with that
  generation's members (`training/exam.py sit --level mixed --tasks 16 --seed 2000NNN1 --empty-memory`).
- **Code written inside a string (the program hook) needs a test that it parses.** Cycle 1: a `\n` became a real
  newline in the generated hook and every program printed an error first. `tests/test_given.py` now parses it.
- **Start long checks in parallel, and do the next piece of work while they run.**
