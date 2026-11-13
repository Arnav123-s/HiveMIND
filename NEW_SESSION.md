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

Use section 1 of `BITNET_MISSION.md` (on main). It hands over the whole goal with full freedom and tells the new
session how to set up this fresh machine. (The older first message that stood here, written on 2026-11-11, is
replaced: its rules were superseded by Arnav's later word, recorded in `NEXT_SESSION.md`.)
