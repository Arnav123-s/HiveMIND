# Starting HiveMIND again in a new Claude Code session

## 1. The cloud environment (once, in claude.ai/code when you create the environment)
- Repository: `Arnav123-s/HiveMIND` (connect GitHub first: claude.ai Settings, Connectors).
- Network (as found on 2026-11-11): the default ("Trusted") reaches package registries, GitHub and most of the web,
  and refuses `download.pytorch.org`, Hugging Face and Wikipedia. With the default the setup below still works (torch
  then comes from PyPI, 5 GB bigger); a body's turn reads the text the hive has (no turn was run there), a harvest
  cannot run. For
  the harvest allow `en.wikipedia.org` and `huggingface.co`; for the working hive `huggingface.co` and the hosts its
  models download from (`cdn-lfs.huggingface.co`, `cas-bridge.xethub.hf.co`); for the small torch `download.pytorch.org`.
- Setup script (paste into the environment's setup script box; it runs once per fresh machine):

```bash
for d in HiveMIND hivemind; do
  if [ -d "$d" ]; then (cd "$d" && git fetch -q origin make-it-work && git checkout -q make-it-work && bash scripts/cloud_setup.sh --light); fi
done
```

`--light` installs only the growing hive (~3 minutes). For the working hive (the one that answers tasks), run
`bash scripts/cloud_setup.sh` inside the session instead (~20 minutes, ~10 GB of models on first use).

## 2. Start things again (inside the session)

```bash
bash scripts/resume.sh status
```

```bash
bash scripts/resume.sh grow
```

`exam` (needs the full setup) and `ask "a task"` are the other commands; `stop` stops what it started.

## 3. The first message to the new session (Fable 5.2)

Copy everything in the box, write your idea where it says so, and send it.

```
You are picking up HiveMIND (github.com/Arnav123-s/HiveMIND), a project I (Arnav) have been building with Claude
in another account. That session is gone; everything it knew is in the repository.

Before anything else:
1. Check out the branch make-it-work. Read, in this order: the "START HERE" block at the top of HANDOFF.md, then
   "Live status" in HANDOFF.md, then README.md. Skim SPEC.md.
2. Run: bash scripts/resume.sh status   (if .venv is missing, first: bash scripts/cloud_setup.sh --light)
3. Tell me back, in a few lines, what you understood: the two hives (the working hive of small pretrained models
   with tools and checks, and the growing hive of BitNet bodies trained from nothing), what runs on its own on
   GitHub, and what is unfinished. Do not start building yet.

Then listen to my idea below. It may have flaws and is open ended: find the flaws, tell me plainly what will and
will not work on CPU-only machines, and propose the strongest version of it you can, with how we would measure
that it is better. Ask me only what you truly cannot decide yourself.

MY IDEA:
<write your idea here, in your own words, as long as you like>

My standing rules (from HANDOFF.md, keep them):
- Risky actions (spending money, deleting, sending anything as me, logging in, using credentials) only when I say so.
- No benchmaxing: held-out sets run once, on frozen code, reported as measured. Never tune on a test.
- CPU only. No model names in commits or PRs.
- Every merge into main needs my explicit yes for that PR.
- Reports use the headings Blocked on me / Changed / Found, and mark anything not confirmed.
- Commit and push before ending a turn.
```
