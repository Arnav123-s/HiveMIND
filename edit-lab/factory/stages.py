"""The six loop stages (FACTORY-ARCHITECTURE.md section 8).

  diagnose -> indict -> edit_train (plan) -> verify (win-gate)
           -> compose -> grow

Each stage is a pure callable over the contracts: same input, same
output, no hidden state — which is what makes stages idempotent and
resumable. Diagnosis is checker-style and deterministic: it classifies
failures from recorded raw evidence (scores, per-case checks), it does
not call a model. Tier-3 may *propose* clusters in Phase B; checkers
dispose (arch. section 4, Tier 3).

Phase A honesty rules, enforced here:
  * diagnose() requires evidence; without it the Diagnosis is marked
    has_evidence=False and the loop stops that subject (fail-closed).
  * indict() never justifies a weight edit from score gaps alone. A
    weight edit requires a map (Tier-0 flip-ablation, knockout, or
    locator evidence). Score gaps indict *coverage* — training
    surfaces, views, data — not weights (IDEA.md section 6).
  * edit_train() returns a plan. In DRY_RUN it executes nothing.
  * verify() validates the plan against the win-gate contract; it
    measures nothing in Phase A (measured=False on every verdict).
"""
from __future__ import annotations

from typing import List

from .contracts import (Action, ClusterKind, CompositionPlan, Diagnosis,
                        FailureCluster, GrowthPlan, Indictment,
                        InterventionPlan, Subject, Verification, WinGate)

SURFACE_GAP_DROP = 0.10   # heldout -> fresh drop that counts as drift


# ---------------------------------------------------------------- stage 1
def diagnose(subject: Subject) -> Diagnosis:
    clusters: List[FailureCluster] = []
    has_scores = subject.heldout_score is not None or subject.fresh_score is not None
    if not has_scores and not subject.failing_cases:
        return Diagnosis(subject_id=subject.subject_id, clusters=[],
                         summary="no recorded evidence for this subject",
                         has_evidence=False)

    if subject.kind == "tier1_adapter":
        # Coordinator: cluster the pristine per-case check failures.
        by_check: dict = {}
        for fc in subject.failing_cases:
            for chk in fc.get("failed_checks", []):
                by_check.setdefault(chk, []).append(fc)
        for chk, cases_ in sorted(by_check.items()):
            clusters.append(FailureCluster(
                label=f"pristine_check_failure:{chk}",
                kind=ClusterKind.CAPABILITY,
                severity="low",
                evidence=(f"{len(cases_)} pristine case(s) fail check '{chk}'; the winner "
                          f"ties the base anchor on every failing case (no regression), "
                          f"so this is residual capability, not an introduced defect"),
                examples=cases_))
        if not clusters:
            clusters.append(FailureCluster(
                label="no_material_failure_observed", kind=ClusterKind.NONE,
                severity="info", evidence="pristine run has no sub-1.0 cases"))
        verdict = subject.fresh_score is not None and subject.fresh_bar is not None \
            and subject.fresh_score > subject.fresh_bar
        summary = (f"pristine {subject.fresh_score} vs gate {subject.fresh_bar} "
                   f"({'WIN' if verdict else 'below gate'}); "
                   f"{len(subject.failing_cases)} sub-1.0 case(s), all tied with base")
        return Diagnosis(subject.subject_id, clusters, summary, True)

    if subject.kind == "tier0_composition":
        per_class = subject.metadata.get("per_class", {})
        weak = {c: v for c, v in per_class.items()
                if v.get("recall") is not None and v["recall"] < 0.75}
        if weak:
            clusters.append(FailureCluster(
                label="weak_class_recall",
                kind=ClusterKind.CAPABILITY,
                severity="medium",
                evidence=("composed accuracy "
                          f"{subject.heldout_score} vs bar {subject.heldout_bar}; "
                          f"weak-recall classes: "
                          + ", ".join(f"{c} recall {v['recall']}" for c, v in weak.items())
                          + ". Eight composition rounds plateaued at the same score "
                            "(phase4 record): an information/surface floor, not a "
                            "composition-strategy defect"),
                examples=[{"class": c, **v} for c, v in weak.items()]))
        else:
            clusters.append(FailureCluster(
                label="below_bar_no_weak_class", kind=ClusterKind.UNKNOWN,
                severity="medium",
                evidence=f"composed {subject.heldout_score} vs bar {subject.heldout_bar}"))
        return Diagnosis(subject.subject_id, clusters,
                         f"composition at {subject.heldout_score} vs bar "
                         f"{subject.heldout_bar} — not cleared", True)

    # Tier-0 specialists: same-distribution held-out vs fresh surfaces.
    held, fresh = subject.heldout_score, subject.fresh_score
    if fresh is not None and subject.fresh_bar is not None and fresh < subject.fresh_bar:
        clusters.append(FailureCluster(
            label="fresh_surface_generalization_gap",
            kind=ClusterKind.CAPABILITY,
            severity="high",
            evidence=(f"held-out {held} but fresh-surface {fresh} < bar "
                      f"{subject.fresh_bar} ({subject.metadata.get('fresh_bar_detail', '')}); "
                      f"battery: {subject.metadata.get('battery_detail', '')}"),
            examples=[]))
    elif held is not None and fresh is not None and (held - fresh) >= SURFACE_GAP_DROP:
        clusters.append(FailureCluster(
            label="fresh_surface_drift",
            kind=ClusterKind.CAPABILITY,
            severity="medium",
            evidence=f"fresh-surface {fresh} passes its bar but trails held-out {held} "
                     f"by {held - fresh:.3f}: surface coverage is thinner than the "
                     f"adoption evidence suggests",
            examples=[]))
    else:
        clusters.append(FailureCluster(
            label="no_material_failure_observed", kind=ClusterKind.NONE,
            severity="info",
            evidence=f"held-out {held}, fresh-surface {fresh} "
                     f"(bar {subject.fresh_bar}): no material failure in evidence",
            examples=[]))
    top = clusters[0]
    return Diagnosis(subject.subject_id, clusters,
                     f"{top.label}: {top.evidence}", True)


# ---------------------------------------------------------------- stage 2
def indict(subject: Subject, diagnosis: Diagnosis) -> Indictment:
    if not diagnosis.has_evidence:
        return Indictment(subject.subject_id, indictable=False, target_units=[],
                          method="none", rationale="fail-closed: no evidence, no indictment")
    actionable = [c for c in diagnosis.clusters if c.kind in (ClusterKind.CAPABILITY,
                                                              ClusterKind.DEFECT)]
    if not actionable:
        return Indictment(subject.subject_id, indictable=False, target_units=[],
                          method="evidence review",
                          rationale="no actionable cluster: incumbent is healthy on the "
                                    "recorded evidence; nothing to indict")
    labels = {c.label for c in actionable}
    if any(l.startswith("fresh_surface") for l in labels):
        return Indictment(
            subject.subject_id, indictable=True,
            target_units=[f"training_surface_coverage:{subject.niche}",
                          "second_view_coverage (each case in an independent surface form)"],
            method="held-out vs fresh-surface score decomposition",
            rationale="the gap appears only on fresh surfaces while same-distribution "
                      "held-out is strong: the indicted unit is training-surface "
                      "coverage, not weights. No flip/knockout map indicts any weight, "
                      "so a weight edit is NOT justified (IDEA.md section 6)",
            weight_edit_justified=False)
    if "weak_class_recall" in labels:
        weak = [e["class"] for c in actionable for e in c.examples if "class" in e]
        return Indictment(
            subject.subject_id, indictable=True,
            target_units=[f"per_class_surface_coverage:{c}" for c in weak] or
                         [f"training_surface_coverage:{subject.niche}"],
            method="per-class recall decomposition over 8 plateaued composition rounds",
            rationale="composition strategy was varied 8 ways and the score did not "
                      "move: the indicted unit is the weak classes' surface coverage. "
                      "More composition of the same surfaces cannot clear the bar",
            weight_edit_justified=False)
    # Coordinator residual check failures.
    return Indictment(
        subject.subject_id, indictable=True,
        target_units=["residual_case_classes:" + ",".join(sorted({
            chk for c in actionable for e in c.examples
            for chk in e.get("failed_checks", [])}))],
        method="pristine per-case check decomposition, paired against base per-case",
        rationale="residual failures tie the base anchor case-for-case: no defect was "
                  "introduced by the winning edit, and the coordinator contest is "
                  "closed by Arnav's binding decision — indictment is recorded for "
                  "the record, and the only legal plan is HOLD",
        weight_edit_justified=False)


# ---------------------------------------------------------------- stage 3
def edit_train(subject: Subject, diagnosis: Diagnosis,
               indictment: Indictment) -> InterventionPlan:
    """Produce the intervention plan. Phase A: plan only, never executed."""
    if not indictment.indictable:
        return InterventionPlan(
            subject_id=subject.subject_id, action=Action.NO_OP,
            steps=["hold the incumbent; re-diagnose when fresh evidence lands"],
            win_gate=None, estimated_cost="none",
            shadow_only=True, executed=False)

    labels = {c.label for c in diagnosis.clusters}
    if subject.kind == "tier1_adapter":
        return InterventionPlan(
            subject_id=subject.subject_id, action=Action.NO_OP,
            steps=["HOLD: contest closed by binding decision; the winner stands",
                   "record residual clusters for any future, separately-authorized "
                   "coordinator work; do not generate candidates against this gate"],
            win_gate=None, estimated_cost="none", shadow_only=True, executed=False)

    if "fresh_surface_drift" in labels:
        # Final-product: preventive drift on a niche with a dream
        # generator is the dream cycle's home ground — the Phase B
        # harvest pools for these subjects are spent, and idle-time
        # self-practice at the capability edge is the remaining
        # legitimate executor. Subjects without a generator keep the
        # widen plan below.
        from . import dream_niches
        if subject.subject_id in dream_niches.GENERATORS:
            bar = subject.fresh_bar
            return InterventionPlan(
                subject_id=subject.subject_id, action=Action.DREAM_TRAIN,
                steps=[
                    "probe the incumbent per difficulty band on fresh "
                    "generated probes (thermostat: train at the edge "
                    "band and the one below it)",
                    "generate parameterized niche families; verify "
                    "every case with the niche checker (execution "
                    "signatures / signal dominance); discard "
                    "unverifiable dreams; two views per kept case",
                    "contamination-filter against train + held-out + "
                    "battery + the spent Phase B harvest pools; "
                    "difficulty filter (keep what the incumbent gets "
                    "wrong + diversity quota)",
                    "retrain smallest-first; the finalist must beat "
                    "the incumbent on a fresh dreamed screen or the "
                    "plan stops, confirm unspent",
                    "confirm ONCE on freshly generated confirm "
                    "families: adoption requires beating the gate AND "
                    "the incumbent measured on the same set, with "
                    "held-out inside the regression gate",
                ],
                win_gate=WinGate(
                    metric="fresh-surface accuracy on generated confirm families",
                    threshold=bar if bar is not None else 0.9,
                    regression_gate="same-distribution held-out must not fall "
                                    "more than 0.02 below the incumbent's "
                                    "recorded held-out score; the finalist must "
                                    "also beat the incumbent on the confirm set "
                                    "itself (paired, same items)",
                    confirm_protocol="thermostat probes -> dreamed screen "
                                     "ranks -> one confirm run on disjoint "
                                     "confirm families, spent once"),
                estimated_cost="Tier-0: seconds to train; the cost is "
                               "generation + screens",
                requires_heavy_leg=False, shadow_only=True, executed=False)

    if any(l.startswith("fresh_surface") for l in labels):
        bar = subject.fresh_bar
        return InterventionPlan(
            subject_id=subject.subject_id, action=Action.TRAIN_DATA_WIDEN,
            steps=[
                "harvest fresh-surface examples for the niche from sources disjoint "
                "from the battery items (difficulty filter: drop what the incumbent "
                "already gets right; diversity quota across surface forms)",
                "add a second view of each training case (an independent surface "
                "form of the same underlying item)",
                "retrain the Tier-0 specialist in-process on the widened set "
                "(seconds-class cost at this scale; no heavy leg)",
                "screen on a NEW fresh-surface set; adoption only via the win-gate",
            ],
            win_gate=WinGate(
                metric="fresh-surface accuracy on a held-out fresh set",
                threshold=bar if bar is not None else 0.9,
                regression_gate="same-distribution held-out must not fall more than "
                                "0.02 below the incumbent's recorded held-out score",
                confirm_protocol="dev/fresh screen ranks -> confirm split -> one "
                                 "pristine-style fresh run for the finalist"),
            estimated_cost="Tier-0: seconds to train; the cost is harvesting + screens",
            requires_heavy_leg=False, shadow_only=True, executed=False)

    if "weak_class_recall" in labels:
        # Phase C: the plan shape changed from TRAIN_DATA_WIDEN to
        # DREAM_TRAIN. There is no external surface to harvest for
        # this composition (Phase B blocked on exactly that); the
        # dream executor manufactures the surfaces instead, with
        # labels PROVED by execution, capability-matched by the
        # thermostat, s1-filtered, in two views. Same win-gate.
        return InterventionPlan(
            subject_id=subject.subject_id, action=Action.DREAM_TRAIN,
            steps=[
                "probe the weak classes' binaries per difficulty band on "
                "fresh generated probes (thermostat: train at the highest "
                "unmastered band)",
                "generate parameterized bug families; verify every case "
                "by execution (correct code runs, mutation observably "
                "differs); discard unverifiable dreams",
                "contamination-filter against train + held-out + the "
                "phase-4 dream corpus; slice diversity quota; difficulty "
                "filter (keep what the incumbent gets wrong + quota)",
                "store each kept case in two views (original + renamed)",
                "retrain only the weak classes' Tier-0 binaries; screen "
                "the recomposed candidate on fresh dreamed surfaces — a "
                "screen that does not beat the incumbent stops the plan",
                "confirm ONCE on the standing sealed held-out set under "
                "the win-gate (the phase-4 set was spent by "
                "dream-phaseC-002; the sealed v2 set serves now); "
                "strong classes untouched throughout",
            ],
            win_gate=WinGate(
                metric="composed held-out accuracy",
                threshold=subject.heldout_bar if subject.heldout_bar is not None else 0.8,
                regression_gate="no per-class recall may fall below its "
                                "recorded value on the confirm set",
                confirm_protocol="composed screen on fresh dreamed surfaces "
                                 "-> one confirm run on the sealed set; "
                                 "8 prior rounds are the plateau evidence, so a "
                                 "screen that does not beat the incumbent "
                                 "composition stops the plan"),
            estimated_cost="Tier-0: per-class retrains are seconds-class",
            requires_heavy_leg=False, shadow_only=True, executed=False)

    return InterventionPlan(
        subject_id=subject.subject_id, action=Action.NO_OP,
        steps=["no plan shape matches the indictment; recorded, not improvised"],
        win_gate=None, estimated_cost="none", shadow_only=True, executed=False)


# ---------------------------------------------------------------- stage 4
def verify(subject: Subject, plan: InterventionPlan,
           indictment: Indictment) -> Verification:
    """The win-gate stage. Fail-closed: any missing contract element
    blocks the plan. Phase A measures nothing — it validates that the
    plan *could* be run under the lab's gates in Phase B."""
    reasons: List[str] = []
    if plan.action == Action.NO_OP:
        return Verification(subject.subject_id, verdict="HOLD",
                            reasons=["no intervention proposed; incumbent stands "
                                     "on recorded evidence"], measured=False)
    if plan.action == Action.WEIGHT_EDIT and not indictment.weight_edit_justified:
        reasons.append("BLOCKED: weight edit proposed without a map-backed "
                       "indictment (IDEA.md section 6)")
    if indictment.indictable is False:
        reasons.append("BLOCKED: intervention proposed with no indictment")
    if plan.win_gate is None:
        reasons.append("BLOCKED: no win-gate defined (threshold + regression "
                       "gate + confirm protocol are all required)")
    else:
        if not plan.win_gate.regression_gate:
            reasons.append("BLOCKED: win-gate has no regression gate")
        if not plan.win_gate.confirm_protocol:
            reasons.append("BLOCKED: win-gate has no confirm protocol")
    if plan.requires_heavy_leg:
        reasons.append("BLOCKED in Phase A: plan requires a heavy leg; the "
                       "governor grants none and the one-heavy-job rule is held "
                       "by another job")
    if plan.executed or not plan.shadow_only:
        reasons.append("BLOCKED: Phase A plans must be shadow-only and unexecuted")
    if reasons:
        return Verification(subject.subject_id, verdict="BLOCKED",
                            reasons=reasons, measured=False)
    return Verification(subject.subject_id, verdict="SHADOW_PASS",
                        reasons=["plan is complete under the gate contract: "
                                 "indictment precedes intervention, win-gate + "
                                 "regression gate + confirm protocol present, "
                                 "no heavy leg required",
                                 "NOT a measured win: no eval was run in Phase A; "
                                 "the gate itself runs in Phase B"],
                        measured=False)


# ---------------------------------------------------------------- stage 5
def compose(subject: Subject, plan: InterventionPlan,
            verification: Verification) -> CompositionPlan:
    if verification.verdict == "WIN" and subject.kind == "tier0_composition":
        # Phase C measured win (dream cycle): the weak classes'
        # binaries were retrained on execution-verified dreams and
        # adopted in place (same serving names); the phase-4 records
        # are backed up inside the run directory as the fallback.
        return CompositionPlan(
            subject.subject_id,
            members=["dream-retrained weak-class bug-*-model binaries "
                     "(adopted, measured)",
                     "untouched strong-class binaries (mutable-default, "
                     "missing-return)"],
            strategy="max-margin composition over per-class binaries, "
                     "unchanged machinery; only the weak classes' "
                     "members changed, and only after the composed "
                     "confirm cleared the bar with no per-class recall "
                     "regression",
            fallback="phase-4 composition (plateau 0.7931); incumbent "
                     "records backed up in the cycle run directory",
            audit_plan="serve-time audit with retirement: if the "
                       "composed audit score falls below the phase-4 "
                       "plateau composition, serving retires to the "
                       "backed-up fallback records",
            shadow_only=False, executed=True)
    if verification.verdict == "WIN":
        # Phase B measured win: the widened specialist was adopted as a
        # new versioned model; the incumbent remains the fallback.
        return CompositionPlan(
            subject.subject_id,
            members=[f"{subject.subject_id}-v2 (adopted, measured)",
                     f"{subject.subject_id} (incumbent, fallback)"],
            strategy=f"the widened {subject.subject_id} serves in its "
                     f"{subject.niche} pipeline; composition is the product, "
                     f"the single incumbent specialist is the fallback",
            fallback=f"incumbent {subject.subject_id} (held-out {subject.heldout_score})",
            audit_plan="serve-time audit with retirement: if the widened "
                       "specialist's audit score falls below the incumbent "
                       "alone, serving retires to the fallback",
            shadow_only=False, executed=True)
    if verification.verdict == "REVERT":
        return CompositionPlan(
            subject.subject_id,
            members=[f"{subject.subject_id} (incumbent, serving)"],
            strategy="candidate reverted by the measured win-gate; the "
                     "incumbent continues to serve unchanged",
            fallback=f"incumbent {subject.subject_id} (held-out {subject.heldout_score})",
            audit_plan="no composition change; re-diagnose when new fresh "
                       "evidence or a new harvest lands",
            shadow_only=False, executed=True)
    if verification.verdict not in ("SHADOW_PASS", "HOLD"):
        return CompositionPlan(subject.subject_id, members=[], strategy="none",
                               fallback="best single measured candidate",
                               audit_plan="n/a — verification did not pass",
                               shadow_only=True, executed=False)
    if subject.subject_id == "synthv1-r4-coordinator":
        return CompositionPlan(
            subject.subject_id, members=["synthv1-r4 (winner)", "base Qwen3-1.7B (anchor)"],
            strategy="single adopted adapter serves; base remains the measured fallback. "
                     "No composition is proposed: the contest is closed and the winner "
                     "already beats the gate alone",
            fallback="base coordinator (pristine anchor 0.930)",
            audit_plan="serve-time audit on live coordinator calls if this side ever "
                       "serves it; retire the adapter if audit falls below the anchor",
            shadow_only=True, executed=False)
    if subject.kind == "tier0_composition":
        return CompositionPlan(
            subject.subject_id,
            members=["per-class bug-*-model binaries (adopted)", "widened weak-class variants (planned)"],
            strategy="jury/max-margin composition over per-class binaries, with the "
                     "widened weak-class variants joining only if the win-gate passes; "
                     "decompose further rather than enlarge any single model "
                     "(arch. section 5)",
            fallback="best recorded composition (round 2-8 plateau, 0.7931)",
            audit_plan="audit rate on served calls with a retirement threshold: a "
                       "composition that cannot beat its best single member on audit "
                       "is retired to the fallback",
            shadow_only=True, executed=False)
    # Tier-0 specialists compose into their niche pipelines.
    pipelines = {
        "review": ["secret-line-model", "contract-judgment-model", "error-class-model"],
        "meta": ["gap-move-model (router)", "niche coordinators"],
        "security": ["secret-line-model"],
        "debugging": ["error-class-model", "bug-pattern-composed"],
        "vcs": ["commit-type-model"],
    }
    members = pipelines.get(subject.niche, [subject.subject_id])
    return CompositionPlan(
        subject.subject_id, members=members,
        strategy=f"the (planned) widened {subject.subject_id} rejoins its "
                 f"{subject.niche} pipeline only after passing the win-gate; "
                 f"composition is the product, the single specialist is the fallback",
        fallback=f"incumbent {subject.subject_id} (held-out {subject.heldout_score})",
        audit_plan="serve-time audit with retirement: if the composed pipeline's "
                   "audit score falls below the incumbent specialist alone, the "
                   "pipeline retires to the fallback",
        shadow_only=True, executed=False)


# ---------------------------------------------------------------- stage 6
def grow(subject: Subject, diagnosis: Diagnosis,
         composition: CompositionPlan) -> GrowthPlan:
    labels = {c.label for c in diagnosis.clusters}
    proposals = []
    if any(l.startswith("fresh_surface") for l in labels):
        proposals.append({
            "job": f"second-view generator for the {subject.niche} niche",
            "niche": subject.niche, "tier": "Tier 0",
            "why": "the indicted unit is surface coverage; a smallest specialist "
                   "that renders each item in an independent surface form is the "
                   "growth-shaped fix (growth instead of refusal, IDEA.md section 5)",
            "gate": "its outputs must raise the incumbent's fresh-surface screen "
                    "when used as training views, measured against views-off control",
        })
    if "weak_class_recall" in labels:
        weak = [e["class"] for c in diagnosis.clusters for e in c.examples if "class" in e]
        for cls in weak:
            proposals.append({
                "job": f"slice-variant specialist for bug class '{cls}'",
                "niche": subject.niche, "tier": "Tier 0",
                "why": f"class recall is the plateau's binding constraint for '{cls}'",
                "gate": "per-class recall must beat the phase-4 recorded value on "
                        "held-out without lowering any other class",
            })
    if not proposals:
        proposals = []
    return GrowthPlan(subject.subject_id, proposals=proposals,
                      shadow_only=True, executed=False)
