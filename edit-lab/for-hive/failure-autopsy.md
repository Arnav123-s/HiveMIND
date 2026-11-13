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

**This page is the BREADTH autopsy (Muse's side).** Causes are counted across Muse's own
fresh-seed sittings. Fable's side is doing the DEPTH autopsy itself — the fourteen failed
tasks of seeds 9005–9007, from its own logs. That work is separate and is **not duplicated
here**: Fable's runs were read only to take the cause labels (below), never counted as runs
on this page.

**Engine that produced these runs: the PyTorch fallback** (`team/llm.py` PyTorch path,
fable-validation venv, OMP/MKL threads = 2, this VM's shared 1.5 CPU). No run counted here
came from the llama.cpp engine. Sitting form: members alone (`AGENT_TEAM_SOLO=2`),
`--empty-memory`, code `942803d`.

**Exception added 2026-11-13 (~09:32 UTC): the `exam_12002` runs merged below are ashp
runs** — members-alone, PyTorch-fallback engine, on ashp (Muse's laptop), not this VM,
code `c256322` (a docs-only diff from `942803d`). Their artifacts sit on this VM at
`~/workspace/edit-lab/for-hive/ashp-artifacts/exam_12002/<task>/`. They are labelled ashp
wherever they are counted, so the engine/host difference stays visible.

## Fable's causes, verbatim (the label set for this page)

From `~/workspace/fable-audit-copy/HANDOFF.md`, "Members still fail, seen on 9005 to 9007"
(lines 252–256):

- numbered lists ("follow a form to the letter": not confirmed)
- three orders in one message (answers right, labels A/B/C not kept)
- summaries (not confirmed; the looser comparison of e312329 is not measured yet: seed
  9008 is its sitting)
- operating a website
- "mend a program" where both members ran the broken program and agreed on its output

From the same file, "Members (team/solo.py), found by logging every program and reply of
four failed tasks here" (lines 279–282):

- DONE came back as a program (crashed, or `print("DONE")` replaced a right answer)
- a finished program was sent again until the turns ran out
- answers were compared by their numbers only
- a typed-out answer ("A: 65 / B: dnarg") was run as a program

Supporting, from "the exam pairs, and two mistakes of the session" (lines 222–236):
members agreeing on wrong answers (seed 9002, with the library); the library shown to
every member — they copied the same old program, values and all, and agreed on the same
wrong answer (mend applied: only member 1 sees it); the longer wording of what a member is
asked after each program made members rewrite right programs (put back).

Labels used below are Fable's, shortened only in the JSON keys; a new label is marked NEW.

## Kinds and run counts

Read at 2026-11-13 ~05:53 UTC, extended ~06:36, ~07:54 and ~08:35 UTC with the VM
sitting, then ~09:32 UTC with five failed ashp `exam_12002` tasks merged in. Sitting
`exam_12001` (16 tasks) was still running — task `e12001_04` in progress at its latest
extension — so this table counts exactly what was complete and read:
**9 tasks completed and read, 9 failed, 0 passed** (4 from `exam_12001` on this VM,
5 from `exam_12002` on ashp). Nothing is rounded up toward the 20-per-kind ask.

| kind | runs read | top causes (counted) |
|---|---|---|
| numbered lists | 0 | — (seed 12001 drew no numbered-list task at all — see below) |
| three labelled orders A/B/C | 0 | — (its one task, e12001_07, not yet complete at read time) |
| summaries | 1 | summaries (not confirmed) (1) — ashp e12002_13 |
| operating a website | 1 | every member guessed a wrong category URL and resent the same failing program (1) — ashp e12002_15 |
| mend a program (members agree on wrong output) | 0 | — (its one task, e12001_04, not yet complete at read time) |
| other kinds | 7 | NEW: timed out at 2400 s before any member finished a first program (4); NEW: fetched what it could state/compute, then resent the failed fetch (2); finished program sent again until turns ran out (1) |

Seed 12001's draw, by autopsy kind (from `training/exam.py show --seed 12001`, so the next
reader knows what this sitting can still yield): mend = e12001_04; three labelled orders =
e12001_07; summaries = e12001_08; operating a website = e12001_05 (scrape a page to a CSV)
and e12001_09 (operate a website); other kinds = e12001_00, _01, _02, _03, _06, _10, _11,
_12, _13, _14, _15. **Numbered lists cannot come from this sitting:** both "follow a form
to the letter" draws landed on the "one word" subkind (e12001_10, e12001_11), not the
numbered-list subkind. That kind needs a later seed or a dedicated sitting.

Seed 12002's merged draw, by autopsy kind (only the five failed tasks handed over for
this merge — not a full inventory of that sitting): summaries = e12002_13;
operating a website = e12002_15 (websites/scrape); other kinds = e12002_00 (knowledge),
e12002_10 (languages/translate) and e12002_12 (live facts). These runs are ashp,
members-alone, PyTorch-fallback engine, code `c256322` (docs-only diff from `942803d`).

## Causes summary

Nine failed runs have been read so far. The first four (all `exam_12001`, this VM) share
one cause, **new against Fable's list**; the five ashp `exam_12002` runs merged
~09:32 UTC follow them, in task order within their sitting:

- **e12001_00 (other kinds — live facts: the licence of microsoft/deberta-v3-base).**
  `exam.json`: `ok=false`, `why: "licence mit in the answer"`, `seconds: 2405`,
  `note: "timed out after 2400 s"`, `answer: ""`. The members folder holds only `TASK.md`
  and `board.db`; the board holds **0 events, 0 steps, 0 facts, 0 artifacts**, and no
  `member*_*.py`, `.out` or `.err` file was ever written. Member 1 never finished its first
  program in 40 minutes, so no member-level cause from Fable's list (not confirmed, DONE as
  a program, typed-out answer run as a program, …) can be assigned — there is no member
  output to read. The cause, in one line: **the task hit the exam's 2400 s limit before any
  member produced a program; engine-bound (PyTorch-fallback generation on this VM), not a
  member cause.** Whether later tasks of this sitting complete inside the limit is the
  first thing the next reader will learn; if they also time out empty, this "cause" is a
  property of the engine on this machine, and the breadth autopsy of member behaviour
  proper starts only with the first task that leaves member artifacts behind.

- **e12001_01 (other kinds — code: write and run a program; count the words with more
  than four letters in 'the quick brown fox jumps over the lazy dog', wants 3).**
  `exam.json`: `ok=false`, `why: "wants 3; the answer's numbers: []"`, `seconds: 2400`,
  `note: "timed out after 2400 s"`, `answer: ""`. Same shape as e12001_00: the members
  folder holds only `TASK.md` and `board.db` (0 events, 0 steps, 0 facts, 0 artifacts)
  and no member program or output was ever written. Same cause: **the task hit the
  exam's 2400 s limit before any member produced a program; engine-bound, not a member
  cause.** Two of two completed tasks have now timed out empty, which strengthens the
  read that this is a property of the engine on this machine.

- **e12001_02 (other kinds — knowledge: greatest common divisor of 56 and 128, wants 8).**
  `exam.json`: `ok=false`, `why: "wants 8; the answer's numbers: []"`, `seconds: 2400`,
  `note: "timed out after 2400 s"`, `answer: ""`. Same empty shape again (board 0 events,
  no member program or output). This run also spans the incident the sitting owner
  recorded in `hive-form.json`: the VM rebooted mid-task (~07:11 UTC), the owner used
  the one permitted restart (same env, `-r2` log/pid), the empty task shell was removed
  and the task re-ran clean for the full 2400 s before timing out. Same cause:
  **the task hit the exam's 2400 s limit before any member produced a program;
  engine-bound, not a member cause.** Three of three completed tasks have now timed
  out empty.

- **e12001_03 (other kinds — units: how many miles are 393 kilometres, wants 244.2).**
  `exam.json`: `ok=false`, `why: "wants 244.2; the answer's numbers: []"`,
  `seconds: 2400`, `note: "timed out after 2400 s"`, `answer: ""`. Same empty shape
  (board 0 events, no member program or output). Same cause: **the task hit the exam's
  2400 s limit before any member produced a program; engine-bound, not a member
  cause.** Four of four completed tasks have now timed out empty.

- **e12002_00 (other kinds — knowledge: chemical symbol and atomic number of mercury;
  FAIL, 1170 s; ashp).** **NEW cause: fetched what it could state/compute, then resent
  the failed fetch.** Members answered a directly-statable fact by fetching external
  APIs/Wikipedia instead; every fetch failed (DNS failures; one Wikipedia scrape
  crashed with a cp1252 UnicodeEncodeError — `events.jsonl` shows `UnicodeEncodeError:
  'charmap' codec can't encode character '↑'`) and the same failing programs were
  resent — spot-checked on the VM: `member2_1.py` and `member2_2.py` are byte-identical
  Wikipedia scrapes. No member ever produced an answer (`exam.json`: `ok=false`,
  `answer: "No member got as far as an answer."`).

- **e12002_10 (other kinds — languages/translate: "The library closes at nine on
  Fridays." into French; FAIL, 808 s; ashp).** **NEW, same cause: fetched what it could
  state/compute, then resent the failed fetch.** Nobody translated directly — a
  Wikipedia fetch 404'd and was resent identically (`member1_2.py` = `member1_3.py`,
  spot-checked); a translation API was called with a wrong JSON key
  (`data['response']['translatedText']` → `KeyError: 'response'`, repeated); one member
  printed an English datetime string instead of a translation ("Library closes at
  2026-11-12 09:00:00 on Fridays."). Members never agreed → not confirmed.

- **e12002_12 (other kinds — live facts: licence of sentence-transformers/
  all-MiniLM-L6-v2 on Hugging Face; FAIL, 2401 s timeout; ashp).** **Fable's label: a
  finished program was sent again until the turns ran out.** Members got the HF API
  JSON but assumed a wrong schema (`data["info"]["license"]` → KeyError), alternating
  that broken extraction with printing the first 800 chars (`print(str(data)[:800])`,
  cut off before the licence) across all turns — spot-checked: members 1 and 2 each
  alternate two byte-identical program shapes turn by turn.

- **e12002_13 (summaries — writing/summary; FAIL, 1567 s; ashp).** **Fable's kind:
  summaries (not confirmed).** Only member 1 attempted it, producing a multi-sentence
  near-copy with a mangled date ("closed in 3/13"); member 2 fetched Wikipedia for the
  fictional subject (403 / "Failed to fetch text", resent identically); member 3 ran an
  unrelated version/date program, resent identically; no agreement.

- **e12002_15 (operating a website — websites/scrape: CSV of Poetry books on
  books.toscrape.com; FAIL, 1028 s; ashp).** **Fable's kind: operating a website.**
  Every member guessed a wrong category URL (three different wrong paths, all
  404/empty) and resent the same failing programs; one member's regex program printed
  nothing twice and never wrote a CSV (`exam.json`: `why: "no CSV made"`).

**Cross-cutting pattern, named and counted: "fetched what it could state/compute, then
resent the failed fetch" — 2 full runs (e12002_00, e12002_10), plus 1 partial
(e12002_15; 3 runs touched in all).** In e12002_00 and e12002_10 members reached for an
external fetch for something they could state or compute directly, then resent the
failed fetch. e12002_15 is only partial: the resending half fits, but there the fetch
itself was the task. The pattern label is used as the primary cause only for the two
full runs, so the count stays honest.

Causes from Fable's list are now counted on Muse's side: summaries (not confirmed)
(1), operating a website (1, as a kind, with the wrong-URL/resend cause above), and
"finished program sent again until turns ran out" (1, in other kinds). Three of the
five target kinds still have 0 runs read (numbered lists, three labelled orders A/B/C,
mend a program).

**Status: in progress.** First breadth read landed 2026-11-13 (~05:53 UTC) while
`exam_12001` was still running (1 of 16 tasks complete); extended ~06:36 UTC with
e12001_01 (2 of 16), ~07:54 UTC with e12001_02 (3 of 16) and ~08:35 UTC with
e12001_03 (4 of 16); merged ~09:32 UTC with the five failed ashp `exam_12002` tasks
(e12002_00, _10, _12, _13, _15) — 9 failed runs read in total, no existing entry
overwritten or renumbered. The files are left so the next
reader can extend them task by task: per kind, append to `runs[]` in
`failure-autopsy.json`, bump `runs_read` and `causes`, and update the table above.

**Verdict: not yet read** — no kind is anywhere near the 20 runs asked for (the largest
kind count is other kinds at 7, and three target kinds are still at 0), so no per-kind
verdict is carried yet.

## Exact commands

```
# artifacts of a sitting live under the work copy:
ls ~/workspace/edit-lab/for-hive/q1-work/runs/exam/exam_<seed>/<task-id>/
# ashp exam_12002 artifacts copied to this VM:
ls ~/workspace/edit-lab/for-hive/ashp-artifacts/exam_12002/<task-id>/
# members' programs and outputs:
find ~/workspace/edit-lab/for-hive/q1-work/runs/exam/exam_<seed> -path '*members*' -name 'member*_*.py'
# a task counts as read only when its exam.json exists; failed means "ok": false in it.
# the sitting's task list and kinds, without running anything:
cd ~/workspace/edit-lab/for-hive/q1-work && python training/exam.py show --seed <seed>
```
