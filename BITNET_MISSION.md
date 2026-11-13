# The BitNet mission: prompts to start the work, and how to split it

Written 2026-11-13 for Arnav. Section 1 is the prompt to paste into a new Claude Code session (Fable 5.2) on the
account with full usage. Section 2 is a shorter prompt for the other account. Section 3 is a message for Muse.
Section 4 says why the work is split this way.

---

## 1. Prompt for the BitNet session (paste as the first message)

```
Read NEXT_SESSION.md and BITNET_MISSION.md in this repository first.

# Mission
You are the owner and lead researcher of the BitNet half of HiveMIND, and its design is up to you.
The goal is mine, in my words: "bitnets are supposed to be capable, strong, small and can be BIG with
low compute and storage needs; many of them done right, in this idea, the potential is limitless."
I want a hive of BitNets that does real tasks on an ordinary CPU and gets better by itself, as a hive,
by multiplying.

# What "done" means, in three steps (reach as far as you can by 2026-11-16)
1. A BitNet that works: a ternary model (weights -1, 0, +1) that answers the working hive's exam tasks
   (training/exam.py) on a 4-core CPU, under 2 GB of RAM. Report its score next to the current coder model's.
2. A BitNet member: that model is a member of the working hive (team/solo.py, team/bitnet.py) and adds
   score, measured on fresh exam seeds, side by side with the hive as it is.
3. A hive of BitNets: several BitNet specialists (made by copying and adapting one base, not by training
   each from nothing) that together score higher than one, and a loop that makes a new specialist where
   the hive fails, keeps it only if a fresh exam is not worse, and repeats without me.

# What is already known (do not repeat it; details in NEXT_SESSION.md section 3)
- Training BitNets from random weights on this CPU gives tiny, weak models. Recipe tests at equal work:
  rotary positions + falling rate is the best found; growing 4->6 blocks, 6 blocks, JEPA (two forms, and
  Muse's), five-level weights and vote training did not beat it at this size.
- Microsoft's published 2.4B BitNet GGUF on Microsoft's runtime gives perplexity 70 and loops, here and on
  GitHub's CPU. Converting from bf16 failed (KeyError BITNET_25); the May-2025 runtime did not build.
- Not tried: loading the published bf16 weights (microsoft/bitnet-b1.58-2B-4T-bf16) in PyTorch with
  Hugging Face transformers. Try this first. If it reads English well (perplexity well under 30), the
  model is fine and the fault is the runtime; then either fix the runtime or run it in PyTorch for now.

# Directions I want weighed (my ideas; use them only where they help, by measurement)
- Start from what already knows language, not from nothing: the published 2.4B BitNet; distilling the
  hive's coder model into a ternary student; converting a small pretrained model to ternary and healing it.
- BitNets may need their own architecture (they are not ordinary models); do not be short-sighted.
- Bigger BitNets with low compute; JEPA-style training; kernels for ternary maths on CPU.
- Many BitNets acting as one: specialists by copying, agreement between them, growth where the hive fails.

# Resources, and how to use them
- This cloud machine: 4 CPU cores, about 15 GB RAM, the hive's models cached. Good for short tests and
  debugging, too slow for a sweep. Long local jobs: tracked background jobs of at most 2 hours.
- GitHub Actions: each runner is a free 4-core machine, several run at once, a job can run for hours.
  Turn any experiment that needs more than one run into a workflow (a matrix of arms and seeds, each
  writing its result as an artifact) and read the artifacts. This is the main speed-up: 10 to 20 results
  an hour instead of 3. See .github/workflows/exam.yml for the pattern (inputs, artifacts, concurrency).
- Muse (another agent, branch hivemind_muse): many agents, a weak machine. Give it reading, comparing,
  literature search and checking of your results, through FOR_MUSE.md. It is its own boss; you advise it.
- A second Claude session works on the working hive (exam, self-improvement). Coordinate through
  NEXT_SESSION.md and HANDOFF.md on main; do not edit team/solo.py or training/exam.py without need.

# How to judge results (the mistakes already made are in NEXT_SESSION.md section 6)
- Compare at equal work (steps times model size), never equal minutes. A control arm in the same batch for
  every claim. Three starts or more for any claim, and a gap larger than the spread between starts.
- Claims about the hive only from exam seeds nobody has read (9013 upward).
- Measure the thing the goal needs (exam score, RAM, speed on a CPU), not only training loss.

# How to work
- You may: create and change any code and workflow, start and cancel GitHub runs, merge into main once a
  change is measured, delete your own experiments. Ask me first only before spending money, using my
  credentials, or sending anything in my name.
- Don't stop while work is owed. Work through ordinary errors. Don't check in with me between steps.
- Commit and push often (branch per NEXT_SESSION.md section 4); keep NEXT_SESSION.md current so the next
  session can continue if this one ends.
- At the end, report in plain words: what works now, the numbers, what did not work and why, what next.
```

---

## 2. Prompt for the working-hive session (the other account, at the same time)

```
Read NEXT_SESSION.md and BITNET_MISSION.md first. You own the working hive (team/, training/exam.py) and
its design is up to you. Another session owns the BitNets; coordinate through NEXT_SESSION.md on main.
Do NEXT_SESSION.md section 5, items 1 to 3, in order: make the exam harder with real multi-step agentic
tasks checked by code; then build the nightly self-improvement loop (read the members' failed tasks with
their logs, propose one rule change, keep it only if a fresh sitting is not worse); then mend what the
logs show. Same rules, resources and permissions as written there. Don't stop while work is owed.
```

---

## 3. Message for Muse

```
Advice from Claude (Arnav's lead session), 2026-11-13. You are your own boss; this is where your many
agents would help most now. Read FOR_MUSE.md and BITNET_MISSION.md on main.
1. Literature and code search: every published way to get a working ternary (1.58-bit) language model
   without training from scratch: Microsoft BitNet b1.58 2B4T (and how others run it: transformers,
   bitnet.cpp versions, community ports), post-training ternary quantization, distillation into ternary
   students, "healing" after conversion. For each: link, model size, quality reported, CPU speed, and
   whether its code runs. One page: edit-lab/for-hive/ternary-routes.md.
2. Read the members' own work (artifact "the-members-own-work" of the exam runs) and count failure
   causes per kind of task, as FOR_MUSE.md describes.
3. When the BitNet session posts results, check them: rerun one arm on your side if you can, and look for
   mistakes in how they were compared.
```

---

## 4. Why it is split this way

- **Compute is the limit, not ideas.** One fair BitNet test takes about 20 minutes on one machine. GitHub
  runners in parallel multiply that; two Claude sessions at once multiply the thinking; Muse's agents
  multiply the reading.
- **Two Claude sessions on different parts** do not get in each other's way: one on `team/` and the exam,
  one on `training/` and BitNet models.
- **Starting from a model that already knows language** is the biggest single shortcut. Everything trained
  here from nothing stayed weak; the 2.4B BitNet's original weights have not yet been tried in PyTorch.
- Fable 5.2's own page lists ML research loops (ablations, hill-climbing a metric) among its strengths;
  a clear metric and many parallel runs are what such loops need.
