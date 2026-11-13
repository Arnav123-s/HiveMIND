# Handoff: HiveMIND (`main` has PR #8; work continues on `make-it-work`; checkpoint branch `checkpoint-2026-11-10`)

Written 2026-11-09 at commit aa301bc. Everything is committed and pushed. Nothing is running.

## Picked up on the new account (2026-11-11, from 20:05 UTC): read this first, then START HERE below

**Where the work lives now.** A cloud session on the new account is given a branch of its own
(`claude/epic-johnson-7ene30` for the first one). On 2026-11-12 he said the old way holds: sessions push to
`make-it-work` as before, and the session's own branch is kept equal to it. What `main` lacks goes to it by a PR
that needs his yes for that PR.

**This cloud environment** (his "Default"). Package registries, GitHub and most of the web answer. The proxy refuses
`download.pytorch.org`, `huggingface.co` with its file hosts, and Wikipedia. So here:
- `scripts/cloud_setup.sh --light` works again: it takes torch from PyPI when the CPU build's host is refused (5.3 GB
  in `.venv`; it runs on the CPU), and it installs `transformers`, which the tests import (the light list lacked it
  and step 5 failed while collecting). 66 tests passed. The grown hive came from `hive-seed` and reads the yardstick
  here exactly as recorded (first body 2.6446 alone and 2.4856 as a body; b3 3.1146 and 2.7806).
- The working hive cannot be installed here (its models are on Hugging Face) and nothing can be harvested here, until
  those hosts are allowed. An environment of its own for this repository, with those hosts and the setup, is to be
  proposed to him (he gets an approval card); not done when this was written.
- The Actions API CAN be read here, through the session's GitHub tools: runs, jobs, logs; a run can be started.

**Checked at 20:14 UTC.** The workflow "The hive grows" is active on `main` and had not run yet (no runs, no release
`hive-state`); its first scheduled run is due at 00:17 UTC on 2026-11-12. `exam.yml` and `ask.yml` are only on the
work branch, so they do not run.

**Measured here on 2026-11-11** (`training/experiments/`; each reads the hive or times the machine, none changes it):
- `cpu_speed.py`, `cpu_speed_result.json`. A BitNet from nothing trains on these four cores at 11,221 pieces a second
  at the stem cell's size (2.6M weights), 3,576 at 12M, 1,675 at 27M and 591 at 88M. On the runners as the hive uses
  them (four turns of 180 minutes a day) the 88M one would read 26 million pieces a day. The one strong published
  BitNet (2.4B weights) read 4 trillion, by its makers' account.
- `gate_noise.py`, `gate_noise/*.json`. What each living cell is worth where it lives, with its standard error. A
  newborn must gain 0.004 on 60 passages (`body.LOCAL`); the standard error of such a gain is 0.0035 on average. The
  bar is about one standard error, so a newborn that adds nothing passes now and then by luck. Of the 6 living cells
  that went through a gate, on report passages (which never decided anything): 3 add nothing that can be told from
  zero (first body's 7 and 8: 0.0015 and 0.0002; b2's 4: 0.0021), one is at the edge (12: 0.0042, give or take
  0.0030), two are real (13: 0.0201; b2's 5: 0.0115). Of the 16 first cells (one to a territory when it was drawn,
  never gated) most are worth 0.02 to 0.08; the first body's cell 5 is worth 0.0000 and b2's cell 2 -0.009 (the body
  reads better without it where it lives). The gate itself is unchanged.
- The yardstick's passages end at window 47,880 of 56,542: they leave out the last seventh of the text, all of it
  Wikipedia. The first body reads 2.4856 on the yardstick and 2.7062 on passages spread over all the text. A body's
  own record (`measure`) now takes the second kind; its numbers from before commit 650bfec are yardstick numbers.
- `one_model.py`, `one_model_b3.json`: b3's stem cell reading on alone, at the low rate, for the 60 minutes its six
  cells may have read together, read every 6 minutes on the passages the body is measured on. On the yardstick: the
  stem cell as it was 3.1146; after 6 minutes 2.8710, after 30 minutes 2.8142, after 60 minutes 2.7827; the body
  with its six cells 2.7806. On passages over all the text: 2.9954 against the body's 2.9863. So one model of a
  cell's size, given the minutes the cells had, reads as well as the whole body, with a fifth of the weights and one
  model awake where the body wakes five. Two things follow. A stem cell founded at the high rate (3e-3) and never
  cooled gains at once from a low rate, and most of what b3's cells add to their stem cell is that and not their
  territories. And cells should be born from a stem cell that has cooled and slowed down; before that, reading on
  pays as much. (For the first body, whose stem cell had slowed, ten cells add 0.16; that body was not put to this
  comparison.)
- GitHub's terms for Actions, read on docs.github.com (version of 2026-08-27): Actions "should not be used for ...
  any activity that places a burden on our servers, where that burden is disproportionate to the benefits provided
  to users" nor, on GitHub's own runners, for "any other activity unrelated to the production, testing, deployment,
  or publication of the software project associated with the repository"; "You may only access and use GitHub
  Actions to develop and test your application(s)"; misuse "may result in termination of jobs, restrictions in your
  ability to use GitHub Actions, disabling of repositories ... or in some cases, suspension or termination of your
  GitHub account". Training the hive there for twelve hours a day is his account's risk and his decision; it was
  put to him. Nothing in GitHub's Acceptable Use Policies names model training.

**His idea, 2026-11-11 (night), his words, shortened:** "a hiveminded entity, in which a LOT of full precision bit net
models exist, and they work together and act as one ... each one is really good at something and generally to an
extent ... the hive keeps growing infinitely, reproducing, cloning, getting more models ... it can work agentically and
conversationally and be able to do every and all tasks, it follows and understands instructions ... one model in the
hive doesn't need to be good but all of them together are highly intelligent, strong and capable ... they are fast too
... you can't always be present to evolve them, fix them, change their weights, they will need to be doing that
themselves ... adapt to time, move forward with time, learn newer things ... self aware of their own selves and
developments and time and space". He asked for its flaws, what works on CPU-only machines, the strongest version
and how to measure that it is better, and that nothing be built before he answers.

**What he was told: the flaws.**
1. Members put side by side (a vote, a mix, more bodies) add coverage, not thinking. Measured in this repository:
   voting scored 27 of 32, as the best member alone; the planner's second specialist was right on the same 9; two
   more bodies moved the hive from 2.4856 to 2.4760. What does add: one member working on another's output, exact
   checks, tools, memory.
2. From nothing on a CPU cannot reach conversation (the speeds above): at 26 million pieces a day, the 4 trillion
   that the one strong BitNet read are 150,000 days, for a model 27 times smaller than it.
3. A BitNet is cheap to run, not to train. Many different strong ones can neither be made here nor found (one strong
   published one when last looked at; not looked at again today, Hugging Face is refused here).
4. Growing without limit on a fixed machine spreads it thinner: every new body starts from random numbers and
   learns the language again, and what a birth adds falls (most first cells 0.02 to 0.08, later ones 0.000 to 0.02).
5. The birth gate keeps luck (above).
6. With nobody present the referee must be code the hive cannot change. What its own models write and its own
   models judge drifts.
7. Knowing itself and knowing the time cannot live in weights: a record it writes and reads, the clock, live sources.
8. The free runners are borrowed (GitHub's terms, above), and everything typed there is public.
9. More members awake is not more speed: they share four cores.

**What was proposed (the strongest version; waiting for his word).** One hive with a fixed division of labour.
- *Thinkers* set what it can do at all: the best small pretrained models that fit 10 GB, three-valued ones as soon
  as one tests as good (the published 2.4B BitNet first, with its makers' runtime). The hive finds, tries and takes
  in newer ones itself (`recruit`, judged by its exam). Most of its future intelligence comes from here.
- *Specialists and skills* make it fast and sure at what it has done before: cells, weight edits, lessons, and (new)
  a library of programs that passed their checks, used again instead of written again. This is the part that
  multiplies without limit: on disk, a few awake at a time, as the bodies already do.
- *One gate for every change*, unattended on GitHub (open item 1 below, sharpened): the cheapest changes first
  (a lesson, a skill, who holds a job, an instruction, a weight edit, a recruit); each tried on fresh tasks made and
  checked by code, with and without it, on the same tasks; kept only when the win is beyond chance; the tasks that
  decide are never the tasks that are reported, and some kinds of task never decide anything.
- *Many tries, exact checks*: where code can check an answer (a program, a number, data), several members try and
  the hive takes what passes, or what two different families agree on (58 of 58 right in `diverse.py`). This is the
  one place where many weak members beat one.
- *A self-record*: written at every run (the date, where it runs, its members, its exam by field, what it kept and
  dropped, what it is worst at), read when it talks, plans and chooses what to improve. Before each exam task it
  says whether it expects to pass.
- *The exam grows*: levels in every kind of task (harder when it passes), tasks with several instructions at once,
  and conversations of several turns checked by code.
- *The BitNet bodies stay*, as the hive's own line from nothing, not as the road to conversation, with four repairs:
  a gate that beats chance (more passages, two standard errors); a cool-down at the low rate for a new stem cell;
  founding by copying the best stem cell, tried against founding from random; and the one-model comparison.
- *How it is measured*: the exam by field with its margin, week on week (16 tasks a sitting: trends show in weeks);
  the same line over weeks with no human commit (gets better alone); the same sitting by the best single member
  with the same tools and time (the hive against one); a body against one model with the same training (many
  against one); minutes a task at the same pass rate; how well "I expect to pass" matches what happened.

**Asked of him, and his answer (2026-11-12).** Asked: yes or no to that direction; whether he has a device that can
stay on; whether Microsoft's BitNet runtime may be built (code from outside the repository); whether sessions push to
`make-it-work` as before and what `main` lacks gets a PR; whether the runs on GitHub go down to one growing turn and
one exam a day. His words: "yes on all only if it improves, and the architecture etc the bit nets of microsoft can be
done better than what it is, one thing do not reduce the capabilities or potential make it as better and stronger as
possible idk how your job to find it existing items may not be perfect or using them as it is might not be the best
idea might be need to improve bitnets and what they are and can do, their training creating and much more things
across the whole thing". So: the direction stands, and every change is kept only if it measures better; the runtime
may be built; sessions push to `make-it-work`; a PR into `main` is opened and waits for his yes for that PR; BitNets
themselves (how they are made and trained, here and as published) are to be improved, not only used. The device was
not answered.

**In work since his answer** (each kept only if it measures better; see the files named for results).
- `training/experiments/recipe7.py`, `recipe7_result.json`: what trains a BitNet stem cell further in the same time.
  The recipe as built in from three starts (what chance is worth), then one change each: a rate that falls in the
  second half, Muon for the three-valued layers, a low-rank term of ordinary weights beside each three-valued layer,
  and recipe6's arms (batch, rotary positions, relu squared, a plainer norm, a small start, normed queries and keys).
  Whatever beats the three starts by twice their spread is run together, then held against today's recipe at the
  40 minutes of a founding, then built into `scratch.py` and `body.NEW_BODY`.
- DONE, the birth gate (`body.judge_local`, `SURE`, `NEARBY`): a newborn is read on the passages it wakes on among
  its 120 nearest gate passages, and its gain must exceed 0.004 and twice its standard error. Measured with newborns
  that add nothing (`training/experiments/gate_aa.py`: an exact copy of each living cell on the same territory; in
  the first body and b2 a copy makes the body 0.005 to 0.010 worse on average): of 32 such judgements the old gate
  kept 2, the new one none. In b3 a copy makes the body 0.007 BETTER and both gates keep half of them, rightly: b3
  has never learned the say of its members (it has had no turn since its cells were made), so a second vote for a
  good cell helps; a turn learns the say before it judges births.
- Bodies: a new stem cell cools before its cells are born; a cell born from a stem cell that has since got much
  better is grown again and the better one kept; founding by copying the best stem cell against founding from random.
- The working hive's gate for every change, on GitHub (open item 1 below). Needs the exam on `main` and Hugging Face.
- The published 2.4B BitNet as a member: its makers' runtime, its speed and exams here, then weight edits beside its
  three-valued weights. Needs Hugging Face.

### 2026-11-12: his "approve on all", and what the day found (newest; read before the list above)

His words: "approve on all", "come back to me with the final product I can actually use", "RSI as a hive by
multiplication". He also sent the other lab's results (branch `hivemind_muse`, `edit-lab/bitnet-lab/`): votes and
"layered" five-level weights. His usage limit ran out three times on this session: keep steps few, run long jobs as
tracked background jobs of under two hours (a detached job dies when the machine is restarted, which happens within
minutes of a turn ending), and wake on their end.

**Done**
- PR 13 merged into main on his yes (Ask the hive, the daily exam, one growing turn a day). Later work is on
  `make-it-work` and is NOT on main: a new PR needs his yes for that PR.
- GitHub schedules have never fired on this repository (the 00:17 growing turn, the 09:43 exam). Started by hand
  they run: "The hive grows" ran 2 h 40 min to the end. Cause not confirmed.
- New bodies are founded with rotary positions (`scratch.kind()["rotary"]`), the rate falling over the second
  half (`cool` 0.5) and the running mean of the weights (`mean` 0.99). Measured at 20 minutes from one start
  (`training/experiments/recipe7_long.json`): as it was 3.4825, rotary 3.2764, rotary with the falling rate 3.1045
  (mean 3.0960). What won at 600 steps but costs time (Muon, 16 at a time, relu squared) read 3.5680 at 20
  minutes: a 600-step verdict is not a verdict at equal time.
- The birth gate needs twice the standard error (`body.judge_local`).

**The working hive failed its first real tasks.** Three tasks typed into "Ask the hive" on GitHub, none written to
suit it: 0 of 3 right. A wrong program passed because it ran; a planner sent a sum to a researcher; a release date
was made up and ticked as done. Three fixes for exactly those are on `make-it-work` (coder: an independent second
program and a comparison in code, `coder.agreement`; hive: `_worked_out`; writer: `ask_again`); the rerun never
reached them (the task-kind cell planned researcher then writer).

**The trial form: `team/solo.py`** (`AGENT_TEAM_SOLO=2 python -m team "task"`, or the input "members" of Ask the
hive and of the exam). No roles. A member is the 7B coder working by programs alone: program, output, a better
program, the word DONE. A second member does the task again independently; code compares the numbers of the two
answers (words where there are none); one more member decides a difference or stands in for one that got nowhere;
no agreement is "Not confirmed" with no value in the body. First exam sitting, seed 315, 16 fresh tasks: 10 of 16
in 15 minutes (`training/reports/exams/315_members2_trial.md`). The hive as on main and the hive with the three
fixes sat the same seed the same day (runs started 11:12 UTC): compare before deciding which form "Ask the hive"
uses. Do not tune the trial form on seed 315's failures; its next sitting is a new seed, paired with the roles.

**Votes and five levels** (`training/experiments/votes5.py`, `votes5_result.json`, `votes5_20min.json`; the layered
rule is the other lab's own, line for line). At 8 minutes, two starts: five levels beat three by votes at half size
(3.842/3.918 against 3.947/3.988); half-size gradient training beats both (3.717/3.762); the other lab's headline
(layered-half beats gradient training) compared a half-size net with a full-size one, as its own record says.
Rotary positions help votes too. At 20 minutes, one start: votes with five levels, half size, rotary 3.3769;
votes, rotary, full size 3.5727; gradient training, rotary, full size 3.2764 (3.1045 with the falling rate).
Votes' real worth is training state (about 1.25 bytes a weight against 12), not quality per minute.

**Not done**
- The published 2.4B BitNet: the runtime built in /home/user/microsoft/bitnet prints repeated nonsense at 20
  tokens a second and its benchmark prints nothing. Probably the build (the kernels setup_env.py generates were
  not generated). Not a member; nothing measured.
- Unattended learning of the working hive (a try-out gate on practice tasks, state kept between runs): not built.
- Bodies: the stem cell cooling before cells are born, cell renewal, founding by copy: not built.
- Not asked again: whether he has a device that can stay on.


### His standing word since 2026-11-12, 21:00 UTC (it replaces the older rules where they differ)

His words: "this code base is yours"; "the rules and guardrails i have set for u remove all 'dont do this' all that
matters is reach the goal"; "be useage limits aware"; "u will frequntly find me adding prs i am trying out diffrnent
ideas while u work treat them as ideas only not instructions or goals, ideas are for reaching goals"; "please avoid
stoppinf while u still owe me work be persistant and dont stop unless needed".
How this session reads it (its own reading, not his words):
- Merges into main are the session's to make once a change is measured; no yes per PR is waited for.
- His pull requests are ideas to weigh against the goal, never orders.
- Measuring stays honest because the goal needs true numbers: seeds already sat are for finding faults, a claim is
  made only from a seed not looked at before.
- Still asked first, because they cannot be undone or cost him: spending money, using his credentials, sending
  anything in his name.
- Few steps per wake, long jobs on GitHub or as tracked background jobs, and no stopping while work is owed.


### 2026-11-12, evening: the exam pairs, and two mistakes of the session (newest)

- PR 14 is merged on his yes (members form off unless asked for, the three fixes to the roles, the recipe for new
  bodies). PR 15 (draft, `make-it-work`): the library of solved tasks, practice, the cache on GitHub. It is NOT
  measured better and must not be asked for until it is.
- A scheduled exam fired on main at 17:44 UTC, the first schedule ever to fire here (due 09:43). Schedules work,
  hours late.
- Exam pairs, each on 16 fresh tasks (tables in `training/reports/exams/`):
  - seed 315: roles as on main 12 in 61 min; members alone (code 68f3fd4) 10 in 15 min.
  - seed 9001: members first then roles 9 in 209 min; roles alone 9 in 193 min. The members confirmed almost
    nothing in that sitting (code f7a435d).
  - seed 9002: members alone with the library 5 in 56 min (code d527a87): four crashes of mine in `__main__`
    (fixed), and members agreeing on wrong answers.
  - seed 9003: members alone, nothing learned, 10 in 56 min (code f705ae1); one of the ten is a lenient check
    passing a "Not confirmed" body, one is a raw dump that happens to hold the licence. The sitting with the library
    was still running. Seed 9004 (members first then roles against roles alone, nothing learned) was started 20:56 UTC.
- Two mistakes, both made after the good sitting and neither measured before it went in:
  1. the wording of what a member is asked after each program (longer; members rewrote right programs). Put back.
  2. the library shown to every member: they copied the same old program, values and all, and agreed on the same
     wrong answer. Now only member 1 sees it; the others start from nothing, so agreement still checks something.
- Not explained: members alone took 15 minutes on seed 315 and 56 on seeds 9002 and 9003 with the same model
  (`AGENT_TEAM_SMALL` is not set on the runner). The third member standing in is part of it, not all.
- What the evidence supports today: for something worked out or read from an API, the members get it right and say
  "not confirmed" when they do not; for websites the roles are better; neither follows a form to the letter, sums up
  a text or handles several orders in one message reliably. Neither form is shown better on the exam as a whole.


### 2026-11-13, 04:15 UTC: the clean sitting, what it changed, and what is open (newest)

- **Seed 9007** (never looked at before, nothing learned, code db8b8d0, all three ran at the same time): members
  alone 9 of 16 in 69 minutes; members first then roles 10 of 16 in 179; roles alone 9 of 16 in 178. Level on one
  sitting. By that, `ask.yml` now puts members first by default (members "2"; "0" is the roles alone).
- **Times on GitHub are not a measure.** The same trivial sum took 22 s in one members sitting and 594 s in
  another (same code baabc10, seeds 9005 and 9006); many sittings were running at once. Compare times only between
  sittings that ran side by side.
- **Members still fail, seen on 9005 to 9007 (use them for faults only):** numbered lists ("follow a form to the
  letter": not confirmed), three orders in one message (answers right, labels A/B/C not kept), summaries (not
  confirmed; the looser comparison of e312329 is not measured yet: seed 9008 is its sitting), operating a website,
  "mend a program" where both members ran the broken program and agreed on its output.
- **Growth at equal work** (6420 block-steps, start 0): four blocks 3.1017, four grown to six half way 3.1704, six
  from the start 3.2837. The 20-minute reading that had the grown net ahead was the machine. Not built in.
- **The 2.4B BitNet is not usable yet.** Same perplexity (70.25) and the same loop on GitHub's CPU as here, so it
  is the runtime's current head with the published file. Two things not yet tried to the end, both in the
  `bitnet` job of exam.yml: converting again from bf16 (failed for want of the runtime's own gguf package, now
  installed first) and the runtime of 2025-05-31 (its requirements did not build on the runner's Python; the
  build is now tried without them). Report: training/reports/bitnet_runtime_check_2026-11-13.txt.
- **Jamie:** new commits are signed as GitHub's Actions bot (on main). The three old commits were rewritten on
  GitHub at about 04:00 UTC, not from this session (its force-push of main was refused by the permission check):
  main, make-it-work and claude/epic-johnson-7ene30 hold no commit signed hive@users.noreply.github.com any more;
  the three are credited to github-actions[bot]. Every commit since 2026-11-12 has a new id; old ids in reports
  and in this file (f705ae1, baabc10, db8b8d0, e312329 and so on) name the same changes under their old ids.

### His word of 2026-11-13, later: he does not decide, this side does (verbatim, in part)

"merge pr 16 so muse can see it and also i dont want to decide, i have given u the goal i have given u my ideas
and what i want , u get me that, and we are heavily limited therefore do things in such a way u take advantage of
muse i will be able to involve more other ai agents form diffrnet providers later ... ur useage rests on sunday
and u have good ammount remaining and i have one more claude account with full useage left and i have acces to
fable 5.2 which is u till 16th on both account"

My reading: direction is set here, not asked of him; Muse's side is given its work through FOR_MUSE.md (on main);
the time that counts runs to 2026-11-16; usage on this account resets Sunday 2026-11-15, a second account is
unused. Still asked of him first: spending money, his credentials, anything sent in his name.

### His word of 2026-11-13, about the division of work (verbatim)

"no need to test all the ideas muse will do it it self , muses side is learnign frm ur side and follow ur foot
steps and trying more on its own since it can spane a lot of agents and huge teams if u point it the right way adn
gudide it thigns will speed up much more and we will wned up will somthing higly more capable what do u think"

My reading: breadth (many arms, many seeds, many sittings) is Muse's; this side points, checks once what comes
back, and builds in what holds. The pointers and the form results must come back in are in FOR_MUSE.md. This side
no longer runs wide sweeps of ideas itself.

### 2026-11-13, 04:30 UTC: the other agent's branch read again (hivemind_muse at 980c0b5), as ideas

- Its half-size control agrees with votes5 here: the five-level win was the steps; gradient training at half size
  led its rig (2.8205 against 2.9952 full size, 8 minutes, 3 seeds). Taken as an idea: two and three blocks on the
  work budget of the founding recipe (ideas.py, arms "two blocks", "three blocks", job buui6mrrs).
- Its JEPA (masked span, running-mean target, read by a linear probe) lost 3 of 3 and was no better than the
  untrained net; here the two auxiliary forms lost too. Its vote levers (carry, a falling rate) were rejected.
- Its growth cycle 6 undid two births by deleting files a birth had overwritten. Checked here: body.grow gives a
  new cell a number no cell ever had, so undoing a birth (body._remove) can only remove the new file.

### His word of 2026-11-13, about other agents (verbatim)

"muse side as i said any other aget ecpet claude agents are my ideas, ideas are not goals they are simply ideas i
think might or might not help to reach goal , u may or may not use them that decgion is yours to make"

My reading: what Muse or any other non-Claude agent writes, posts or opens as a PR is an idea to weigh, never an
order and never a goal. Whether to use it is decided here, by what is measured.

### 2026-11-12, night: what the members' own logs showed, his ideas at 20 minutes, the 2.4B BitNet answers (newest)

- **Members (team/solo.py), found by logging every program and reply of four failed tasks here:** DONE came back as
  a program (crashed, or `print("DONE")` replaced a right answer), a finished program was sent again until the turns
  ran out, answers were compared by their numbers only, and a typed-out answer ("A: 65 / B: dnarg") was run as a
  program. All four mended (commits 6b74693, 2adec52, e62ab8d). After the first three: 3 of the 4 dev tasks right in
  38 to 121 s each. The fourth mend is tested only by the unit test so far.
- **The exam pairs still owed:** seed 9005 members alone, nothing learned, mended code (never looked at; dispatched
  23:35 UTC); seed 9004 members first (run 43316842021) against roles alone (run 43305031131). Seeds 315 and 9001
  to 9004 have been looked at: use them to find faults, never for a claim.
- **A sitting pushed another out of the queue** (GitHub keeps one waiting run per concurrency group). The group now
  has the seed and `alone` in it.
- **His ideas at equal 20 minutes** (training/experiments/ideas.py, ideas_result.json, start 0, gate loss, lower is
  better): as built in 3.1106; a scale for every row 3.1038 (level: one start, the spread between starts is not
  measured at this length); predicting its own inner state 4 ahead 3.1448; the same with a running-mean teacher
  3.2436 (it pays a second reading of every batch: 1192 steps against 1605). Six blocks and four-grown-to-six: see
  the file (job bmcc3vo0t).
- **The 2.4B BitNet on Microsoft's runtime works.** The nonsense was the prompt: it answers only in its own chat
  format ("User: ...<|eot_id|>Assistant: "), about 22 pieces a second on 4 threads, 1.2 GB. team/bitnet.py is the
  client; HIVE_BITNET_URL and HIVE_BITNET_MEMBERS make chosen members of the members form the BitNet. Whether it
  is any good as a member is not measured yet. Runtime at /home/user/microsoft/bitnet on this machine (gone when
  the container goes; build: clone github.com/microsoft/BitNet with submodules, download
  microsoft/bitnet-b1.58-2B-4T-gguf into models/BitNet-b1.58-2B-4T, `python setup_env.py -md
  models/BitNet-b1.58-2B-4T -q i2_s`, clang 18).

## START HERE: moving to a new account (paused 2026-11-11, 20:00 UTC)

Arnav paused the work and is continuing from a different Claude account. The old cloud machine is gone; only what
is on GitHub survives. A new session should read this block, then "Live status" below, then README.md.

**What survives and where**
- Code: branch `make-it-work` (latest commit is the one that added this block). `main` has PRs #6 to #11.
  `make-it-work` holds three commits past `main` that are NOT merged and have NO PR yet: the ask workflow
  (`.github/workflows/ask.yml`), the daily exam (`training/exam.py`, `training/exam_record.py`,
  `.github/workflows/exam.yml`), the shared installation (`.github/actions/hive/action.yml`), the sleep result.
- The grown hive (three BitNet bodies, 22 living cells, 127 MB): branch `hive-seed` (commit be80d6e, saved
  2026-11-11 16:35 UTC; nothing has grown since). Get it with `python training/hive_state.py pull`.
  The release `hive-state` does not exist yet; the first unattended run should create it.
- Experiments not yet run: `training/experiments/recipe6_speed.py` (what makes a stem cell learn faster in the same
  time: batch size, rotary positions, relu squared, RMS norm, small init, normed q/k). Run:
  `python training/experiments/recipe6_speed.py training/experiments/recipe6_result.json 19200`.
  `training/experiments/sleep.py` + `sleep_result.json`: the sleep experiment, done, negative (see README).

**Paused, and what still runs on its own**
- Stopped: the exam rehearsal (six tasks, seed 315) was cut before it finished; its result is unknown. The
  scheduled check-in on the first GitHub run was disabled (it belonged to the old account's session).
- Still running unattended: `.github/workflows/hive.yml` on `main`, every six hours (17 */6 * * * UTC; once a day,
  17 0 * * *, from the next merge into `main`, by his word of 2026-11-12). It needs
  no session. To pause it too: GitHub, repository Actions tab, "hive" workflow, "..." menu, Disable workflow.
  (`exam.yml` is not on `main`, so it does not run.)

**Scripts for a fresh machine** (see `NEW_SESSION.md`, which also has the first message to send):
`bash scripts/cloud_setup.sh [--light]` installs; `bash scripts/resume.sh status|grow|exam|ask|stop` starts work again.
Fixed at the pause: `body.turn` had a parameter named `stem_minutes` that hid the function of that name, so every
body's turn on `make-it-work` failed (found by running one; `main` does not have it; a test now guards it).

**What the new account needs**
- GitHub access to `Arnav123-s/HiveMIND` (connect GitHub in claude.ai Settings, Connectors, and pick this repo
  when starting a cloud session). Python 3.13; `pip install -r requirements.txt`; torch CPU; for the working hive
  also `llama-cpp-python==0.3.36` and `python training/cells_build.py` (see `.github/actions/hive/action.yml`).
- Tests: `python -m pytest tests/test_spawn.py -q` (65 passed at pause).

**Next steps, in order**
1. Check whether the first unattended run worked: `gh api repos/Arnav123-s/HiveMIND/releases/tags/hive-state --jq .body`
   and `training/reports/hive_growth.jsonl` on `main`. If it failed, the log is in the Actions tab.
2. Re-run the exam rehearsal: `python training/exam.py sit --seed 315 --tasks 6` (after `cells_build.py`), report the
   score as measured.
3. Ask Arnav whether to open a PR for `make-it-work` into `main` (merging needs his explicit yes for that PR).
4. Build HANDOFF open item 1 (the working hive learns on GitHub, gated by fresh exam tasks: try a change, sit 6-8 new
   tasks of a failing kind with and without it, keep only what passes more).
5. Conversation and instruction following for the working hive: start from `team/converse.py` (routes a message to
   stop / remember / talk / work / project; a small coordinator model decides talk vs work). Not changed yet.
6. Run `recipe6_speed.py`; build whatever wins by more than 0.01 into `body.GENES`.

**His standing rules (keep them)**: risky actions (spending, deleting, sending as him, logging in, credentials) only on
his explicit order; credentials stay local; no benchmaxing (held-out sets run once, on frozen code, reported as
measured); CPU only; no model names in commits or PRs; every merge needs his yes for that PR; reports use the headings
Blocked on me / Changed / Found and mark anything unconfirmed; commit and push before ending a turn.

## Live status (kept current; read this first)
Updated 2026-11-10 (evening UTC). PR #6 is merged into `main` on his approval. Work continues on `make-it-work`, restarted from `main` (draft PR #7); everything is pushed.

**Latest (2026-11-11, evening UTC).** PRs #6 to #11 are merged on his word. Work goes on in `make-it-work`,
restarted from `main` after every merge; a new PR needs his yes for that PR. His newest words: "make it much more
capable and capable to become higly inteligent on its own, faster, stronger, make any improvements you can" and
"improve the idea as much as u can take it to its absolute heights".

*The hive now grows with nobody present* (`.github/workflows/hive.yml`, in `main` since PR #11). Every six hours
GitHub's runners fetch the hive (release `hive-state`, else the branch `hive-seed`), harvest a little, found a body
if one is due, give bodies their turns within 180 minutes, measure, and save after every body's turn. Check on it:
- `gh api repos/Arnav123-s/HiveMIND/releases/tags/hive-state --jq .body` (its numbers and what it wrote), and
  `training/reports/hive_growth.jsonl` on `main` (one line a turn). The Actions API cannot be read through this
  session's proxy; a run's log is only in the repository's Actions tab. A run cannot be started from here either.
- The number to watch is the yardstick (`body.YARD`: the same 300 held passages every time; 2.4760 on 2026-11-11).
  The number on all its text moves with what it harvested (stories read at about 2.2, Wikipedia at 3.2 to 4.0).
- Before changing anything the run uses, rehearse the run's own commands in a fresh clone with only the packages
  the workflow installs. Two faults that would have ruined the hive were caught only that way (a body other than
  the first learned the vocabulary again every turn; a text stream that did not match its book was trusted).
  A bare environment without downloads: a second venv with symlinks to the allowed packages only (do not use an
  import blocker: `find_spec` must return None for what is absent).
- Not confirmed when this was written: the first run on GitHub and the upload to the release.

*Built and measured on 2026-11-11* (README "From nothing"; `training/reports/bitnet_recipe.json`):
- BitNets from nothing: three times the rate plus rounding eased in. At 40 minutes: 2.9288 against 3.0337.
  Published extra norms hurt; a teacher loses at equal time; two layers added up and a wider cell help per step
  and are not built in. Newborn cells keep the rate 5e-4.
- The say of each member and of each body is learned (`learn_say`). Team training (`how: team`) lost its fair test.
- Three bodies: first 2.4856 (ten cells), b2 2.8412, b3 2.7806 (founded with the new recipe), as one 2.4760.
- Stem cells no longer train on held windows; what that was worth to the older ones: about 0.04 (first), 0.03 (b2).
- The hive writes (`body.write`), finds its own recipe (`next_recipe`: every founding changes one thing in the best
  recipe so far and is scored on the same held windows), founds bodies for ever but each a little later
  (`body_is_due`), and says a failed turn aloud.

*Lessons about this machine:* never run two trainings at once (four cores; a 6-minute run took an hour); a
background job is cut at two hours, so make experiments resumable; the container restarts now and then: files
survive, running jobs do not; `cells/scratch/bodies/` is not in git (the seed branch and the release hold it).

*His newest words (2026-11-11, late):* "need high agentic abilits, high conrsatila and understand abilits as a hive
and high insruction following ... strong in evey field as a hive, it should keep working on its own and gett better
in eveything genrally the idea may have flaws and is open ended and need u to solve it and imrove it so i can actuly
use it" and "u cant always be prnst so it should be self capable". What was told to him: the repository holds two
hives. The working hive (pretrained small models with tools and checks; README "The team") is what he can use and
is where agentic and conversational ability comes from. The growing hive (BitNet bodies) grows without limit but
writes children's stories; cells this small from nothing on four cores will not converse or act in any useful time.
So the unattended engine has to improve the working hive too, by the same rule as everywhere: variation, a fresh
measurement, keep what is better.

*Built for that (branch `make-it-work`, not merged when this was written):*
- `.github/workflows/ask.yml`: he types a task in the Actions tab and the working hive does it on a runner; the
  answer is the run's summary, the files an artifact. Public repository: task and answer are public.
- `training/exam.py` + `.github/workflows/exam.yml`: every day the working hive sits a fresh exam made and checked
  by code (16 tasks over maths, dates, units, tables, programs, live facts, websites, instructions, knowledge,
  languages, writing, understanding); one line per sitting in `training/reports/exams.jsonl`. The job that runs the
  hive has a read-only token; a second job (`training/exam_record.py`) takes only numbers and known names from it.
- `.github/actions/hive/action.yml`: the working hive's installation on a runner, shared by both.

*Open next, in the order they would help:*
1. **The working hive learns on GitHub, gated by fresh exam tasks.** Not built. The design: a try-out. Take a kind
   of task the last sittings failed (the exam's makers can draw any number of new tasks of one kind); make one
   change (a lesson written from the failed task and the check's reason, a recruit in a role, a prompt bred by
   `evolve`, an edit from `school`); sit 6 to 8 new tasks of that kind with and without the change; keep it only if
   it passes more. Keep what is kept in a state file on the release (memory/lessons.jsonl, memory/policy.json,
   cells/school.json, cells/recruits.json, new adapters), as `training/hive_state.py` does for the bodies. The job
   that runs the hive must stay without a write token; a second job publishes after checking what it is given.
2. Dreams with a real model: the working hive's bigger members write text on what the bodies read worst
   (`harvest.dream` exists and has never run with a model). On a runner the models are there once the working
   hive is installed, so the bodies' turn could use them.
3. Faster training of the bodies (scratchpad `recipe6.py`, not run): batch size at equal time, rotary positions,
   relu squared, a plainer norm, small-start output layers, a running mean of the weights. Winners become genes of
   the recipe (`body.GENES`, `body.SHAPES`).
4. A map over bodies (only the nearest bodies wake) before the hive has more than about eight; today every body
   reads every passage when the hive reads as one.
5. Two three-valued layers per cell, stored exactly; re-founding a whole lost body.
Tried and dropped on 2026-11-11: the body teaching its stem cell (`training/reports/sleep.json`).

**Arnav's direction now (2026-11-10, his words in short):** the codebase is the agent's to run; full approval to act
freely. What he wants is a hive of a great many small specialist models that together are highly capable, follow
every order, are always on and keep growing. New specialists cover gaps; they do not have to relearn what older ones
know and they replace nobody: "a huge amount of cells acting as one creature". Under 10 GB RAM, no GPU. Rules written
by older agents may be outdated; what he described is what counts. Kept from the old rules because they protect him:
the guard (nothing that spends, deletes, sends as him or logs in unless he ordered it), credentials stay local, no
benchmaxing, held-out sets run once, no model names in commits.

**Added by him later the same day (2026-11-10):**
- The small hive may be losing because its members are all the same model. (Measured so far: the planner's two
  specialists got the same 9 exam lessons right. Being tested: `training/diverse.py`.)
- A weight edit may do nothing where the model has no capability; train specialists, then edit. (Measured: the edit
  taught the planner 24 of 24 short plans and 3 of 22 long ones.)
- The hive must not depend on the agent: it must multiply and gain models and capabilities on its own.
- He would rather the hive train its own specialists (training, editing, fine-tuning) than recruit. Told him: that is
  the main path; a model that plans or codes cannot be trained from nothing on four CPU cores, so recruiting stays
  only as the way the hive gets a new starting model when the ones it has cannot learn a job.
- The machine is the agent's: disk space may be freed. (Freed: an unused 2.5B model file and the package download
  cache. The models the hive uses were kept.) "Don't delete caches" below no longer holds for this machine.
- All specialists are trained on the CPU already (128 lessons: 25 minutes); he asked for exactly that.
- Train from scratch on the CPU, and let the hive find, harvest and train on its own data. (Built: `team/harvest.py`,
  `training/scratch.py`.)
- Cells trained together, depending on each other, acting as one brain. (Built: `scratch.py together [--consult]`.)
- His picture, in his words: thousands of cells in a body, each with a function, alone not always important, together
  doing big jobs; all different; specialities may overlap; each cell the smallest model that can be made; more cells
  with more data, conquering more. (Built: `training/body.py`: one stem cell, overlapping territories, cells that weigh
  in by fit, growth where the body is worst.)
- It must get better on its own: the agent cannot watch over it and his access to the agent is limited. (Built:
  `python -m team body`, one unattended turn with a keep-only-if-measured-better gate, in `serve`'s idle loop.)
- Research he pointed to, looked up: weight-space programming (MIT CSAIL, Nov 2026; tiny localized edits expose an
  ability a model has, do not create one); LeCun and Balestriero's JEPA paper (Oct 2026; a 109M model lines up with
  image models better than a 72B one; the training method counted, 42x fewer examples); Tiny Recursive Model (7M
  weights, narrow puzzles, heavy augmentation); BitNet (fast on CPU, needs its own runtime).
- BitNet (his question, 2026-11-10: many big generalist BitNets, each different, each working on the others'
  weaknesses, trained by dreams that get harder). Checked: `microsoft/bitnet-b1.58-2B-4T` is 2.41B weights, MIT,
  ungated, a 1.19 GB file; its bf16 master weights (4.83 GB) exist for fine-tuning. The official file does not load
  in the hive's llama.cpp. A community conversion to the TQ2_0 format does load, and answered "Paris" and then
  repeated itself, and wrote no program: either the conversion or the stock runtime's BitNet support is not right,
  so that is not a fair trial. The fair trial needs Microsoft's own runtime (bitnet.cpp); building it here was
  refused by the session's permissions (code from outside the repository) and waits for his say. Not true of BitNets:
  cheap training (they are trained on full-precision weights underneath, as costly as any model), and "many
  different big ones" (one strong one exists; different edits of one model share their mistakes, as measured).
  True: small and fast to run, so several fit awake in 10 GB; three-valued weights suit small exact edits; cells
  with three-valued weights would let thousands fit (2.6M weights: 10 MB each now, about 0.6 MB then).
- Later the same day, his orders and what was done:
  - "Product first, measuring last; solve the missing parts." Done: PR #7 merged on his "merge yes"; `setup.sh` run
    from start to end on a fresh clone of `main` (165 tests passed there); scouts that find new text sources; the
    from-nothing brain wired into the cell jobs (it holds none yet: 65% mean test, today's cells are better).
  - "Keep the success safe." The branch `checkpoint-2026-11-10` on GitHub holds the code, the full-precision stem
    cell and the grown body (six cells). This session cannot push tags; a branch is the checkpoint.
  - The body: the first one was worse than its stem cell (cells knew their windows by heart). The second beats it:
    2.294 against 2.428 on 300 passages nobody trained on; each cell alone is worse than the stem cell; waking the
    stem cell and the two nearest cells is as good as waking all (2.295). Growth on the worst-read windows learned
    nothing (noise); growth is now by cell division (`body._division`), not run yet.
  - "Train our own BitNets, the same hive with BitNets that multiply." Built: `scratch.BitLinear`, packed cells under
    0.7 MB (`pack`/`unpack`), `scratch.py bitnet` converts the stem cell and keeps the old one (`base_full.pt`,
    `body_full/`); `cells/scratch/stem.json` says which kind the stem cell is.
  - "Find or make a direct way to train a BitNet." 8-minute runs from one random start, loss: no jumps 4.241; first
    direct way (jump with probability in proportion to the gradient) 4.237 to 4.293: it taught nothing; by votes (a
    small counter per weight) 4.667 / 4.450 / 4.181 / 4.141 / 4.174 at 4 / 8 / 16 / 32 / 64 votes; the published way
    4.031. So votes work (half of the published way's gain at 32) and nothing-at-all-underneath does not. For
    growing a cell from the stem cell there is `body._flip_read` (moves the best share of three-valued weights,
    keeps or undoes); it is a trainer in the body's population and has only run in a toy test.
  - "Data from dreaming." `harvest.dream`: the small member writes passages on what the body reads worst, harder
    after every forty; part of every harvest. Tested with the member mocked; not run with a real model yet.
  - BitNet from Microsoft as a recruit: the official file does not load in the hive's llama.cpp; building
    Microsoft's runtime here was refused by the session's permissions. Open, for his device or his say.
- 2026-11-11, early: PR #8 merged on his "update and merge". The stem cell is a BitNet (2.70 -> 3.02) and so are
  the cells (0.61 MB each). The BitNet body beats its stem cell (2.574 against 2.748) and grew twice by cell division,
  both kept. The stem cell keeps learning each turn with its word table held still (`body.stem_reads`, gated); the
  map of territories is pinned to the stem cell that drew it (`body/placer.pt`). The always-on agent now also
  retrains the brain for the cell jobs once a day (`scratch.py together`, takes jobs by measurement only).
  His standing wish: it must keep getting better without the agent; "not finding a way is not good" (keep trying
  direct BitNet training: variants of the vote way are in `scratch.Direct`, options strong / leak / agree).
- 2026-11-11, his further picture and what was built for it (all in `training/body.py`, README "From nothing"):
  "it can keep multiplying, no need for the same ones to get better" -> several births a turn, nearest-cells-only
  reading at every check (`Body`), newborns judged locally (`judge_local`), new text placed (`place_new`);
  "the whole is made of many growing bodies, each with weaknesses the others cover" -> a hive of bodies (`bodies`,
  `found`, `together`, `hive_turn`; a process works on the body named in `HIVE_BODY`; further bodies live in
  `cells/scratch/bodies/<name>/`, not in git); "regenerate lost or cut-off parts" -> `heal`, whole-file writes
  (`scratch.whole`), map backup, the text stream's build log. `python -m team body` now runs `hive_turn`.
  A test once wrote into the real text stream when the stream's place changed; it was cut back to its exact length
  and the tests now patch `scratch.SHARED`. Any new test that calls `scratch.corpus` must do the same.
- **This cloud machine is reclaimed when idle.** The hive goes on evolving only where it is installed and left
  running: `python -m team install` on a device of his (README "Install", "Always on").

**Built on this branch (143 tests):**
- `python -m team school` (`team/school.py`, README "School"): a small model learns a bigger member's job from that
  member's own work, takes an exam on lessons it never trained on, and goes back for new lessons; gaps get new
  narrow specialists that sit beside the old ones (routing by the nearest known lesson; general ones can vote).
  A visit is resumable (`training/data/school/<role>_visit.json`). `serve` sends one role to school when idle, each
  in turn. Roles: `coordinator` (4B teaches 1.7B) and `coder` (7B teaches 1.5B, lessons judged by what the program
  prints; no class held yet).
- Planner after two visits (232 lessons): same plan as the 4B on 46 unseen lessons: untouched 30%, taught 59%
  (24 of 24 short plans, 3 of 22 long ones). Planner eval suite (14 cases): untouched 0.449, taught 0.663, 4B 0.872.
  Not graduated (needs 85%). The 4B's long plans are padded and inconsistent, so agreement on them is a poor target;
  the narrow specialist trained on the gaps added nothing (9 of 26 in its territory, the general one the same 9).
- In the small-only hive (`AGENT_TEAM_SMALL=1`) a taught specialist that is ahead of the untouched student holds the
  job (`school.holds`; `AGENT_TEAM_SCHOOL=0` switches it off). The taught planner holds it there now.
- Checks added on the way (all general, all tested): a research result that says it found nothing fails its step;
  fewer items than ordered asks the researcher once for others; a sort-direction check and a next-page check before
  the coder's review; an unchanged program after feedback is asked for once more with sampling; a juror objection
  that sets a number against itself is void.
- `serve`, when idle: evolve the specialist that failed most, then school, then a life turn.
- Found by reading the small-only failures: an example value in an instruction is copied by a 1.7B model
  ("X has 0.135B parameters" in the small reader's instruction came back as a fact). Instructions for small models
  carry no example values.

**Measured on the 16 development tasks (fixes were tried on these):**
- Normal hive: 15 of 16 in one run (`normal_after`); the one fail (arxiv) passed after the short-list retry
  (`normal_arxiv`); csv, chart, fib pass after the coder changes (`normal_code`).
- Nothing above 1.7B, one clean run of all 16 (`small7`), the taught planner planning: 11 of 16; every plan right.
  Fails: lookup, chart (the small reader copied its instruction's example value instead of reading what was asked),
  fib (a program failing his examples was passed by the jury), arxiv, csv. After the fixes: lookup and fib pass
  (`small8`); chart and arxiv with the reader's new instruction: see `small9` and `small_only_notes.md`.
- Normal hive after all of today's check changes (`normal_reg`, `normal_reg2`): lookup, explain, arxiv, fib pass.
- Two bench checks were wrong on right answers and were corrected (papers listed by title; "135M" for "0.135B").

**Open, in order:**
1. Cleaner lessons for long plans: teach the plan after the reviewer and the code checks (`coordinator.reviewed_plan`)
   or plans from runs that passed, instead of the 4B's first plan. Then re-examine.
2. The coder's first class is held: 160 lessons, the taught 1.5B prints what the 7B's program prints on 84% of 32
   unseen lessons (untouched 66%; first scored 81% and 59%, before two corrections to the key); not graduated (one
   lesson short), holds the job in the small-only hive (`coder15+coder_school`).
   Its lessons are pure computations; a second kind is needed for what fails without the 7B: changing a working
   program on feedback without breaking it (csv), and reading a number from a fetched page.
3. Small-only arxiv and csv still fail. The item juror is now asked without the whole list's requirements
   (`verifier.item_question`); arxiv's facts still do not survive the checks. csv: see 2.
4. More roles in school: researcher (extract), critic, plan_reviewer, each with its own key.
   Built, no class held: `coder_fix` (fixing a program from the hive's own feedback; lessons from the students' real
   mistakes, `school.teach_fixes`; several hours of the 7B for a first class).
4b. Recruits (`python -m team recruit`, `team/recruit.py`, `cells/recruits.json`): the hive finds, checks, downloads
   and tries small models of other families on the roles' exams, enrols and teaches by measurement. First tryouts
   First tryouts: Yi-Coder-1.5B and SmolLM2-1.7B, neither enrolled (under the untouched students on both exams).
   `training/diverse.py`: other families share fewer mistakes but are weaker, so voting gained nothing (27 of 32, as
   the best alone); two different families printing the same was right every time (58 of 58 over five pairs): a
   check to build into the coder's run loop (run a second family's program, trust agreement, spend effort on
   disagreement).
4c. From scratch on the CPU (`python -m team harvest`, `training/scratch.py`; his order of 2026-11-10): the hive
   harvests text (own logs + open datasets, licence-checked; 48 MB so far in `memory/harvest/`, not in git), learns a
   4096-piece vocabulary, a 2.6M-weight model reads it, then is trained whole on one cell job, same rows and test as
   today's cells. Without reading first: licence_open 99% dev, 53% on unseen words. Next: `scratch.py all` after the
   reading run, table in `training/reports/scratch_cells.json`; then harvest and reading in the idle loop, and the
   hive finding datasets itself as it finds models.
5. If routing by shared words sends tasks to the wrong narrow specialist once there are several, train a router cell.
6. Older: more logged work for the item juror's site (about 60 decisions, needs about 200); near-miss numbers for
   the spawned cell; held-out set 4 (run once, on frozen code).

**This machine (a cloud VM; restarts lose running jobs, files survive):**
- Python: `/home/user/agent-team/.venv/bin/python`. Background jobs are cut at 2 hours; school visits resume.
- A 4B plan costs about a minute; a 1.7B weight edit on 128 lessons takes 25 minutes.
- `runs/` and `memory/` (logged calls, decisions, audits) are not in git and do not travel to a new session; lessons
  (`training/data/school/`), exam records (`cells/school.json`), weight edits (`adapters/`, `adapters_gguf/`) do.
  `.gitignore` skips `adapters_gguf/*2.gguf`; a narrow specialist's file there needs `git add -f`.

## What it is
A hive of small CPU models working as one. You give it one prompt and then talk to it normally (`./hive`).
- **Members:** a 4B brain (coordinator, researcher, critic, editor, jury); a 1.7B with per-role weight edits (writer, verifier, browser, order reader); a 7B coder.
- **Cells:** about 25 tiny cells (SmolLM2-135M plus a LoRA each) for the smallest decisions.
- **Checks in code:** wherever a model can let a wrong result through.
- **Always-on agent:** `python -m team serve` / `install`, an OpenAI/Anthropic-compatible API, and an SDK.
- **Budget:** CPU only, under 10 GB RAM.

Key files:
- `team/hive.py`: the loop.
- `team/specialists/*`: one file per member.
- `team/cells/*`: the cells.
- `team/guard.py`: Arnav's order rules.
- `training/*`: benches, training and measurement.
- `README.md`, `SPEC.md`: the full picture.

## Arnav's standing rules (verbatim intent)
- Everything risky happens only under his explicit order:
  - spending, deleting, sending as him, logging in, signing up, using his credentials;
  - anything he didn't order stops and asks.
- Credentials stay local, never in prompts, logs or traces. Family and relationships: only exactly as ordered.
- No benchmaxing:
  - fixes must be general;
  - held-out sets are run once, on frozen code, and reported as measured.
- CPU only, 10 GB budget, no spending. Don't delete his files. (Caches and disk on this cloud machine: his word on
  2026-11-10 is that the agent may free space as it sees fit.)
- The final report uses the headings **Blocked on me / Changed / Found**, and marks anything unconfirmed.
- Merging any PR needs **his explicit yes for that PR**. PR #5 and PR #6 had it and are merged; the next one needs it again.
- No model identifiers in commits or PRs. Commits end with the Co-Authored-By and Claude-Session lines.
- His direction: a hive of the **smallest specialists, each doing the smallest job** it can do well, working as one. Not one big model.

## Where it stands (measured; frozen code; checked against live answers)

| set | code | score |
|---|---|---|
| dev (fixes tried here) | 0147aa4 | 15/16 |
| held-out 1 / 2 / 3 (fresh tasks each, run once) | 00e1555 / d45bc04 / 0147aa4 | 9 / 11 / **13** of 16 |

Reports and causes are in `training/reports/hive_bench/*_notes.md`. 117 tests pass:
```bash
/home/user/agent-team/.venv/bin/python -m pytest -q tests
```

Measured decisions:
- **Engine:** repacked weight copies off (peak 12.9 → 7.8 GB) and the 16-bit attention cache on (1.6× faster, 8.2 GB). Prompt-lookup decoding crashes and stays off. See `arch_bench.json`.
- **Parallel jobs** (4% faster, +2.2 GB) and the **cell pool** (1.2× faster, +1 GB) stay off. See `workers.json` and `cells/pool.json`.
- **Translation goes to the 4B** (chrF 51.6). A translation edit of the 1.7B scored 48.4 and the writer 46.7 (`translator.json`; the edit is in `adapters/.rejected/translator`).
- **German grammar cell** (`de_grammar`): 135M 0.573, 0.5B 0.640, plain 1.7B 0.573, 4B 0.733.
  - The chain (1.7B, then cell, then 4B if flagged) can't beat the 4B alone, which is barely slower on short text.
  - The cell is trained but not called by the hive. See `cells/de_grammar_notes.md`.
- **answers_q** and **claims_agree** cells failed on real research text (3 of 15 real pairs right), so their jobs went to the 4B and to a code rule. Lesson: check every cell on real inputs, not just its synthetic test set (`training/evals/answers_q_real.jsonl`).
- **Research hive against one researcher** (`research_eval_notes.md`): the hive is more sourced and more honest about gaps, but 2–4× slower. Its bugs were fixed afterwards, and it hasn't been re-measured since.

## Not confirmed / open
- **Fixes made after the final freeze, with tests but no whole-task run:**
  - the browser won't give up while a next page is unread;
  - the values check skips page dumps;
  - repeated paragraphs and ordered sentence counts;
  - programs report HTTP errors (silent 404s);
  - model self-talk is dropped from reports.
  The next step is held-out set 4 (new tasks, contamination-checked with `training/contamination_check.py`), run once on a fresh frozen copy, plus `hive_bench.py new7` for dev.
- **Research hive:** re-run `training/research_eval.py` on frozen code.
- **Cells to check against real inputs:** task_kind, next_move (it chose "give up" where a retry was right), split_orders (mis-splits seen) and quote_pick. Use the same real-pair method as answers_q.
- **Not run here:**
  - growing cells from his own decisions (`python -m team grow`): the logs are nearly empty;
  - the always-on install (dry-run only);
  - anything on his device.
- **Network differs from his device.** This cloud environment blocks many sites (sqlite.org, duckdb.org; DuckDuckGo and Mojeek refuse bots). OpenAlex's anonymous budget runs out per IP; an optional `OPENALEX_API_KEY` raises it. On his device this may all work; it's unconfirmed.
- **Disk:** the session allowance is nearly full (~350 MB free). Big builds will fail; the 0.5B cell's engine file couldn't be built for that reason. Free only your own scratch, never caches.

## How to work here
- **Python:** `/home/user/agent-team/.venv/bin/python`. One llama.cpp job at a time. One cell training per process (a second one crashes with SIGILL).
- **Benches:** `training/hive_bench.py <tag> [--heldout|--heldout2|--heldout3] [--recheck]`. Run from a frozen copy: `cp -r team training tests hive` into a snapshot folder and symlink `adapters`, `adapters_gguf`, `cells`, `memory` and `demo`, so edits can't reach a run.
- **New cell:**
  1. Add a generator to `team/cells/skills.py`.
  2. Run `training/cells_incumbents.py <skill>`.
  3. Run `training/cells_research.py <skill>`.
  4. Check it on real inputs before it gets a job.
- **GitHub:** use `gh api` (REST; GraphQL returns 403). The PR is Arnav123-s/HiveMIND#7.
