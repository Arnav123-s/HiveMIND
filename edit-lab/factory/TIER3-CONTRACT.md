# Tier-3 interface contract (arch. §4, Tier 3) — final-product item 4

Status: **contract written, stub implemented** (`factory/tier3.py`).
No API keys exist for this interface, no backend is configured, and
no live call has ever been made through it. The stub validates,
audits, and refuses — fail-closed — so the loop's behavior without
Tier 3 is the tested behavior.

## What Tier 3 is for

Tier 3 (frontier models reached through this interface) is a **tool
the loop consults**, never the brain and never a judge of record.
The working precedent is this lab's own method: a frontier model
performs well as an *engineer inside a harness* — drafting,
clustering, proposing — when its output is independently verified.
Its documented boundary is why the contract exists: it indicts well
only when an indictable defect exists, so its proposals are inputs
to checkers, never verdicts.

## Request / response shape

`Tier3Request` (typed, `factory/tier3.py`):

| field | meaning |
|---|---|
| `kind` | one of the allowlist below |
| `subject_id` | the loop subject the request serves |
| `payload` | raw outputs, per-case failures, or draft material (verbatim) |
| `rationale` | **required**: why a deterministic checker cannot decide this |
| `est_input_tokens` / `est_output_tokens` | budget estimates, checked against caps before any call |
| `cycle_id` | the factory cycle the request belongs to |

`Tier3Response`: the proposal **verbatim** (text or structure),
the backend's `model_id`, and reported token `usage`.

Allowed kinds: `diagnose_proposal`, `cluster_failures`,
`draft_suite`, `review_indictment`, `judge_uncheckable` (only
where no checker exists — and the rationale must say which checker
was considered and why it cannot decide).

## Never delegate

The following are refused by the contract itself, before any
backend is consulted:

- `gate_verdict` — WIN / REVERT / HOLD come from measurements
  through the win-gate, never from a model.
- `adoption_decision` — what serves is decided by gates and
  recorded in the registry; Tier 3 may not pick winners.
- `checker_decidable` — anything a deterministic checker can
  decide is decided by the checker (cheaper, exact, auditable).
- `weight_edit` — edits are closed-form operations derived from
  maps (flip/knockout/locator evidence). Tier 3 may *review* a
  map-backed indictment (`review_indictment`); it may not author
  or apply an edit.
- `sealed_set_contents` — sealed sets are generated and sealed
  locally; their contents are never disclosed to an external
  model (that would spend them by construction).
- `spend_or_send` — no purchases, messages, or any external
  action ride this interface.

## Budget caps (defaults; tightening is free, loosening is recorded)

| cap | default |
|---|---|
| input tokens / call | 32,000 |
| output tokens / call | 4,000 |
| calls / cycle | 20 |
| total tokens / cycle | 400,000 |

Estimates are admitted against the *running* cycle budget before
the call; reported usage is charged after. A cycle that exhausts
its budget proceeds without Tier 3 — the loop never blocks on a
tool.

## Logging

Every request, refusal, and (future) response is appended verbatim
to the audit sink (JSONL) with timestamp, kind, subject, and token
accounting. The reasoning is auditable, not just the picks
(arch. §4). Refusals are records too: a refused request is evidence
the contract held.

## Fail-closed behavior

- Contract violation (kind, delegation, rationale, caps) →
  `Tier3Refused`, audited, no call.
- No backend configured (this build, always) → the request is
  validated and audited, then `Tier3NotConfigured`; the loop
  proceeds on checkers alone.
- Backend error or malformed response (future) → treated as no
  proposal: the stage that asked must fall back to its checker
  path or record a BLOCKED, never invent the missing judgment.

## Wiring a backend later

Implement one callable `Tier3Request -> Tier3Response` and pass it
as `backend=` to `Tier3Gateway`. The contract — allowlist,
never-delegate list, caps, audit — is enforced in the gateway, so
a backend cannot widen its own authority. Pricing is deliberately
absent from the contract: budgets are in tokens and calls, the two
currencies that survive provider changes (arch. §6).
