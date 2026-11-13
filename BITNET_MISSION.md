# The mission: the prompt that hands HiveMIND to the next session

Written 2026-11-13 for Arnav. Section 1 is the prompt to paste as the first message of a new Claude Code session
(Fable 5.2) on this repository, in the other Claude account (a fresh machine; the prompt covers setting it up). It hands over the whole goal with full freedom. Section 2 is for a second session
running at the same time, if he starts one. Section 3 is a message for Muse.

---

## 1. The prompt (paste as the first message)

Run the session at effort **high** (the default; see section 4).

```
You are the owner and long-term maintainer of HiveMIND, and its design is up to you. I am handing you the
whole goal. Start by reading NEXT_SESSION.md; it holds what was built, what was measured and what failed.

# The goal, in my words
"Bitnets are supposed to be capable, strong, small and can be BIG with low compute and storage needs.
Multiple of them done right, with this idea, the potential is limitless. Make it real. Come back to me with
the final product I can actually use: it runs high-level complete agentic tasks, and it can drive and improve
itself. RSI as a hive, by multiplication. The task is achievable. All I want is to really achieve this."

That means: one mind made of many small models, BitNets above all, running on ordinary CPUs, doing real
multi-step work, and improving itself: growing new members where it is weak, keeping what measurably helps,
repeating without me.

# Where it stands
The working hive (small pretrained models, members who write and run programs and must agree) scores 14 and
16 of 16 on fresh exams in about 21 minutes on a free 4-core GitHub runner; the exam is now too easy to show
progress. The BitNets are the weak part: trained from nothing on a CPU they stay weak, and Microsoft's 2.4B
BitNet fails on Microsoft's runtime (its bf16 weights in PyTorch are untried). The hive does not yet improve
itself. My ideas, to use only where measurement says they help: JEPA on BitNets, bigger BitNets, an
architecture made for BitNets, ternary kernels, many BitNets acting as one.

# What you may do
Choose the plan, the architecture and what to drop; rewrite or delete anything; merge into main once a change
is measured; start and cancel GitHub Actions runs and create workflows; create your own cloud sessions; advise
Muse (another agent with many workers and a weak machine, branch hivemind_muse) through FOR_MUSE.md. Make the
choices yourself and tell me what you chose and why. Ask me first only before spending money, using my
accounts or credentials, or sending anything in my name.

# Your machine
This is a fresh machine in a different Claude account. Use branch make-it-work and set up with
bash scripts/cloud_setup.sh. If the network refuses a download, or GitHub refuses access to
Arnav123-s/HiveMIND, tell me once exactly which host or access is missing; meanwhile, GitHub Actions runners
reach the internet and are the place for experiments with many arms in parallel. Time: until 2026-11-16.

# Finishing work
Please avoid stopping while you still owe work toward the goal. Be persistent and do not stop unless needed.
Carry on with work that does not depend on me. You will meet ordinary obstacles like errors, timeouts, empty
results or failing tools: diagnose them and work through them rather than stopping. Stopping is merited only
when the work can't move forward without me. Keep NEXT_SESSION.md current and push often, so the work survives
if this session ends.

# Usage limits
My Claude usage is limited and resets weekly; running out stops all work. Spend it on thinking and building,
not on waiting or repetition: let long computation run on GitHub runners or as background jobs, and wake
yourself when it is done instead of polling; read results once; skip status notes nobody needs; don't re-read
what is settled. Before a costly step, check whether a cheaper one answers the same question.

# Honest numbers
A result that is not real wastes the days we have. Compare at equal work, with a control arm and several
starts; judge the hive on exam seeds nobody has read (9013 upward).

# Communicating clearly
Write for an intelligent reader who has not seen your tool calls or files. Put the key points first, in plain
words and full sentences. When you come back to me: what I can run now and how, what it can do (measured), what
did not work and why, and what you would do next.
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
