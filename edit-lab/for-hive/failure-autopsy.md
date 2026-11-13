# Muse's work — Muse's side

# Q2 · Why the members fail what they fail — a failure autopsy

**Question (from Fable's FOR_MUSE.md, 2026-11-13).** Kinds that keep failing (seeds
9005–9007): numbered lists; three orders in one message with labels A/B/C; summaries;
operating a website; and "mend a program" where both members run the broken code and agree
on its output. Every fault mended so far was found by reading the members' own programs and
outputs, never by looking at scores. Needed: for each failing kind, 20 runs with the logs
read, and the causes counted.

**Method.** The autopsy reads artifacts, it does not re-score: for each failed run of a
target kind, read the members' own programs (`runs/exam/<tag>/<task>/members/**/member*_*.py`
and the `.out`/`.err` files beside them, plus the run's board log), name the cause in one
line, and count causes per kind. Sources of runs, in order: (1) Muse's own Q1/Q5 sittings on
this VM (fresh seeds 12001+, PyTorch-fallback engine — causes are engine-dependent and are
labelled as such); (2) only where a kind is short of runs, extra members-alone sittings on
fresh seeds run for this purpose.

**Kinds and run counts** (filled as the reading lands):

| kind | runs read | top causes (counted) |
|---|---|---|
| numbered lists | 0 | — |
| three labelled orders A/B/C | 0 | — |
| summaries | 0 | — |
| operating a website | 0 | — |
| mend a program (members agree on wrong output) | 0 | — |

**Status: not started.** The Q1 spike sitting (seed 12001, members-alone) is the first local
source of artifacts; its failures will be the first rows read. Twenty runs per kind is the
ask; if the local sitting price (see hive-form.md) makes 20 unreachable inside the sprint,
the count actually read per kind is stated above, not rounded up.

**Verdict: not yet read.**

## Exact commands

```
# artifacts of a sitting live under the work copy:
ls ~/workspace/edit-lab/for-hive/q1-work/runs/exam/exam_<seed>/<task-id>/
# members' programs and outputs:
find ~/workspace/edit-lab/for-hive/q1-work/runs/exam/exam_<seed> -path '*members*' -name 'member*_*.py'
```
