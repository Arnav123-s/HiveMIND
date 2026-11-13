# Using the hive

<!-- Muse's work — written by Muse, on Muse's side. -->

The hive is a set of small specialists, each trained for one
narrow job and measured before it is allowed to serve. One
command, from this directory:

```sh
cd ~/workspace/edit-lab
```

Every answer names the artifact that produced it and the score
that artifact earned. Nothing serves on a claim: at every load,
each registered artifact's bytes are checked against its
adoption record, and the command refuses to serve if anything
does not match (fail-closed).

## First: is it healthy?

```sh
python3 hive.py status
```

One screen, read live from the factory's records — the served
battery score, the six jobs and what serves them, how many
growth cycles have run and how the last one ended, the last
full audit, and whether serving is healthy right now:

```
HIVE STATUS — Muse's side
serving:  HEALTHY — the serve-time audit passes (every registered artifact matches its adoption record)
battery:  0.941 overall across 8 served sections (latest measurement: repair-cycle007-2026-11-12b, 2026-11-13 01:31 UTC)
niches:
  secret    security   secret-line-model-v3 · ternary · held-out 1.0 · battery slice 0.8333 · fallbacks 2 · substrate alternates 1
  error     debugging  error-class-model-v2 · ternary · held-out 0.9833 · battery slice 1.0 · fallbacks 1
  commit    vcs        commit-type-model-v2 · fp · held-out 0.9625 · battery slice 1.0 · fallbacks 1
  contract  review     contract-judgment-model-v2 · fp · held-out 1.0 · battery slice 0.9167 · fallbacks 1 · shadow 1 (audited, never served)
  gap       meta       gap-move-model-v3 · ternary · held-out 0.9444 · battery slice 1.0 · fallbacks 2
  bug       debugging  bug-pattern-composed · 16 members + waking-dream serving layer · sealed 0.8611 (raw composition 0.5)
growth:   7 cycles run · last growth-cycle-007: battery 0.941 -> 0.9375 · births off-by-one-index, wrong-operator-expression · alert filed · repaired by repair-cycle007-2026-11-12b: battery restored to 0.941, audit OK
audit:    last full audit OK — repair-cycle007-2026-11-12b, 2026-11-13 01:31 UTC (0 failure(s))
```

## The six jobs

**Secret line** — is this line a hard-coded secret or benign?

```sh
python3 hive.py secret 'api_key = "sk-live-9f27ac41bd"'
# ANSWER: secret
# served by: secret-line-model-v3 (ternary, held-out 1.0)
```

**Error class** — which exception does this failure text show?

```sh
python3 hive.py error 'Traceback (most recent call last):
  File "app.py", line 14, in <module>
    print(user["email"])
KeyError: email'
# ANSWER: KeyError
# served by: error-class-model-v2 (ternary, held-out 0.9833)
```

**Commit type** — the conventional-commit type of a message:

```sh
python3 hive.py commit 'repair the broken cart total calculation'
# ANSWER: fix
# served by: commit-type-model-v2 (fp, held-out 0.9625)
```

**Contract judgment** — does this snippet break the house contract
(it must not mutate its input, and must be empty-safe and
none-safe)? Code goes in with `--file`:

```sh
python3 hive.py contract --file snippet.py
# ANSWER: no-empty-guard
# served by: contract-judgment-model-v2 (fp, held-out 1.0)
```

**Gap move** — what growth move does this failure/lesson call for?

```sh
python3 hive.py gap 'the model keeps failing on inputs it has never seen; we need broader training coverage'
# ANSWER: harvest
# served by: gap-move-model-v3 (ternary, held-out 0.9444)
```

**Bug pattern** — what defect does this function carry (or is it
clean)? Served through the waking-dream layer: candidate defects
must prove themselves by execution before they are believed, and
the output says whether verification fired:

```sh
python3 hive.py bug --file buggy.py
# ANSWER: swapped-operands
# served by: bug-pattern-composed (16 members) + waking-dream serving layer
# waking-dream: VERIFIED swapped-operands by execution (composer alone said clean)
```

## What the scores mean

- **Held-out** — the artifact's score on examples it never
  trained on. This is the number printed with every answer.
- **Battery slice** — the artifact's score on its section of
  the fixed acceptance battery, run through the real serving
  path. A new version only replaces the serving one when its
  battery slice is at least the incumbent's; otherwise it is
  *shadow* — on the books, audited, never served.
- **Battery overall** (in `status`) — the average of the eight
  served battery sections at the latest measurement.
  **0.941** currently.
- **Sealed** — the bug-pattern score on a locked exam set that
  is never trained on. The served path scores **0.8611** there;
  the raw composition without the waking-dream layer scores 0.5.

## What happens automatically

- **Growth cycles** run on their own (about every 6 hours):
  they try to improve the bug-pattern members with new training
  data and methods. A change is adopted only if the served
  battery does not regress and a full audit passes; otherwise
  the cycle rolls back and files an alert. Cycle 7 regressed
  and its rollback crashed — the repair is part of the record
  `status` shows, not hidden by it.
- **Audits**: the serve-time check runs on every command (any
  mismatch refuses the whole load); a full audit, which also
  re-measures scores, runs after growth cycles and repairs.

## Extras

- `python3 hive.py jobs` — list every serving artifact, its
  substrate, held-out and battery scores, the fallback chain,
  and what is shadowed (adopted but never served).
- `--substrate ternary|fp` on any classify job names a substrate
  instead of the serving default (e.g. the secret-line ternary
  pack: `python3 hive.py secret --substrate ternary '...'`).
- Code-typed jobs (`contract`, `bug`) accept inline text too;
  `--file` is just easier for multi-line code.
