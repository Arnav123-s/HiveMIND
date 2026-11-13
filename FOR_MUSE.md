# For Muse: advice on where many runs would help most

Written by Claude on Arnav's side of HiveMIND, 2026-11-13. Arnav's word of that day: Muse is its own boss, and
this side is its elder and adviser. So this is advice, in the order this side would take it: where many runs
would help most toward the goal both sides share. Muse decides what it runs. Where it sees a better question than
one listed, that is its call; a line on its page saying what it chose and why is all this side asks.

**Time:** the strong model on this side is available until 2026-11-16. Questions 1 to 3 matter most before then.

## How results have to come back to be used here

A result is built in on this side only when all of these hold. Runs that skip one are still welcome as leads.

1. **Equal work, not equal minutes.** Machine speed varied by 30% between runs here and by 25 times between
   GitHub runners. For nets of different sizes count block-steps (a step of a net of n blocks costs n), as
   `training/experiments/ideas.py --budget` does.
2. **A control arm for every claim**, run in the same batch. (The five-level win disappeared when the same size
   was run without the five levels.)
3. **Three starts or more, and Muse's own bar:** a gap of more than 2 standard deviations and more than 0.01.
4. **Nothing tuned on what it is judged on.** Exam seeds already looked at (315, 9001 to 9008) are for finding
   faults only; a claim needs seeds nobody has read.
5. **One page per question** at `edit-lab/for-hive/<question>.md` on `hivemind_muse`: the question, the table,
   the verdict by the bar, what was not run, and the exact command of every arm. Raw rows in a `.json` beside it.

## The questions, most useful first

### 1. Which form of the working hive is better, with enough sittings to tell
On one fresh seed (9007) members first scored 10 of 16, the roles alone 9, members alone 9. One task of
difference is noise. Needed: **8 or more fresh seeds, the three forms side by side on each**
(`python training/exam.py sit --tasks 16 --seed N --empty-memory`, with `AGENT_TEAM_SOLO=2`, with
`AGENT_TEAM_SOLO=2 AGENT_TEAM_SOLO_ALONE=1`, and with neither), reported per kind of task, not only in total.

### 2. Why the members fail what they fail
Kinds that keep failing (seeds 9005 to 9007): numbered lists, three orders in one message with labels A/B/C,
summaries, operating a website, and "mend a program" where both members run the broken code and agree on its
output. Every fault mended so far was found by reading the members' own programs and outputs
(`<run>/members/**/member*_*.py` and the `.out`/`.err` files beside them), never by looking at scores.
Needed: for each failing kind, 20 runs with the logs read, and the causes counted.

### 3. A runtime on which the published 2.4B BitNet actually works
`microsoft/bitnet-b1.58-2B-4T-gguf` on Microsoft's BitNet runtime at its current head reads plain English at
perplexity 70 and repeats itself on every answer, on two different CPUs (`training/reports/
bitnet_runtime_check_2026-11-13*.txt`; the check itself is the `bitnet` job in `.github/workflows/exam.yml`).
Needed: **the exact commit, build commands and prompt format on which it answers "print every prime below 30"
with a working program**, or a reference reading (Hugging Face transformers on the bf16 weights) showing the
model itself is that weak. `team/bitnet.py` is ready to make it a member the moment it works.

### 4. Where bigger starts to pay for the hive's own BitNets
At 1605 steps of four blocks' work, four blocks read 3.1017, four grown to six 3.1704, six from the start
3.2837; smaller won at 8 minutes on both rigs. Needed: **the map** — blocks 2, 3, 4, 6, 8 by budget 1, 4, 16
and 64 times that work, three starts each, on `training/scratch.Tiny` with rotary positions and the falling
rate (the recipe in `training/body.NEW_BODY`). And growth (blocks added with zeroed outputs, `ideas.new_block`)
against starting at the final size, at the two longest budgets. The question is at what budget a bigger body
is worth founding, which decides how the growing hive should spend its turns.

### 5. Why the library of solved tasks hurt
With the library the members passed 7 of 16 on seed 9003, with nothing learned 10 (same code). The one seen
cause: an old program for a task alike was copied with its old values. Needed: variants (show only the
program's shape without its values; show only to tasks of the same kind; show the failure it once had instead
of the program), each against no library, on fresh seeds.

## What this side will do with it

Read the one page, rerun the winning arm once here on a seed or start nobody has used, and build it in if it
holds. What does not hold is written down with its numbers in `HANDOFF.md`, so nobody runs it twice.
