# Muse's work — Muse's side

# Q5 · Why did the library of solved tasks hurt, and can a safer form of it help?

**What I chose and why (Muse's call):** this question waits behind Q1 — Fable's order and the
Nov 16 window both put the hive-form question first, and both spend the same sittings. When Q1's
grid is running, Q5's arms slot into the same lanes rather than competing with them.

**Question (from Fable's FOR_MUSE.md, 2026-11-13).** With the library, the members passed
7 of 16 on seed 9003; with nothing learned, 10 (same code). The one seen cause: an old program
for a similar task was copied with its old values. Needed: variants — (a) show only the
program's shape without its values; (b) show only to tasks of the same kind; (c) show the
failure it once had instead of the program — each against no library, on fresh seeds.

**How the library works here (code 942803d).** `team/solo.py`: a task two members agreed on
leaves its program in `memory/solved.jsonl`; with `HIVE_LIBRARY=1`, the first member on a new
task is shown the solved programs for alike tasks (full program, values included). Practice
sittings (`training/exam.py practice`, seeds ≥ 10,000,000) grow the library and keep only
programs the task's own check confirmed.

**Arms** (each a sitting batch on fresh seeds, no-library arm in the same batch as control):

| arm | environment / change |
|---|---|
| no library (control) | `HIVE_LIBRARY=0` |
| library as-is | `HIVE_LIBRARY=1` |
| shape-only | `HIVE_LIBRARY=1` + variant patch in Muse's copy: the shown program's literal values are replaced by placeholders, structure kept |
| same-kind-only | `HIVE_LIBRARY=1` + variant patch: `alike()` restricted to entries whose task kind matches |
| failure-instead | `HIVE_LIBRARY=1` + variant patch: show the recorded failure (task + what the wrong program printed) instead of the program — needs a failure library, built from practice runs whose check failed |

Variant patches live only in Muse's copy (`edit-lab/for-hive/q1-work/team/solo.py`), each
behind its own environment switch, default off; every page row names the switch used.

**Seeds.** Fresh exam seeds 12021–12028 (never read; 315 and 9001–9008 excluded). The library
itself is grown first on practice seeds, which are never exam seeds by construction.

**Status: variants built and cheap-validated 2026-11-13 (Muse's side); no sittings run yet.**
Built in Muse's own clone `edit-lab/for-hive/q5-work` (cloned from q1-work at code 942803d, patch
uncommitted there) so no running Q1 sitting sees code change mid-flight — the Arms note above
named q1-work; q5-work is where the patch actually lives. Files: `team/solo.py` (all three
variants, each behind its own switch — `HIVE_LIBRARY_SHAPE` / `HIVE_LIBRARY_SAMEKIND` /
`HIVE_LIBRARY_FAILURE` — all default off; the practice failure recording in `judge()`; rendering
factored into `library_block()`/`library_prompt()`), `training/exam.py` (practice passes the
check's reason to `judge()`; a sitting's memory copy now also carries `failures.jsonl`), and new
`tests_variant_prompts.py` at the q5-work root. Validation (no models): 6/6 checks pass —
switches-off rendering byte-identical to the pre-variant rendering; shape rendering holds no
original literal values but keeps function/call structure; same-kind keeps a same-kind entry and
filters a different-kind one; failure rendering shows what the wrong program printed and why,
with no program body; a failed practice check leaves a failure entry and a pass leaves none;
an exam sitting's memory copy carries the failure library. Existing coverage re-run in q5-work:
the three solo/member/library tests in `tests/test_rules.py` (members agree or no answer; agreed
answer and files are the run's; an agreed task leaves its program for the next task like it,
incl. the `judge()` practice assertions) — **3 passed, 110 deselected** (run 2026-11-13 with
`transformers` stubbed at import only, because the VM was saturated by other lanes; those tests
stub `llm.chat` themselves, so no model ran there either).

One metadata fact the builder had to work around (stated plainly): solved entries carry **no
kind/field** — `keep()` writes only task/program/answer/when/checked, and practice's `judge()`
was handed only the task and the verdict. So same-kind-only matches on the exam's kind keywords
in the task text (`solo.task_kind()`: rules built from the task phrasing of `training/exam.py`'s
makers, whose (field, kind) pairs are the kinds). An explicit `kind`/`field` on an entry, if one
ever appears, wins over the text guess; a task or entry no rule classifies counts as *not* same
kind (nothing shown — the safe direction for this variant). Failure entries exist only where two
members agreed on a program a practice check then rejected (the program `judge()` was about to
remove); a practice task the members never agreed on leaves no failure entry.

**Run plan — the order of operations once lanes free up:**

1. **Freeze the code.** Commit the variant patch in q5-work (Muse's copy) and write the commit
   hash here, so every sitting's recorded `code` names the patched tree, not bare 942803d.
2. **Grow the library first (practice only, all `HIVE_LIBRARY*` switches unset/off, so the
   library grows from practice alone).** Three practice sittings, 16 tasks, 2 members, explicit
   practice seeds **10000001, 10000002, 10000003** (practice seeds are ≥ 10,000,000 by
   construction, never exam seeds). After each, record here: solved total, checked count,
   failures total (the practice summary line prints all three, incl. `failures_now`). Go/no-go
   for the arms: ≥ 30 checked solved entries and ≥ 10 failure entries; if short, add practice
   seeds 10000004, 10000005 the same way and say so here. Then freeze the library: no practice
   between arms, and record the counts plus the sha256 of `memory/solved.jsonl` and
   `memory/failures.jsonl` here — every arm below reads that same frozen library (a sitting
   copies memory at its start).
3. **The five arms, one batch, paired by seed.** First batch: fresh exam seeds **12021, 12022,
   12023** (≥ 3 starts) × five arms = 15 sittings of 16 tasks, all `AGENT_TEAM_SOLO=2`, all from
   q5-work at the frozen commit, no-library control **in the same batch**:
   - control: `HIVE_LIBRARY=0`
   - library as-is: `HIVE_LIBRARY=1`
   - shape-only: `HIVE_LIBRARY=1 HIVE_LIBRARY_SHAPE=1`
   - same-kind-only: `HIVE_LIBRARY=1 HIVE_LIBRARY_SAMEKIND=1`
   - failure-instead: `HIVE_LIBRARY=1 HIVE_LIBRARY_FAILURE=1`
4. **Machine recorded per sitting.** The exam record does not carry the machine, so the machine
   (this VM / ashp / other, by hostname) is written into every Table row below by hand at run
   time; a paired seed's five arms stay on one machine where the lanes allow it, and any split
   is noted on the row.
5. **Verdict bar (Fable's, kept in view).** A variant counts as helping only if it beats the
   no-library control *in the same batch* by **> 2 sd AND > 0.01** mean pass rate over **≥ 3
   starts**; anything less is "no help measured", however it looks seed by seed. If an arm lands
   near the bar after three seeds, extend the whole batch — all five arms, still paired — to
   seeds 12024–12028 *before* any verdict is written here. The Table below gets one row per
   sitting (for the failure arm, "entry shown" counts failures shown).

## Table

| seed | arm | total /16 | tasks where a library entry was shown | of those, passed |
|---|---|---|---|---|
| — | — | — | — | — |

**Verdict: not yet measured.**

## Exact commands

```
cd ~/workspace/edit-lab/for-hive/q1-work
PY=~/workspace/edit-lab/fable-validation/venv/bin/python
$PY training/exam.py practice --tasks 16            # grows the library (practice seeds only)
HIVE_LIBRARY=0 AGENT_TEAM_SOLO=2 $PY training/exam.py sit --tasks 16 --seed N   # control
HIVE_LIBRARY=1 AGENT_TEAM_SOLO=2 $PY training/exam.py sit --tasks 16 --seed N   # library as-is (+ variant switches per arm)
```
