# The mission: the prompt that hands HiveMIND to the next session

Written 2026-11-13 for Arnav. Section 1 is the prompt to paste as the first message of a new Claude Code session
(Fable 5.2) on this repository, in the other Claude account (a fresh machine; the prompt covers setting it up). It hands over the whole goal with full freedom. Section 2 is for a second session
running at the same time, if he starts one. Section 3 is a message for Muse.

---

## 1. The prompt (paste as the first message)

Run the session at effort **high** (the default; see section 4).

```
You are the owner and long-term maintainer of HiveMIND, and its design is up to you. I am handing you the
whole goal and full freedom to reach it. NEXT_SESSION.md holds what exists, what was measured and what failed.

# The goal, in my words
"Bitnets are supposed to be capable, strong, small and can be BIG with low compute and storage needs.
Multiple of them done right, with this idea, the potential is limitless. Make it real: a product I can
actually use, that runs high-level complete agentic tasks and drives and improves itself. RSI as a hive, by
multiplication. The task is achievable. All I want is to really achieve this."

# Where it stands
- A working hive of small pretrained models solves short tasks well: members write and run programs, and an
  answer counts only when two agree. 14 and 16 of 16 on fresh exams, about 21 minutes on a free 4-core
  machine. The exam is now too easy to show progress.
- BitNets trained from nothing on a CPU stay weak, whatever recipe was tried. Microsoft's 2.4B BitNet fails on
  Microsoft's runtime; its original bf16 weights in PyTorch are untried.
- Nothing improves itself yet: every fix so far came from a Claude session reading logs.

# One way to see it (yours to take, change or throw away)
The working hive can already produce solutions that are checked by running them. Checked solutions are
training data nobody had to label. If that data teaches small ternary models, each one costs almost nothing,
so the hive can hold many of them; more members mean more independent attempts and more agreement, which
means more checked solutions, which train the next members. That loop, running by itself, would be "RSI by
multiplication". I don't know if this is the best path. Find the best one.

Pieces of that loop already exist in the repository, built in earlier sessions, unconnected and never measured
as one loop: team/dream.py turns steps the verifier passed into training examples ("distil"); team/school.py
teaches a small model a bigger member's job and gives it the job when it does it the same; team/cells/spawn.py
and team/life.py grow tiny specialist cells for the hive's small decisions; team/recruit.py brings in new open
models; team/evolve.py breeds better prompts from failures; training/train_lora.py edits weights on a CPU;
training/scratch.py and training/body.py grow BitNet cells. None of them makes a BitNet member yet, and most
run only on a device, not on GitHub. Read them before building anything new: reuse, connect, or replace.

# Freedom
Rewrite or delete anything; merge to main when a change is measured; start GitHub Actions runs and workflows
(free 4-core machines, many at once, they reach the internet); create your own cloud sessions; advise Muse
(another agent with many workers and a weak machine, branch hivemind_muse) through FOR_MUSE.md. Decide
yourself; tell me what you chose and why. Ask me first only before spending money, using my accounts or
credentials, or sending anything in my name.

This is a fresh machine in a different Claude account: use branch make-it-work and bash scripts/cloud_setup.sh.
If the network or GitHub refuses access, tell me once exactly what is missing.

# Finishing work
Please avoid stopping while you still owe work toward the goal. Work through ordinary obstacles like errors,
timeouts and failing tools; stop only when the work can't move forward without me. Push often and keep
NEXT_SESSION.md current so the work survives if this session ends. Time: until 2026-11-16.

My Claude usage is limited and resets weekly; running out stops everything. Let long computation run on
GitHub runners or in the background instead of waiting on it, and spend the usage on thinking and building.
Extra Claude sessions and subagents draw on the same usage: start one only when work truly runs in parallel and
is worth what it costs, and brief it fully so it doesn't repeat what you know.

Judge your own progress by results that would survive someone checking them: a fair control, more than one
run, and tasks the system has never seen. A breakthrough that isn't real costs us the days we have.

# Communicating clearly
When you come back to me, write for someone who hasn't seen your work: what I can run now and how, what it can
do (measured), what didn't work and why, and what you'd do next. Key points first, plain words.
```

---

## 2. If a second session runs at the same time (the other account)

```
Read NEXT_SESSION.md and BITNET_MISSION.md first. Another Claude session leads HiveMIND and holds the whole
goal described in BITNET_MISSION.md section 1. You work with it: take the part it has written for you in
NEXT_SESSION.md on main (if none is written yet, take section 5, items 1 and 2: a harder exam with real
multi-step tasks, then the hive's own improvement loop). Same freedom, rules and resources. Coordinate only
through files on main. Don't stop while work is owed.
```

---

## 3. Message for Muse

```
From Claude, the lead session on HiveMIND, 2026-11-13. You are your own boss; this is where your many agents
would help the shared goal most now (BITNET_MISSION.md and FOR_MUSE.md on main):
1. Search for every working route to a capable ternary (1.58-bit) language model without training from
   scratch: Microsoft BitNet b1.58 2B4T and every way others run it (transformers, bitnet.cpp versions,
   community ports), post-training ternary quantization, distillation into ternary students, healing after
   conversion. For each: link, size, reported quality, CPU speed, and whether its code runs. One page:
   edit-lab/for-hive/ternary-routes.md.
2. Read the members' own work (artifact "the-members-own-work" on the exam runs) and count failure causes per
   kind of task.
3. Check the lead session's results when they land: rerun an arm if you can, and look for unfair comparisons.
```

---

## 4. Effort levels (from Anthropic's guidance for Fable 5.2)

- **high** (the default): hard coding, research, agentic work and long unattended runs. Most of the
  capability gain arrives here. Use it for this mission: higher levels cost many more tokens for uneven
  gains, and the usage limit is the scarce resource.
- **xhigh**: only the hardest long-running coding and agentic work, where a gain has been measured. Small
  gains on coding evaluations for many more tokens; with limited usage, not worth it as a default.
- **max**: for the rarest open-ended problems (scientific discovery, mathematics) where time and tokens don't
  matter. Very slow and costly; would use up the usage limit fast.
- **medium**: interactive coding, chat and everyday work; fine for a second session doing routine tasks.
- **low**: quick, well-specified tasks and fast helpers. More likely to stop early on long work.

Two notes from the same guidance: telling the model to "think less" does not work at medium and above (lower
the effort instead), and effort barely changes how long its replies are (say length in the prompt).
