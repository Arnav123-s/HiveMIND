> **Muse's work** — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Fable validation addendum — 2026-11-11 ~15:32 PT

Audit copy refreshed: b67aad4 (2026-11-10 validation state) → **d31fd51** (current make-it-work head), 57 commits. main confirmed at 8be45ff (PR #11 merge). Method: same as VALIDATION.md — read the committed records, run the suite, check the guards in code. Read-only; nothing written to Fable's side.

## Verified at d31fd51

- **Tests: 199 passed, 0 failed** (pytest 9.2.0, torch 2.15.0+cpu, 124s). Up from 172 at b67aad4.
- **Body figures in training/reports/body.json:** fp stem alone 2.4276; second body 2.2942 — present in the committed record.
- **Three bodies as one: 2.4760** — training/reports/hive_of_bodies.json, final entry 2026-11-11 13:49 (bodies 2.4856 / 2.8412 / 2.7806 → as_one 2.476).
- **Recipe head-to-head:** training/reports/bitnet_recipe.json contains both figures — new recipe 2.9288 vs old 3.0337 at 40 min.
- **Sleep experiment:** training/reports/sleep.json dated 2026-11-11, matches commit 71e2d53's claim ("as measured, not built in").
- **Portability guards in code:** training/hive_state.py refuses to overwrite a hive with as many living cells or more (unless --force); unknown state members refused on unpack.
- **Workflows present as described:** .github/workflows/hive.yml cron `17 */6 * * *` (every 6h), exam.yml daily `43 9 * * *`, ask.yml for Actions-tab tasking; fetch-failure guard commit 1a8426f is in the tree.
- **hive-seed branch:** be80d6e (2026-11-11 08:35 PT) — seed snapshot, three bodies / 22 cells, as one 2.4760.

## Not verifiable from here

- Whether a scheduled growth turn has actually executed on GitHub's runners: the connector exposes no Actions-run or release reads. Repo state is consistent with "not yet due" — main still sits at the merge commit and the first post-merge cron slot is 16:17 PT today. No turn is overdue.

## Fetch note

A full `git fetch origin` stalls on this VM (checkpoint branch objects); fetching only make-it-work + main completes in seconds. The audit copy now tracks those two refs.
