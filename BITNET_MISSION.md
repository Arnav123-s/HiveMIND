# The mission: the prompt that hands HiveMIND to the next session

Written 2026-11-13 for Arnav. Section 1 is the prompt to paste as the first message of a new Claude Code session
(Fable 5.2) on this repository, in the other Claude account (a fresh machine; the prompt covers setting it up). It hands over the whole goal with full freedom. Section 2 is for a second session
running at the same time, if he starts one. Section 3 is a message for Muse.

---

## 1. The prompt (paste as the first message)

```
This project is yours. I am handing you the whole goal and full freedom to reach it. Read NEXT_SESSION.md,
then this prompt again, then decide for yourself how to get there.

# What I want, in my own words (from the session that built this so far)
"bitnets are supposed to be capable, strong, small and can be BIG with low compute and storage needs,
multiple of them done right, with this idea, the potential is limitless. Make it real. Come back to me with
the final product I can actually use and run high-level complete agentic tasks, and it can drive and improve:
RSI as a hive, by multiplication."
"The task is achievable, don't doubt it. My idea seems to work; your ideas can work better, and you can make
them work stronger and better."
"All I want is to really achieve this. Make this real."

In plain terms: HiveMIND is one mind made of many small models, BitNets above all, running on ordinary CPUs,
that does real multi-step work for me and makes itself better: it grows new members where it is weak, keeps
what measurably helps, and repeats without me. Small parts, each cheap, many of them, acting as one.

# Your freedom
- The codebase is yours and its design is up to you. Rewrite, replace, delete, restructure anything,
  including what earlier sessions built, if that gets closer to the goal.
- You decide the plan, the order, the architecture, what to measure and what to drop. I do not want to
  decide; don't ask me to choose between options. Choose, and tell me what you chose and why.
- You may merge into main, start and cancel GitHub Actions runs, create workflows, create and archive your own
  cloud sessions, and direct the work of other agents.
- My ideas are ideas, not orders. Use them where measurement says they help, drop them where it says they
  don't: JEPA (LeCun's idea) on BitNets; bigger BitNets with low compute; an architecture made for BitNets,
  since they are not ordinary models ("being short-sighted will delay you"); kernels for ternary maths;
  votes and layered weights (Muse's); many BitNets acting as one.
- Ask me first only before spending money, using my credentials or accounts, or sending anything in my name.

# Where it stands (details and numbers in NEXT_SESSION.md; don't redo what is settled there)
- The working hive (small pretrained models via llama.cpp, members who write and run programs and must
  agree) scores 14 and 16 of 16 on two fresh exams in about 21 minutes on a free 4-core GitHub runner.
  The exam is now too easy to show more progress.
- The BitNets are the weak part. Trained from nothing on this CPU they stay tiny and weak, and no recipe
  change tried so far changed that. Microsoft's published 2.4B BitNet fails on Microsoft's runtime (perplexity
  70, loops). Its original bf16 weights have never been tried in PyTorch.
- The hive does not yet improve itself; every fix so far was found by a Claude session reading logs.

# You are on a fresh machine, in a different Claude account from the session that wrote this
Nothing from that session is on this machine: no Python environment, no downloaded models, no scratch files.
Everything it knew is in the repository (NEXT_SESSION.md, HANDOFF.md). First:
1. Work on branch make-it-work (git fetch origin make-it-work; git checkout make-it-work). Push your work there
   and to a claude/ branch of your own; open PRs to main and merge them yourself once measured.
2. Set up: bash scripts/cloud_setup.sh (about 20 minutes; the hive's models, about 10 GB, download on first
   use). If only the BitNet side is needed at first: bash scripts/cloud_setup.sh --light (about 3 minutes).
3. If a download is refused by the network (Hugging Face, download.pytorch.org, Wikipedia), the cloud
   environment's network settings need those hosts: ask for exactly that, once, with the hosts named
   (NEW_SESSION.md section 1 lists them). Meanwhile use GitHub Actions runners, which reach the internet.
4. If pushing to GitHub or reading Actions runs is refused, this account's GitHub connection lacks access to
   Arnav123-s/HiveMIND: say so at once; it is the one thing only I can fix.

# Resources
- This cloud machine: 4 CPU cores, about 15 GB RAM (once set up, the hive's models are cached here).
- GitHub Actions runners: free 4-core machines, several at once, jobs of hours. Experiments with many arms
  belong there, in parallel, with results as artifacts (see .github/workflows/exam.yml).
- Muse (another agent, branch hivemind_muse): many agents, a weak machine, its own boss. You are its senior
  adviser: give it reading, searching, checking and replication through FOR_MUSE.md.
- Possibly a second Claude session at the same time (BITNET_MISSION.md section 2): give it work through
  NEXT_SESSION.md on main.
- Time: until 2026-11-16 with this model. Be usage-aware: spend on what moves the goal, not on repetition,
  status notes or re-reading what is settled.

# What I ask of the way you work
- Be honest with numbers: equal work when comparing, a control arm for each claim, several starts, exam seeds
  nobody has read (9013 upward). A result that is not real wastes the days we have.
- Don't stop while work is owed. Work through ordinary errors. Don't check in between steps.
- Commit and push often and keep NEXT_SESSION.md current, so another session can continue if this one ends.
- When you come back to me: what I can run now and how, what it can do (measured), what did not work and why,
  and what you would do next. Plain words.
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
