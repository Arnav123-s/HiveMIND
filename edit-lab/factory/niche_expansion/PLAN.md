# Niche-Expansion Plan — Hive Growth Department, Muse's Side

Scout report, 2026-11-12 (read-only investigation; nothing in the lab was
edited, trained, or run beyond imports/inspection). Companion file:
`picks.json` in this folder.

---

## 0. How the factory actually works (what a builder is plugging into)

### Birth machinery, end to end

- **Models** are `swarm.factory.TinyNet` (`coding/swarm/factory.py`):
  softmax-linear or one-hidden-layer MLP over a featurized bag
  (word tokens + char trigrams). Featurizer modes (`featurize`):
  `text`, `text0` (legacy sanitize), `words` (unigrams+bigrams),
  `code` (identifier-anonymized via `tokenize`: names→VAR, numbers→NUM,
  strings→STR), `secret` (literal-shape normalized), `codetext`
  (union of anonymized-code and raw-text bags, prefix-separated).
  Training is pure Python + numpy inside the training call only;
  inference is pure Python. Adoption follows the win rule everywhere.
- **`factory/growth.py::attempt_birth`** is **bug-pattern only** — it
  hardcodes `P3.gen_bug_patterns(...)` and `dream.load_bug_registry()`.
  It cannot birth a new subject. Its `_methods_arms` (recipe head-to-head
  chosen on a dev split of train, breadth-vs-concentrated edit,
  dream-first repair) is a *methods* layer for bug slices, not a generic
  entry point. **Do not try to reuse it for new niches.**
- **`factory/growth_cycle.py::run_cycle`** is likewise bug-pattern only:
  `TARGETS = [("wrong-operator","expression"), ("off-by-one","index")]`.
  Its *flow* is the template to mirror, not call: snapshot
  `composer_config.json` + `waking-dream/results.json` + `registry.json`
  bytes (plus per-model-file snapshots, the cycle-006/007 repair) →
  served battery BEFORE → births under a **dual pristine held gate**
  (phase-3 held slice + name-intent held slice, strict child > parent on
  both) → registry rebuild → battery AFTER → full audit → **any battery
  regression or audit failure rolls the births back** byte-for-byte.
  Records land as `growth/growth-cycle-NNN.md` + `.json` (runner line,
  births table, methods provenance, battery before/after table, audit
  line, harvest, novelty rotation) and `growth/ledger.jsonl`.
- **Generic subject paths that DO exist** (the ones this plan uses):
  - `factory/executors.py::subject_config(subject_id)` — a hardcoded
    table of the 5 serving jobs: niche, job text, classes, fmode,
    epochs, `train_fn`, `held_fn`, battery items. `retrain_candidates`
    trains hidden ∈ (0, 4, 8) via `F.train_candidate`, prunes, and
    reports held-out acc per size (smallest-first).
  - `factory/executors.py::run_widen_subject` — harvest pools
    (`factory/harvest_data.py::POOLS`, widen/screen/confirm per subject;
    note POOLS covers only 4 of the 5 jobs — error-class has none) →
    `contamination_filter` (exact / anonymized-shape / featurized-jaccard
    / 8-gram containment vs train+held+battery+other pools) →
    `difficulty_filter` → retrain → rank on screen only → **confirm set
    spent once** → WinGate (confirm ≥ threshold and held-out ≥ incumbent
    − 0.02) → on win, `F.save_model` writes a NEW versioned file
    `coding/swarm/models/<job>-v<N>.json` (incumbent kept as fallback).
  - `factory/dream_niches.py::run_dream_niche_subject` +
    `factory/dream_gen_niches.py::niche_generators()` — the niche-dream
    path, currently registered for exactly 2 subjects
    (contract-judgment, commit-type). Generators expose
    `gen_pool / gen_screen_pool / gen_confirm_pool` built from
    **disjoint template families per partition** (train / screen /
    confirm families are different template sets, bands 1–3), each item
    verified at generation (contract items by an execution signature,
    commit items by a verb-surface proof). This is the data-supply
    pattern every pick below copies.
  - `factory/subjects.py::load_coding_subjects` — read-only diagnosis
    loader over `phase3_results.json` + battery + highest adopted
    `-v<N>` model file per job. Not on the birth path.
- **`factory/registry.py`** — `python3 -m factory.registry` rebuilds
  `factory/registry.json` from `SPECIALIST_JOBS` (hardcoded list of the
  5 jobs) + adopted model files in `coding/swarm/models/` + the bug
  composition + the Tier-1 coordinator. **Standing serving rule:** an
  adopted version *serves* only when its measured battery slice in
  `factory/battery_evidence.json` is ≥ the incumbent's; otherwise it is
  registered as **shadow** (audited, never served). A single-version job
  serves as `entries[0]`. Every entry carries the file's sha256.
- **`factory/serve.py::ServingHive`** — generic over the registry: any
  job present in `registry["specialists"]` answers
  `{"kind":"classify","job":...,"text":...}` with provenance; an
  unregistered job returns `gap: "no specialist registered for job …"`,
  `growth_move: "registry intake (factory growth)"`. Audits files at
  load, fails closed. **No serve.py change is needed for a new job.**
- **`factory/audit.py`** — `verify_files` (every registered file exists,
  sha256 matches; ternary payloads hashed too), `verify_rule`
  (re-derives serving/fallback/shadow from battery evidence and compares
  to the book), `full_audit` (additionally re-measures every serving
  specialist on its `subject_config` held set and requires the recorded
  `heldout_acc` within TOL 0.0011, and re-measures the bug composition
  on the sealed v2 set). **Consequence: a job with no `subject_config`
  entry fails full audit** (`"no subject config to re-measure with"`).

### Interpreter (verified)

- Growth records say `python3 -m factory.growth_cycle`, and that is
  literally correct: **system `python3` is 3.12.3, has numpy 1.26.4,
  and has NO torch — and needs none.** There is no `torch` import
  anywhere in `factory/` or in `coding/swarm/factory.py` / `phase3.py`;
  TinyNet training/inference is numpy + pure Python.
- `~/workspace/edit-lab/venv/bin/python` (also 3.12.3) has
  torch 2.15.0+cpu and numpy 2.5.4. The venv is for the team.Hive / HF
  side (battery Part B, BitNet work), per `run_battery.py`'s own
  docstring — not for Tier-0 factory work.
- Builder rule: run all expansion machinery with system `python3` from
  the lab root, `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2` (VM compute
  rules). Do not "fix" the runner line to the venv.

### Which battery is authoritative

- **For the Tier-0 sections in `growth/growth-cycle-005.md`,
  `factory/run_battery.py` is authoritative.** `growth_cycle.
  measure_served_battery` imports `factory.run_battery`, redirects its
  `OUT`, and calls `part_a1()` (the five classify sections, through
  `factory.serve`), `part_a1b()` (bug-pattern on the sealed v2 set;
  in the current file this also triggers `part_a1s`, the learned-say
  section), `part_a1c()` (ternary secret-line), `part_a2()`
  (tiny-hive-ops). Results land in `results/hive_battery_acceptance.json`.
- `hive_battery.py` at the lab root is the original 2026-11-09/10
  battery: it is the **item authority** — `run_battery.part_a1` imports
  its `SECRET_ITEMS / ERROR_ITEMS / COMMIT_ITEMS / CONTRACT_ITEMS /
  GAP_ITEMS` — and it defines Part B, but its own A1 runs through the
  swarm registry, not the serving path. Items: root file. Sections,
  scores, Tier-0 overall (0.941): `factory/run_battery.py`.

### Data already on disk

- `coding/swarm/models/` — 31 files: ONLY the 5 serving jobs (plus
  versions/ternary) and the bug-pattern members. No model exists for
  any other niche.
- `coding/swarm/field.py` / `field2.py` / `field_sec.py` — the
  constructed specialists for all field + security niches. These are
  deterministic oracles: for the picks below they are the **label
  verifiers** (an item is kept only if the oracle ensemble agrees with
  its constructed label, exactly like `dream_gen_niches` verifies
  contract/commit items at generation).
- `candsets/` and `data/` (coordinator / researcher / micro sets) —
  LM-adapter and micro-specialist data; **not usable** as seed data for
  any pick here (wrong task shapes, and the coordinator contest is
  closed). Stated plainly so nobody reaches for them.
- `factory/harvest_data.py` — hand-written widen/screen/confirm pools
  for the 4 POOLS subjects; structure (paired views, group ids) is the
  template for hand-seeding a new subject's pools if a widen cycle is
  wanted later. Not needed for a first birth.
- `factory/runs/dream-niche-commit-001/`, `dream-niche-contract-001/` —
  precedent records for niche dream cycles (cycle_report.json, per-
  subject outcome.json) — the record format a new expansion cycle
  should imitate alongside the growth-cycle format.

### Serving evidence (where the hive is weak / where demand shows)

Tier-0 sections, growth-cycle-005 and `results/hive_battery_acceptance.json`
(they agree):

| section | score |
|---|---|
| classify-secret-line | **0.8333** (weakest classify section) |
| bug-pattern-composed-sealed-v2 | 0.8611 |
| classify-contract-judgment | 0.9167 |
| classify-secret-line-ternary | 0.9167 |
| classify-error-class / commit-type / gap-move / tiny-hive-ops | 1.0 |

- `factory/serve_log.jsonl` (41 lines at scout time; small and growing
  via the other agent's spawn-mining work): overwhelmingly bug-pattern
  calls, one classify (commit-type), one `coordinate` refused with
  `gap: tier1-backend-required`, and one classify refused with
  `gap: "no specialist registered for job 'nope'"` — i.e. **the serving
  path's own documented response to unregistered demand is registry
  intake**. There is no logged demand for any specific new niche; the
  honest demand signal is (a) the security branch is the weakest
  serving area, and (b) 27 of 32 swarm niches have constructed
  specialists but zero factory-served models.

---

## 1. The 32-niche inventory

Source: `coding/swarm/niches.py` — `NICHES` = 11 core +
`field_niches.FIELD_NICHES` (16) + `security_niches.SECURITY_NICHES` (5).
"Factory-served" = a TinyNet job for that niche is in
`factory/registry.json` and answers through `factory/serve.py`.
Every niche below has swarm specialists (constructed and/or model-bound)
unless noted; "swarm-only" means those specialists exist but no factory
model serves the niche.

| # | niche | factory-served status |
|---|---|---|
| 1 | coding | NOT served — root coordinator; Tier-1 coordinator winner (synthv1-r4) is registered for provenance under this tree, serving needs the LM backend (`coordinate` → gap) |
| 2 | planning | swarm-only (4 constructed + api-shape-planner model-bound, unloaded) |
| 3 | writing | swarm-only (code-extractor constructed; coder/fixer model-bound, unloaded) |
| 4 | testing | swarm-only (constructed checkers/runners + phase-2 test-analysis; test-writer model-bound) |
| 5 | debugging | **SERVED** — error-class-model (v2) + bug-pattern-composed composition (16 members, waking-dream layer) |
| 6 | review | **SERVED** — contract-judgment-model (v2 serving; v3 shadow under the standing rule) |
| 7 | integration | swarm-only (3 constructed) |
| 8 | interface | swarm-only (5 constructed) |
| 9 | compliance | swarm-only (3 constructed + semantic-checker model-bound) |
| 10 | meta | **SERVED** — gap-move-model (v3); also holds the factory/dreamer/growth specialists themselves |
| 11 | surgery | swarm-only (5 constructed, protocol specialists) |
| 12 | reading | swarm-only (9 constructed + code-explainer model-bound) |
| 13 | linting | swarm-only (9 constructed checkers) |
| 14 | refactoring | swarm-only (6 constructed + refactor-suggester model-bound) |
| 15 | documenting | swarm-only (4 constructed + docstring-writer model-bound) |
| 16 | security | **SERVED** — secret-line-model (v3 ternary serving, v2/v1 fallback, ternary alternate) |
| 17 | performance | swarm-only (3 constructed finders) |
| 18 | data | swarm-only (5 constructed parser checkers) — **PICK #2** |
| 19 | sql | swarm-only (4 constructed + sql-writer model-bound) — **PICK #3** |
| 20 | dependencies | swarm-only (4 constructed) |
| 21 | build | swarm-only (3 constructed listers/checkers) |
| 22 | vcs | **SERVED** — commit-type-model (v2) |
| 23 | regex | swarm-only (3 constructed) |
| 24 | shell | swarm-only (4 constructed finders/checkers) |
| 25 | languages | swarm-only (3 constructed + shell-writer model-bound) |
| 26 | web | swarm-only (2 constructed + api-usage-advisor model-bound) |
| 27 | translation | swarm-only (code-translator model-bound only; no constructed specialist) |
| 28 | sec-code | swarm-only (5 constructed finders in `field_sec.py`) — **PICK #1** |
| 29 | sec-deps | swarm-only (3 constructed finders) |
| 30 | sec-config | swarm-only (5 constructed finders) |
| 31 | sec-inventory | swarm-only (4 constructed, read-only /proc parsers) |
| 32 | sec-scan | swarm-only as a niche — its workspace-secret-scanner *composes* the served secret-line model + sec-scan finders; no model of its own |

Served today: 5 niches (debugging, review, meta, security, vcs),
6 jobs counting the bug composition. Everything else is unserved.

---

## 2. The three picks (ranked)

Selection rules applied: classification over generatable **and**
verifiable data; a disjoint-partition held slice must be constructible
the `dream_gen_niches` way; training must run through existing
machinery (`F.train_candidate` / `executors.retrain_candidates`,
`contamination_filter`, `F.save_model`); **no bug-pattern defect
classes**; **no birth step may require editing the other agent's
files** (see §4). All three picks are first births (no incumbent), so
the gate is the widen/dream-niche analogue, not `attempt_birth`.

### Pick #1 — sec-code: `sec-code-model`

- **Classes:** `clean`, `path-traversal`, `insecure-random`,
  `unsafe-yaml-load`, `tls-verify-off`, `ssrf` (6).
- **Justification:** The security branch is the serving hive's weakest
  area (secret-line 0.8333 is the lowest classify section) and the
  entire sec-* branch — Arnav's Phase-4 security field — has **zero**
  factory models; sec-scan already composes the one security model
  that exists. sec-code's five weakness classes are already defined
  one-per-finder in `coding/swarm/field_sec.py`
  (`path_traversal_finder`, `insecure_random_finder`,
  `unsafe_yaml_load_finder`, `tls_verify_off_finder`, `ssrf_finder`),
  so ground truth is executable, not asserted.
- **Subject definition:** `_cfg`-shaped entry mirroring
  `executors.subject_config`: niche `sec-code`, job "classify a code
  snippet by the one weakness class it contains (or clean)",
  fmode **`codetext`**, epochs 300. `codetext` is forced, not a
  preference: `code` mode anonymizes identifiers to VAR, which erases
  exactly the signal (`verify=False`, `yaml.load`, `random.` in a
  secret context, non-literal URL/path arguments); the raw-text half
  of `codetext` keeps API names while the anonymized half keeps
  structure. (Phase-4 used `codetext` for the same reason.)
- **Data / generation:** NEW `factory/niche_expansion/gen_sec_code.py`,
  patterned on `dream_gen_niches`: snippet template families in three
  disjoint partitions — train families, screen families, confirm
  families — crossed with bands 1–3 (band 1: single obvious shape;
  band 2: shape inside ordinary surrounding code; band 3: shape with
  near-miss distractors, e.g. `verify=True` beside a URL fetch =
  clean, `random.` used for a shuffle = clean). Every generated item
  is **verified before it is kept**: it must parse (`ast.parse`), and
  the `field_sec` finder ensemble must fire on exactly its labelled
  class and no other (clean = none fire) — the same
  prove-it-at-generation discipline as `verify_commit_item` /
  `contract_signature`. Items failing verification are dropped with
  reasons counted, never relabelled by hand.
- **Held gate (dual, pristine):** held-A = screen-partition families,
  fresh seed; held-B = confirm-partition families, fresh seed. Neither
  partition's templates, identifier pools, or literal pools appear in
  train. Candidate *selection* (hidden ∈ 0/4/8, recipe variants) uses
  a dev split of TRAIN only. Finalists are ranked on held-A; held-B is
  **spent once** on the single finalist. Birth requires: held-A ≥ 0.90
  AND held-B ≥ 0.90 AND per-class recall ≥ 0.80 on both AND both
  scores strictly above the strongest dumb baseline measured on the
  same slices (majority-class; and a first-token/keyword-rule baseline
  the builder writes in the generator module for reference).
- **Training entry point:** the new runner (§3)
  `python3 -m factory.niche_expansion.expansion_cycle --subject sec-code-model --cycle-id niche-expansion-001`,
  which calls `executors.retrain_candidates` + `executors.measure` +
  `executors.contamination_filter` (references = train + held-A +
  held-B + all five existing battery item sets) and, on a pass,
  `swarm.factory.save_model(finalist, extra, directory=MODELS_DIR)`.
- **Battery section:** `classify-sec-code`, 12 fresh items (2/class)
  authored in the new battery module (§3), written for the battery
  only and never trained on, bar 9/12, evaluated through
  `ServingHive.serve({"kind":"classify","job":"sec-code-model",...})`
  — the measured slice is what gets entered into
  `factory/battery_evidence.json` at adoption.
- **Registry intake:** model file `coding/swarm/models/sec-code-model.json`
  (`adopted: true`, `niche: "sec-code"`, heldout/train counts in the
  record via `save_model`'s `extra`) → the serialized adoption edits in
  §4 → `python3 -m factory.registry`.
- **Audit will check:** sha256 of the model file; serving-rule
  re-derivation (single version → serving, with its battery slice
  attached); full-audit re-measurement on the `subject_config` held set
  must reproduce the recorded `heldout_acc` within 0.0011 — which is
  why the held_fn added in §4 must be the deterministic seeded held-A
  generator, returning the identical set every call.

### Pick #2 — data: `data-format-model`

- **Classes:** `json`, `malformed-json`, `csv`, `toml`, `plain-text` (5).
- **Justification:** The data niche's five constructed specialists are
  stdlib-parser checkers (`json_validity_checker`, `csv_shape_checker`,
  `toml_validity_checker`, … in `field2.py`) — the oracle is the Python
  standard library itself, the strongest verification available
  anywhere in the lab. The hive's own working life is saturated with
  exactly these payloads (registry.json, results/*.json, jsonl logs,
  CSV exports), and format/validity triage is the classification a
  routing layer needs before any parser is chosen. `malformed-json`
  (near-JSON with a proved syntax error) keeps the task from being a
  pure first-character lookup: the model must learn JSON *shape*, the
  same reason contract-judgment is a real subject.
- **Subject definition:** niche `data`, job "classify a short text
  payload by its data format", fmode **`text`** (the `_OP_CODE`
  punctuation encoding keeps `{ } [ ] " : , =` distinct — the signal
  is punctuation shape, and `text` mode preserves it; `words` would
  throw it away), epochs 300.
- **Data / generation:** NEW `factory/niche_expansion/gen_data_format.py`.
  Generators synthesize payloads from disjoint train/screen/confirm
  surface families (different key vocabularies, value shapes, nesting
  depths, CSV column themes, TOML section styles; bands: flat →
  nested → noisy-with-comments/whitespace variation where the format
  allows). **Verification by oracle ensemble, mutual-exclusion style:**
  `json` ⇔ `json.loads` succeeds; `malformed-json` ⇔ text carries the
  JSON shape (starts with `{`/`[` after strip, quotes/braces present)
  AND `json.loads` raises; `toml` ⇔ `tomllib.loads` succeeds AND
  `json.loads` fails; `csv` ⇔ ≥3 rows, ≥2 columns, consistent width
  via the `csv` module, AND both parsers above fail; `plain-text` ⇔
  all parsers fail AND csv shape test fails. Any item whose oracle
  verdict ≠ its constructed label is dropped with the reason counted.
- **Held gate:** identical dual construction to Pick #1 (held-A screen
  families / held-B confirm families, disjoint vocabularies, dev-split
  selection, confirm spent once, ≥ 0.90 on both, per-class recall
  ≥ 0.80, beats majority baseline on both).
- **Training / battery / registry / audit:** same runner and same
  adoption path as Pick #1. Battery section `classify-data-format`,
  10 items (2/class), bar 8/10 (mirroring gap-move's 6/10 proportion),
  through `ServingHive`. Audit legs identical (hash, serving rule,
  deterministic held re-measurement).

### Pick #3 — sql: `sql-statement-model`

- **Classes:** `select`, `insert`, `update`, `delete`, `create`,
  `alter`, `drop` (7).
- **Justification:** The sql niche already has the constructed
  `sql_statement_classifier` and `sql_where_checker` (`field2.py`) and
  an unloaded model-bound `sql-writer`, but no learned specialist —
  while commit-type (the closest analogue: short conventional texts,
  `words` featurization) is a proven factory subject at battery 1.0.
  Statement-type is also the routing fact the safety-relevant
  `sql_where_checker` hangs off (UPDATE/DELETE without WHERE), so the
  battery section below reports that slice as detail.
- **Subject definition:** niche `sql`, job "classify a SQL statement
  by its leading verb class", fmode **`words`**, epochs 800 (the
  commit-type/gap-move setting for words-mode subjects).
- **Data / generation:** NEW `factory/niche_expansion/gen_sql.py`.
  Template frames per class with disjoint train/screen/confirm
  families: different table/column name pools, clause mixes (WHERE /
  JOIN / GROUP BY / ORDER BY / LIMIT / RETURNING-style tails kept
  within sqlite grammar), literal styles, case and whitespace
  variation. **Verification:** `field2.sql_statement_classifier` must
  agree with the constructed label, AND every DML/DDL item must at
  least `EXPLAIN`-compile against an in-memory `sqlite3` database
  pre-seeded with the frame's tables (items that don't compile are
  dropped, not fixed). Honest caveat, stated in the record: the
  leading verb is a near-deterministic signal, so this subject is
  expected to saturate; its value is niche coverage and a served
  routing primitive, not difficulty. It is ranked third for exactly
  that reason.
- **Held gate / training / battery / registry / audit:** same as
  Picks #1–2. Battery section `classify-sql-statement`, 14 items
  (2/class), bar 11/14, through `ServingHive`; detail string includes
  accuracy on the UPDATE/DELETE-without-WHERE subset of the items.

### Considered and rejected

- **linting** (`lint-class-model`): attractive (9 constructed checkers
  as oracles) but **3 of its natural classes are unlearnable with any
  existing featurizer** — trailing-whitespace, tab-indent and
  final-newline are erased before featurization (`_bag` squashes all
  whitespace runs; `code` mode's tokenizer drops NL/INDENT tokens).
  A token-visible subset (wildcard-import, bare-except, print-call,
  name-case classes) survives only under `codetext`. Rejected as a
  first wave pick rather than shipped crippled; revivable if a
  whitespace-preserving fmode is ever added to `coding/swarm/factory.py`.
- **sec-config / sec-deps:** same oracle pattern as sec-code and good
  second-wave candidates; two security picks in wave 1 would
  concentrate the wave in one branch.
- **dependencies** (import-origin: stdlib/third-party/local): verifiable
  via `sys.stdlib_module_names`, but "third-party vs local" has no
  closed oracle (local depends on the tree being read). Weaker ground
  truth than the three picks.
- **translation / writing / planning model-bound jobs:** no constructed
  oracle and no generatable verified data — they need an LM backend,
  which is precisely what Tier-0 is not.
- **Anything bug-pattern-adjacent** (per-class defect slices, defect
  compositions): excluded by assignment — that is the growth cycles' /
  other agent's turf.

---

## 3. The shared build recipe (all three picks)

One new runner serves all three subjects; per-subject differences live
in the three generator modules and one config table.

### Files the builder must CREATE (all new, all under `factory/niche_expansion/`)

| file | contents |
|---|---|
| `factory/niche_expansion/__init__.py` | empty/package marker |
| `factory/niche_expansion/gen_sec_code.py` | Pick #1 generator: `gen_train(seed)`, `gen_held_a(seed)`, `gen_held_b(seed)`, `verify_item(text,label)`, band/family partitions, drop-reason stats — mirrors `dream_gen_niches`' pool functions (`gen_pool/gen_screen_pool/gen_confirm_pool` signatures returning `(items, stats)`) |
| `factory/niche_expansion/gen_data_format.py` | Pick #2 generator, same interface, oracle ensemble = json/csv/tomllib |
| `factory/niche_expansion/gen_sql.py` | Pick #3 generator, same interface, oracle = `field2.sql_statement_classifier` + sqlite3 EXPLAIN |
| `factory/niche_expansion/subjects.py` | the three `_cfg`-shaped subject configs (niche, job, classes, fmode, epochs, train_fn, held_fn, battery_items) — held_fn is the deterministic seeded held-A generator; train_fn the seeded train generator. Kept here, NOT in `executors.py`'s table (see §4 for the one adoption-time exception) |
| `factory/niche_expansion/battery_sections.py` | the three fresh battery item sets + `run_sections()` evaluating them through `factory.serve.ServingHive`, writing `factory/niche_expansion/battery_results.json`; mirrors `run_battery.part_a1`'s save/detail format |
| `factory/niche_expansion/expansion_cycle.py` | the runner: `python3 -m factory.niche_expansion.expansion_cycle --subject <id> --cycle-id <id>` |
| `factory/niche_expansion/records/` | per-cycle records, growth-cycle format: `<cycle-id>.md` + `<cycle-id>.json` (runner line, gate table parent-baselines vs child on held-A/held-B, methods provenance, battery before/after incl. existing Tier-0 overall, audit line, rollback note) |
| `coding/swarm/models/sec-code-model.json` etc. | created BY the runner via `F.save_model` on a passed gate — never hand-written |

### Runner flow (`expansion_cycle.py`) — mirrors `growth_cycle.run_cycle`

1. Preflight: refuse to run if `growth/.growth.lock` exists or a
   factory run is in flight (the lab is CPU-shared; one heavy job at
   a time, threads pinned to 2).
2. Snapshot bytes: `factory/registry.json`,
   `factory/battery_evidence.json` (into `records/<cycle-id>/snapshots/`).
3. Battery BEFORE: existing Tier-0 overall via
   `factory.run_battery` parts a1/a1b/a1c/a2 (import only, OUT
   redirected as `growth_cycle.measure_served_battery` does) + the new
   subject's section from `battery_sections.py` (expected: job absent
   → recorded as no-specialist, score 0).
4. Generate train / held-A / held-B; run each generator's verifier;
   `executors.contamination_filter` against train + held-A + held-B +
   all existing battery items (both directions between partitions).
5. Dev-split recipe selection on train only (hidden 0/4/8 × the
   subject's epochs; winner by dev acc, smallest on ties — the
   `retrain_candidates` order). Train finalists; rank on held-A.
6. Spend held-B once on the best finalist. Apply the birth gate
   (§2). On failure: write the record, stop — no model file, no
   registry change, nothing to roll back.
7. On pass: `F.save_model` → new model file; run the §4 serialized
   adoption edits; `python3 -m factory.registry`; battery AFTER
   (Tier-0 + new section); `factory.audit.full_audit`. **Any Tier-0
   regression, any new-section score below its bar, or any audit
   failure rolls back**: delete the new model file, restore the two
   snapshot files byte-for-byte, rebuild the registry, re-run the
   file audit, and mark the record ROLLED BACK (growth-cycle
   discipline, incl. the cycle-006 lesson: snapshot BEFORE, restore
   bytes, never "rebuild and hope").
8. Append the cycle's entry to `factory/niche_expansion/records/ledger.jsonl`
   (the expansion department's own ledger — NOT `growth/ledger.jsonl`,
   NOT `factory/lineage.jsonl`).

### Dual held gate, constructively

For every pick: held-A and held-B come from **different template
families** (screen vs confirm partitions in the generator), different
identifier/literal pools, and different seeds; train uses a third
family set. This is the `dream_gen_niches` contract/commit partition
discipline transplanted, and it is what makes "pristine" mean
something for a synthetic subject: the child has never seen the held
families' surfaces, only the class concept from train families.

---

## 4. File-ownership map

### HANDS OFF — owned by the other agent (active edits)

`factory/serve.py`, `factory/learned_say.py`, `factory/say_dev.py`,
`factory/run_battery.py`, `factory/dream.py`, and **appends to**
`factory/registry.json` + `factory/lineage.jsonl` (spawn mining /
learned composer work).

- This plan only **imports** `serve` (read path) and `run_battery`
  (battery measurement, OUT redirected in-process — the same thing
  `growth_cycle` already does). No pick's birth touches any of them.
- Consequence, stated honestly: a new subject's section is **not**
  part of `run_battery`'s Tier-0 overall (0.941) in wave 1. It is
  measured by `niche_expansion/battery_sections.py` through the same
  serving path and reported beside Tier-0. Folding it into the
  Tier-0 overall requires a small edit to `run_battery.py`
  (one `fams` entry in `part_a1` per subject, or one call to
  `battery_sections.run_sections()`) — **deferred until the other
  agent's work lands**, and listed here as the single known
  integration debt.

### Shared files needing ONE careful serialized edit at adoption time

Adoption edits happen once per subject, in one sitting, in this
order, and only while no other agent's registry/battery work is in
flight (coordinate in the shared thread; the registry.json appends
from spawn mining are the contention point):

1. `factory/executors.py` — add one entry to `subject_config`'s table
   per subject (niche/job/classes/fmode/epochs/train_fn/held_fn/
   battery_items, pointing at `niche_expansion.subjects` /
   `battery_sections`). **Required**: without it `full_audit` fails
   the new job with "no subject config to re-measure with".
   Not on the other agent's list.
2. `factory/registry.py` — append the job name to `SPECIALIST_JOBS`
   (one line per subject). **Required**: `build_registry` only picks
   up listed jobs. Not on the other agent's list (they append to the
   *output* `registry.json`; this is the generator's source list).
3. `factory/battery_evidence.json` — add one entry per new artifact
   with its measured battery slice (from `battery_sections.py`,
   source string naming the run). **Required for an honest serving
   record**: a lone v1 serves as `entries[0]` without it, but the
   standing rule's promotion comparisons for any future v2 are
   impossible until a slice is recorded (fail-closed by design).
4. `factory/registry.json` — regenerated by `python3 -m factory.registry`
   immediately after edits 1–3. This is a rewrite of a file the other
   agent appends to: **run it once, serialized, and verify with
   `python3 -m factory.audit --files` before and after** so a
   concurrent append is detected rather than silently overwritten.
5. Optional, same sitting: `factory/subjects.py` `_BATTERY_KEY` /
   `_BATTERY_BAR` entries so the read-only diagnosis loader reports
   the new jobs' fresh scores. Cosmetic; skip if the sitting is tight.

No other shared file is touched. In particular: `factory/growth.py`,
`factory/growth_cycle.py`, `factory/dream_gen*.py`,
`factory/dream_niches.py`, `factory/harvest_data.py`,
`coding/swarm/niches.py`, `coding/swarm/field*.py`,
`coding/swarm/security_niches.py`, `hive_battery.py` — **read/import
only** (the field modules are imported as oracles; `hive_battery`'s
existing item sets are imported as contamination references).

### Safe new-file locations

Everything under `factory/niche_expansion/` (this plan's folder);
new model files under `coding/swarm/models/` created by
`F.save_model` at adoption; per-cycle run dirs under
`factory/runs/<cycle-id>/` if the builder prefers the factory
convention over `niche_expansion/records/` (pick one and say which in
the record).

---

## 5. Risks and blockers, honestly

1. **No hard blocker was found for any of the three picks.** Every
   step runs on existing machinery with system `python3`; no pick
   needs an LM backend, a download, torch, or an edit to a hands-off
   file for its birth.
2. **Registry contention is the top operational risk.** The other
   agent is actively appending to `registry.json`/`lineage.jsonl`.
   The §4 adoption sitting must be serialized with that work; the
   audit-before/after check is the tripwire. If contention cannot be
   cleared, births can still be *trained and gated* (steps 1–6 of the
   runner write nothing shared) and adoption deferred — the gate
   record stands on its own.
3. **Tier-0 integration debt** (from §4): until `run_battery.py` can
   be edited, the new sections live outside the 0.941 overall.
   Anyone quoting an "expanded overall" before that edit lands is
   mixing two batteries; the records must keep them separate.
4. **Audit's determinism demand:** `full_audit` re-measures the held
   set on every audit, forever. The generators' held-A functions must
   be pure functions of their seed (no dict-order, time, or
   filesystem dependence) or the new job will eventually fail audit
   with score drift. This is a build requirement, not a hope: the
   runner should assert `held_fn() == held_fn()` before saving.
5. **sec-code near-miss design is the scientific risk.** Bands 1–2
   alone would teach "API name present → weakness", which is wrong
   (`requests.get(url)` with a literal URL is clean; `random` for
   non-secret purposes is clean — `field_sec`'s own finders encode
   the context conditions, e.g. `_SECRET_CONTEXT`). The band-3
   distractor families are what make the subject honest; if the
   builder skimps there, expect a model that passes held slices from
   its own generator and fails the independently-authored battery
   items — the contract-judgment v3 lesson (win-gates passed,
   battery 5/12) in a new costume. The battery items must be authored
   *outside* the generator's idiom, ideally by hand first, generator
   second.
6. **sql saturation:** Pick #3 will probably hit ~1.0 everywhere.
   That is acceptable under smallest-specialist doctrine but the
   record must not oversell it; if held-B < 0.90 it indicates a
   generator/oracle bug (e.g. sqlite EXPLAIN rejecting valid frames),
   not a hard subject.
7. **CPU contention:** a BitNet scale-ladder train is running on this
   VM. TinyNet training is CPU-seconds-to-minutes, but the runner's
   preflight lock check and thread pinning are mandatory, and battery
   re-runs (which load every serving artifact) should be scheduled
   around the ladder, not against it.
8. **`codetext` vocab size (Pick #1):** the union featurizer doubles
   the feature space against the 1024-feature vocab cap in
   `swarm/factory.py::_vocab`. With small train sets this is the
   known phase-4 regime and worked there; if dev accuracy shows the
   cap binding (discriminative trigrams dropped), the fallback is
   `text` mode — decide on the dev split, never on held.

---

## 6. One-paragraph summary for the record

Wave 1 grows the serving hive from 5 niches / 6 jobs to 8 niches /
9 jobs: **sec-code** (weakness-class, `codetext`, oracle = the
`field_sec` finders), **data** (payload-format, `text`, oracle = the
stdlib parsers), **sql** (statement-type, `words`, oracle =
`field2` classifier + sqlite). All data is generated in three
disjoint template partitions and verified at generation; all births
run a new runner in `factory/niche_expansion/` that mirrors the
growth cycle's snapshot → dual pristine held gate → battery → audit →
rollback discipline while touching none of the other agent's files;
adoption itself is one serialized sitting of three small shared-file
edits (`executors.py`, `registry.py`, `battery_evidence.json`) plus a
registry rebuild.
