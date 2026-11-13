# Learned say for the bug-pattern composition — battery record
**Muse's work, Muse's side** (Fable-study Build 2, 2026-11-12)

## What was built
- `factory/say_dev.py` + `factory/say_dev.json` — the dev pool the
  say fits on: 216 items (fresh template families written for this
  build + the spent phase-3 held set + the factory dream screen
  pool + the swarm dream corpus), every item contamination-filtered
  against the sealed v2 set and the members' train set (47 dropped).
- `factory/learned_say.py` — seats (all 16 serving members grouped
  per class), per-seat standings + per-class thresholds fitted by
  joint coordinate ascent on composed dev verdict accuracy (strict
  improvements only), sharpness fitted as a 1-D calibration. A
  cross-entropy Adam fit was tried first and measured worse on dev
  verdict accuracy (0.569–0.579 vs the uniform rule's 0.597); the
  ascent reaches **dev 0.6528 vs uniform 0.5972, routed 0.4676**.
- Plumbing: `swarm/composers.class_margins` honors a config-carried
  say (weighted seat mean replacing fixed routing for named
  classes); the composer factory, `factory/dream.make_composer` and
  `WakingDream` now pass the serving config through (previously the
  composer re-read the config file, ignoring the caller's). Serving
  merges an adopted say into the config in `factory/serve.py`. The
  waking-dream code change is recorded in the registry the audited
  way (serving-layer sha256 updated, one field; audit clean).
- Battery: `run_battery a1b` now also runs `a1s` — fit at every
  battery run, judged in the same run. The say state lives in
  `factory/learned_say.json`, OUT of the specialist registry;
  serving honors only status "adopted".

## The sealed verdict (same battery run, full serving path)
| path | sealed acc | clean | off-by-one | wrong-op | swapped | missing-ret | mutable-def |
|---|---|---|---|---|---|---|---|
| incumbent | **0.8611** | 0.8182 | 0.6667 | 0.9 | 1.0 | 1.0 | 1.0 |
| learned say | 0.8056 | 0.6364 | 0.6667 | 0.9 | 1.0 | 1.0 | 1.0 |

**SHADOW.** The say's dev gain did not transfer: every defect class
is identical, and the whole difference is clean recall (−2 items).
The re-weighted margins make clean code lean defect-ward to the
waking layer (its clean-win gate reads the adjusted margins), so
two more clean snippets took defect verdicts. State file status:
"shadow" with this evidence; serving is unchanged and
`load_serving_say()` returns None.

## Reading
The Fable version of the say differs in one way this build could
not copy: Fable's members are probabilistic readers whose outputs
are *mixed*; here the say feeds a verify-by-execution layer whose
gates key off margin scale, so combination changes move the
verification behaviour, not just the verdict. A future attempt
should fit with the waking layer in the loop on dev (fit on
dev-path outcomes, not raw verdicts) — recorded as the next
attack, not attempted here.
