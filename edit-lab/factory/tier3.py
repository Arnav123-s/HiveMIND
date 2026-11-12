"""Tier-3 interface contract — as code (arch. section 4, Tier 3;
final-product item 4). STUB ONLY: no API keys, no network, no
spend. The gateway validates every request against the contract
(kind allowlist, never-delegate list, budget caps), writes an
audit record, and then refuses with Tier3NotConfigured — because
no backend is configured, by design, in this build. Wiring a real
backend later means implementing `propose` behind this same
contract, not bypassing it.

The contract in one paragraph (full text: TIER3-CONTRACT.md):
Tier 3 is a TOOL the loop may consult — diagnosis proposals,
failure clustering, suite drafting, indictment review, judging
only where no checker exists. It must NEVER be delegated: gate
verdicts, adoption decisions, anything a checker can decide,
weight edits themselves, or the contents of sealed sets. Every
proposal is logged verbatim in the audit sink so the reasoning is
auditable, not just the picks; checkers and sealed tests dispose.
"""
from __future__ import annotations

import dataclasses
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------ the contract
ALLOWED_KINDS = {
    "diagnose_proposal",     # propose failure clusters from raw outputs
    "cluster_failures",      # group per-case failures (checker verifies)
    "draft_suite",           # draft candidate eval cases (contamination-checked later)
    "review_indictment",     # second opinion on a map-backed indictment
    "judge_uncheckable",     # judge ONLY where no checker exists
}
NEVER_DELEGATE = {
    "gate_verdict",          # WIN / REVERT / HOLD are the loop's, from measurements
    "adoption_decision",     # what serves is decided by the win-gate, not a model
    "checker_decidable",     # anything a deterministic checker can decide
    "weight_edit",           # edits are closed-form ops from maps, never authored by Tier 3
    "sealed_set_contents",   # sealed sets are generated + sealed locally, never disclosed
    "spend_or_send",         # no purchases, no messages, no external actions
}


@dataclass
class BudgetCaps:
    """Per-call and per-cycle ceilings. Config may tighten; loosening
    is an explicit, recorded act (arch. section 6)."""
    max_input_tokens_per_call: int = 32_000
    max_output_tokens_per_call: int = 4_000
    max_calls_per_cycle: int = 20
    max_total_tokens_per_cycle: int = 400_000

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class Tier3Request:
    kind: str                              # one of ALLOWED_KINDS
    subject_id: str
    payload: Dict[str, Any]                # raw outputs / cases / draft material
    rationale: str                         # why a checker cannot decide this
    est_input_tokens: int = 0
    est_output_tokens: int = 0
    cycle_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class Tier3Response:
    kind: str
    subject_id: str
    proposal: Any                          # verbatim proposal (text or structure)
    model_id: str
    usage: Dict[str, int]                  # tokens in/out as reported by the backend
    logged_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


class Tier3Refused(Exception):
    """The contract refused the request (kind, delegation, or caps).
    Refusals are audit records too."""


class Tier3NotConfigured(Exception):
    """The request was contract-valid but no backend is configured.
    This stub raises it for every valid request: fail-closed."""


@dataclass
class CycleBudget:
    """Running per-cycle spend, checked before every call."""
    caps: BudgetCaps
    calls: int = 0
    total_tokens: int = 0

    def admit(self, req: Tier3Request) -> Optional[str]:
        if req.est_input_tokens > self.caps.max_input_tokens_per_call:
            return (f"input estimate {req.est_input_tokens} exceeds the "
                    f"per-call cap {self.caps.max_input_tokens_per_call}")
        if req.est_output_tokens > self.caps.max_output_tokens_per_call:
            return (f"output estimate {req.est_output_tokens} exceeds the "
                    f"per-call cap {self.caps.max_output_tokens_per_call}")
        if self.calls + 1 > self.caps.max_calls_per_cycle:
            return f"per-cycle call cap {self.caps.max_calls_per_cycle} reached"
        if self.total_tokens + req.est_input_tokens + req.est_output_tokens \
                > self.caps.max_total_tokens_per_cycle:
            return (f"per-cycle token cap "
                    f"{self.caps.max_total_tokens_per_cycle} would be exceeded")
        return None

    def spend(self, req: Tier3Request,
              usage: Optional[Dict[str, int]] = None) -> None:
        self.calls += 1
        if usage:
            self.total_tokens += usage.get("input_tokens", 0) \
                + usage.get("output_tokens", 0)
        else:
            self.total_tokens += req.est_input_tokens + req.est_output_tokens


class Tier3Gateway:
    """The only door to Tier 3. Validates, audits, and (in this
    build) refuses at the backend step — fail-closed, always."""

    def __init__(self, caps: Optional[BudgetCaps] = None,
                 audit_sink: Optional[Path] = None,
                 backend: Optional[Any] = None):
        self.caps = caps or BudgetCaps()
        self.budget = CycleBudget(self.caps)
        self.audit_sink = Path(audit_sink) if audit_sink else None
        self.backend = backend   # None in this build: no keys, no calls

    # ------------------------------------------------------------ audit
    def _audit(self, record: Dict[str, Any]) -> None:
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **record}
        if self.audit_sink:
            self.audit_sink.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_sink, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------ contract
    def validate(self, req: Tier3Request) -> Optional[str]:
        """None if the request is contract-legal, else the refusal
        reason. Pure: no audit, no budget mutation."""
        if req.kind in NEVER_DELEGATE:
            return (f"'{req.kind}' is on the never-delegate list: gate "
                    f"verdicts, adoptions, checker-decidable questions, "
                    f"weight edits, sealed contents, and external "
                    f"actions are never Tier 3's to make")
        if req.kind not in ALLOWED_KINDS:
            return (f"kind '{req.kind}' is not in the contract "
                    f"allowlist {sorted(ALLOWED_KINDS)}")
        if not req.rationale:
            return ("no rationale: a Tier-3 request must state why a "
                    "checker cannot decide the question (arch. "
                    "section 4 — checkers dispose)")
        return self.budget.admit(req)

    def propose(self, req: Tier3Request) -> Tier3Response:
        """The full door: validate -> audit the attempt -> backend.
        In this build the backend step always raises
        Tier3NotConfigured (stub: no keys, no spend, no live calls)."""
        reason = self.validate(req)
        if reason is not None:
            self._audit({"event": "tier3_refused", "kind": req.kind,
                         "subject": req.subject_id, "reason": reason,
                         "request": req.to_dict()})
            raise Tier3Refused(reason)
        self._audit({"event": "tier3_request", "kind": req.kind,
                     "subject": req.subject_id,
                     "est_tokens": req.est_input_tokens
                     + req.est_output_tokens,
                     "request": req.to_dict()})
        if self.backend is None:
            self._audit({"event": "tier3_not_configured",
                         "kind": req.kind, "subject": req.subject_id,
                         "reason": "stub build: no Tier-3 backend "
                                   "configured (no API keys, no spend)"})
            raise Tier3NotConfigured(
                "no Tier-3 backend is configured in this build "
                "(stub): the request was contract-valid and has been "
                "logged, and the loop must proceed without it — "
                "checkers dispose")
        # A future backend implements this call behind the same
        # contract; its response is logged verbatim before returning.
        resp = self.backend(req)
        self.budget.spend(req, resp.usage)
        resp.logged_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._audit({"event": "tier3_response", "kind": req.kind,
                     "subject": req.subject_id,
                     "response": resp.to_dict()})
        return resp
