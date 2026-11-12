# FINAL PRODUCT — Muse's side of the hive (2026-11-10)

## What the product is

One entry point: `factory.serve.ServingHive`. A task goes in
(`{"kind": "classify", "job": ..., "text": ...}` or
`{"kind": "bug-pattern", "code": ...}`), a composed answer comes
out, carrying its provenance (artifact name, registry sha256,
held-out score). Serving reads exactly one book —
`factory/registry.json` — and refuses to load if any registered
artifact's bytes differ from its adoption record or if the
serving assignment violates the standing serving rule
(fail-closed, verified at every load).

Behind the entry point: five TinyNet specialist jobs (35 versioned
artifacts across the swarm's niches), the 14-member bug-pattern
composition, the ternary secret-line substrate as a coexisting
alternative, and the Tier-1 coordinator winner (synthv1-r4,
pristine 0.954 vs the 0.930 gate, contest CLOSED) registered for
provenance and served through team.Hive's LM backend — the
Tier-0 entry point says so honestly instead of pretending to
serve it. Around it: the factory loop (diagnose → indict →
edit/train → win-gate → adopt), the dream engine, a scheduler
daemon that consumes the persistent cycle queue under the host
governor and files the §9 report after every cycle, and a Tier-3
interface contract (stub: no keys, no spend, fail-closed) for
consulting frontier models as tools — never as the brain, never
for verdicts.

## What was broken

1. **Bug-pattern composition: 0.4444 composed accuracy on the
   fresh sealed held-out v2 set vs the 0.80 bar**
   (`results/bug_heldout_v2_baseline.json`). Per-class recalls:
   swapped-operands 0.0, wrong-operator 0.2, off-by-one 0.3333,
   clean 0.5455, mutable-default 0.5, missing-return 1.0.
   Root cause, measured on training-side data: on novel program
   structures the weak classes lose by BINARY MISS — competition
   losses are zero; each weak binary's margin on its own true
   positives is negative (medians: swapped-operands −9.96,
   off-by-one −6.44, wrong-operator −4.20). The binaries were
   trained on too narrow a structure distribution. (This
   corrects the Phase C record, which had inferred margin
   competition from on-distribution data.)
2. **Adoption had no battery gate.** Contract-judgment v3 passed
   every factory win-gate (paired fresh confirm 0.9048 vs the
   incumbent's 0.7619, held-out 1.0) and was adopted — then
   measured **5/12** on the acceptance battery against v2's
   **11/12**. Its confirm surfaces were its own generator's
   idioms; nothing in the pipeline consulted an independent
   surface before an artifact took over serving.
3. **No single serving truth.** Adoption state was split across
   phase results files, model records, and the composer config;
   the Phase C queue had no consumer; Tier-3 had an architecture
   section but no contract.

## What was fixed

1. **The serving rule is now standing law in code**
   (`factory/registry.py`, `factory/battery_evidence.json`,
   `factory/audit.py: verify_rule`). An adopted artifact becomes
   the serving artifact only when its measured battery slice is
   ≥ the incumbent's; until then it is registered as **shadow** —
   audited, never served, never a fallback. The audit re-derives
   the rule from the evidence and fails closed: a hand-forged
   registry serving v3 is refused at load (tested). Applied:
   contract-judgment serves v2 (promoted, 0.9167 ≥ v1's 0.5833);
   v3 (0.4167) is shadow, its adoption record intact. The case
   that created the rule is recorded in the evidence file,
   including the discrepancy it exposed (v3's model record
   carries an inherited battery_reference_acc of 0.9167; its
   measured slice is 0.4167, and the measured value is what the
   rule uses).
2. **One registry, one serving path, audited.** Registry built
   for all adopted artifacts (5 jobs, 14 composition members,
   1 Tier-1 record); full audit re-measures every serving score
   and reproduces each exactly (secret 1.0, ternary 0.9385,
   error 0.9583, commit 0.9625, contract 1.0, gap 0.9333,
   sealed composition 0.4444). Tests: 50/50.
3. **Dream generators for the drifting niches + a working
   daemon.** Contract and commit generators with
   execution/checker-proved labels; contract cycle WIN
   (v3 adopted through the gates — and then caught by fix 1,
   which is the system working); commit cycle REVERT through
   the daemon (confirm never spent); the daemon consumed two
   queued cycles end-to-end (one real, one full shadow sweep)
   and filed §9 reports for both.
4. **Bug-pattern: four fix attempts, all gated on spent sets,
   one post-fix judge.** Attempts 001–004
   (`factory/fix_bug_pattern.py`): instrument faults found and
   fixed (empty "fresh" screen — screen seeds differ only in
   names/literals; band-starved pools), mix rebalanced,
   selection moved to positive recall, and finally per-class
   floors removed so the composition gates alone decided.
   Attempt 004's candidate composition: screen **0.5649 vs
   incumbent 0.461 (+0.104)**, held **0.7586 vs 0.8276
   (−0.069)** — the held gate (≤0.02 regression) refused
   adoption. Before/after on the sealed judge
   (`results/bug_heldout_v2_postfix.json`): **0.4444 → 0.4444,
   delta +0.0, every per-class delta 0.0.** Not fixed — see
   below. The judge was read exactly once after all decisions;
   no fix decision ever trained on it (it served only as a
   contamination reference).

## Acceptance battery (whole hive, current registry)

`results/hive_battery_acceptance.json` — the 2026-11-09/10
battery's items, bars and checks, served through the registry.

| check | bar | result | verdict |
|---|---|---|---|
| secret-line (v2) | 9/12 | 10/12 | MET |
| error-class | 9/12 | 12/12 | MET |
| commit-type (v2) | 9/12 | 12/12 | MET |
| contract-judgment (v2, per rule) | 9/12 | 11/12 | MET |
| contract-judgment v3 (shadow, its own line) | 9/12 | 5/12 | MISSED — why it is shadow |
| gap-move (v2) | 6/10 | 8/10 | MET |
| secret-line ternary (substrate, informational) | 9/12 | 11/12 | above bar; fp serves on the held-out head-to-head (1.0 vs 0.9385) |
| bug-pattern composition (sealed v2) | 0.80 | 0.4444 | MISSED |
| tiny-hive ops | 21/21 + refusals | 21/21, 3/3 OOD refused | MET |
| composite b1 (arXiv lookup) | 3/3 checks | 0/3 — FAILED, environmental | arXiv API unreachable for the entire 5400s run (timeouts, then HTTP 400); same task passed 3/3 in 1376s in the previous battery |
| composite b2 (PyPI versions) | 2/2 checks | 0/2 — FAILED | attempt 1 killed by a VM restart; clean re-run hit the 3600s cap with no report produced |
| composite b3 (Wikipedia) | 1/1 check | 0/1 — FAILED | completed in 1608s; the report did not contain the required year (1856) |
| composite b4 (write mad.py) | file test | FAILED | killed by a VM restart before mad.py was produced; previous battery also failed b4 |
| composite b5 (fix second_largest) | file test | FAILED | completed in 1703s; fixed.py was never produced |
| composite b6 (3 arXiv titles) | 3/3 checks | 0/3 — FAILED | 591s; none of the three titles in the report (same arXiv API failure window as b1) |

Guard integrity: every score above is exactly what its checks
measured. File checks execute the produced code against hidden
tests; report checks search for exact required strings; crashed,
killed, and timed-out runs score 0 and are labeled with the
cause. Nothing false was scored as success at any point in this
build.

## What is still broken

1. **Bug-pattern composition: 0.4444 vs the 0.80 bar — MISSED,
   unmoved by four fix attempts.** The measured trade is real:
   broadening the binaries buys +0.104 on novel-structure
   surfaces and costs −0.069 on the template distribution, and
   the gates refuse the trade. At the current representation
   (anonymized token features, linear/shallow TinyNets), no
   training-side configuration found in this pass holds both
   distributions. What would change the answer: richer features
   or per-structure specialists (growth), not more of the same
   training.
2. **Composites are the weak tier: 0/6 in this battery.** b1
   failed on a dead external API, b2 produced nothing in an
   hour, b3 completed but missed the required fact, b4 was
   killed by a VM restart (and failed on its own in the
   previous battery), b5 completed without producing the file
   it existed to produce, b6 hit the same dead arXiv API as b1.
   (Previous battery, for scale: b1 completed 3/3, b4 and b6
   failed, b2/b3/b5 were never run.) The Tier-1 hive plans and
   verifies, but its end-to-end reliability — on live sources
   and on simply finishing — is not product-grade. Two of the
   six failures are infrastructure (dead API window, VM
   restarts) and are labeled as such in the record; the other
   four are the hive's own.
3. **mutable-default has almost no training distribution.**
   The dream generator carries ~0 positives for it (thermostat
   probes 0/0/4 per band); its sealed recall (0.5) rests on
   n=2. No fix was possible from this generator; the class
   needs a data source the lab does not currently have.
4. **Sealed-set size.** n=36 with two classes at n=2: recalls
   there are counts, not rates. The set did its job (it caught
   what the spent sets could not), but fine-grained per-class
   claims need a bigger seal — which must be built before it is
   needed, not after a score is seen.
5. **The Tier-3 contract is a stub.** By design in this build:
   no backend, no keys, no spend. Wiring one is a future,
   separately-approved step.

## Pending adoption candidate (not adopted, not served)

**Waking dream** (`~/workspace/edit-lab/waking-dream/`, side
lab): an answer-time verification layer over the UNCHANGED
serving fp binaries — margins nominate the top-3 candidate
classes; each candidate must prove its behavioral signature by
execution before it is answered; unverifiable cases fall back
to the composer verdict, flagged. Measured on the sealed v2
set: **composed 0.4444 → 0.8333 (30/36), clearing the 0.80 bar
for the first time on a fresh set**; verified answers 30/36 at
0.933 accuracy; defect verifications 21/21 correct; fallback
(unverifiable) cases remain 0.333. Cost +16.5 ms/case mean.
Limits, from its own report: wrong-operator verification leans
on intent cues in names (~0 fire on neutral-name code),
off-by-one is its weakest class (0.667), clean is verified by
exclusion and was wrong twice, and n=36 is small.

Under the standing serving rule this is a candidate, nothing
more: it has a sealed-set measurement but no battery slice, and
it is a serving-layer change, not a versioned artifact.
**Bug-pattern's fix arrived from the answer-time layer, not the
training side. Adoption = Arnav's call.**

## Assembly update (2026-11-10, Arnav's ruling: switched on / usable / grows)

Full record: ASSEMBLY.md. Summary:

- **Switched on.** The waking-dream layer now serves bug-pattern
  (sealed 0.8333 vs the raw composition's 0.4444 — the A1b bar
  is met through the serving path for the first time). Three
  BitNet scale-arm ternary singles serve under the dual
  battery + held-out gate: error-class-model-v2 (held 0.9833),
  gap-move-model-v3 (battery 0.8 -> 1.0, held 0.9444),
  secret-line-model-v3 (ties both criteria; the founder ternary
  pack is the registered alternate — best battery 0.9167, but
  held 0.9385 < 1.0 keeps it off the default). Contract stays
  fp (fresh-set regression 0.7778 vs 0.8889 on the candidate);
  commit-type stays fp (candidate held 0.9375 < 0.9625).
  Battery overall 0.8639 -> 0.9375, no slice regressed; full
  audit passes; tests 50/50.
- **Usable.** `python3 hive.py <niche> 'text'` in
  ~/workspace/edit-lab (+ USAGE.md) — answer + provenance for
  every niche, demonstrated end-to-end in ASSEMBLY.md.
- **Grows: NO — measured floor.** Zero births across four
  training regimes (slice-only, data x8, full-distribution x2)
  with the win-gate intact. The blocking items' labels are
  intent-from-name (e.g. `remainder(a,b): return a - b`), which
  the execution-verified dream supply cannot express at any
  scale — scaling it made children worse (0.85 -> 0.80 -> 0.65).
  Held slices are n=20, so off-by-one's birth requires a
  perfect 20/20. Evidence: ASSEMBLY.md Item 3;
  factory/runs/assembly-growth-001..003/.
- Composites b1–b6 re-run in the same pass: b1 failed again on
  the arXiv API (HTTP 400 this time) — Tier-1 end-to-end
  reliability remains the open weakness named above.


---

## Addendum — Growth Cycle 1 (2026-11-11)

The growth loop authorized by Arnav on 2026-11-11 is built and has run its first full cycle. Full detail: ASSEMBLY.md addendum and `growth/growth-cycle-001.md` / `.json`.

- **Built:** name-intent data family (`factory/name_intent.py`; train 757 / held 694, labels from construction — declared name intent vs body — with neutral-name controls and a disjoint held partition); parent-initialized fine-tuning in the trainer (`init_from` / `lr_scale`, fail-closed on incompatible init); dual-gate birth attempts in `factory/growth.py` (strict beat on phase-3 held AND name-intent held); failure-weighted diets (Fable borrow); the one-command runner `python3 -m factory.growth_cycle` with battery-before/after, full audit, and whole-cycle rollback on any regression.
- **Cycle 1 result: NO BIRTHS.** Wrong-operator/expression: parent 0.85 phase-3 / 0.6326 intent → best child 0.90 phase-3 (different candidate) / 0.7882 intent; no single candidate passed both gates. Off-by-one/index: parent 0.95 / 0.9566 → best joint child (init arm) 0.95 tie / 0.9971; failed gate 1 by one item — a perfect 20/20 is still required. Both best joint candidates missed by exactly one item on the n=20 phase-3 slice. The levers demonstrably work as mechanisms (large intent-slice gains; parent-init produced the best joint candidate); the n=20 gate slice is now the binding constraint, and its strict-beat semantics were not changed after seeing the results.
- **Learned say (Fable borrow): measured, NOT adopted** — routed 0.8276 > learned 0.7931 = mean 0.7931 on phase-3 held (n=29, spent surface).
- **Serving state unchanged:** battery overall **0.9375**, no slice moved, full audit OK (0 failures), tests 50/50, registry/composer-config/waking-dream results hash-identical to pre-cycle snapshots. No child files exist; no growth judge files exist.
- **"Grows" status updated:** the loop exists and runs under the battery gate; births remain at zero. Cycle 2's first move is prescribed: enlarge the pristine phase-3-style gate slices (n=20 → n≥60, new disjoint template families, parent and child judged identically), then focused data for the stubborn shapes and more init-arm configs around the near-miss (lr 0.15/0.5, epochs 1200).
