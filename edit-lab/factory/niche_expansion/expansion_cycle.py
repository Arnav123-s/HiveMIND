"""The niche-expansion runner (Muse's side, Hive growth department).

    python3 -m factory.niche_expansion.expansion_cycle \
        --subject sec-code-model --cycle-id niche-expansion-001

Implements PLAN.md section 3 steps 1-6 ONLY (plus the step-7
save_model artifact on a passed gate). The section 4 adoption edits
(registry / executors / battery evidence) are the coordinator's
serialized sitting and are NEVER done here.

Flow: preflight (growth lock + in-flight factory processes, threads
pinned to 2, system python3 from the lab root) -> snapshot
registry.json + battery_evidence.json bytes -> battery BEFORE via
battery_sections (pre-adoption the job is unregistered, so the
expected result is the serving path's no-specialist gap) -> generate
train / held-A / held-B (oracle-verified at generation) ->
contamination filter across partitions + all five existing battery
item sets -> candidate selection on a DEV split of train only
(hidden 0/4/8 via executors.retrain_candidates, smallest-first) ->
finalists trained on full train, ranked on held-A -> held-B spent
ONCE on the single best finalist -> BIRTH GATE (held-A >= 0.90 AND
held-B >= 0.90 AND per-class recall >= 0.80 on both AND both scores
strictly above the majority-class and keyword/first-token rule
baselines measured on the same slices -- or the coordinator's
2026-11-13 tie-at-perfection clause: model and rule both exactly
1.0000 on both slices with recall 1.0, recorded in the gate record
when it fires) -> determinism assert on the
held generator -> on PASS, swarm.factory.save_model writes
coding/swarm/models/<job>.json (BORN-STAGED); on FAIL nothing shared
is written and the record stands as the rejection.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Dict, List  # noqa: E402

LAB_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import factory as F  # noqa: E402

from factory import executors  # noqa: E402

from . import battery_sections as BS  # noqa: E402
from .subjects import SUBJECTS  # noqa: E402

RECORDS = Path(__file__).parent / "records"
MODELS_DIR = executors.MODELS_DIR
GATE_ACC = 0.90
GATE_RECALL = 0.80


# ------------------------------------------------------------ baselines
def majority_baseline(items, classes):
    counts = Counter(it["label"] for it in items)
    top, n_top = counts.most_common(1)[0]
    return {"acc": round(n_top / len(items), 4) if items else 0.0,
            "predicts": top}


def rule_predict(subject_id: str, text: str) -> str:
    """The dumb keyword/first-token rule baseline (runner-written)."""
    if subject_id == "sql-statement-model":
        m = re.match(r"\s*([A-Za-z]+)", text)
        verb = m.group(1).lower() if m else ""
        return verb if verb in SUBJECTS[subject_id]["classes"] else "select"
    if subject_id == "data-format-model":
        s = text.strip()
        if s.startswith("{") or s.startswith("["):
            return "json"
        lines = [ln for ln in s.splitlines() if ln.strip()]
        if len(lines) >= 3 and all(ln.count(",") >= 1 for ln in lines) \
                and len({ln.count(",") for ln in lines}) == 1:
            return "csv"
        if "=" in s:
            return "toml"
        return "plain-text"
    # sec-code-model: surface keyword rules, in firing order
    if "verify=False" in text:
        return "tls-verify-off"
    if "unsafe_load" in text or "yaml.load" in text:
        return "unsafe-yaml-load"
    if "random." in text and re.search(
            r"(?i)(token|password|passwd|secret|otp|session|reset|api_?key)",
            text):
        return "insecure-random"
    if "requests." in text or "urlopen" in text:
        return "ssrf"
    if "open(" in text or "send_file" in text:
        return "path-traversal"
    return "clean"


def rule_baseline(subject_id, items):
    right = sum(1 for it in items
                if rule_predict(subject_id, it["text"]) == it["label"])
    return {"acc": round(right / len(items), 4) if items else 0.0,
            "rule": "keyword/first-token (expansion_cycle.rule_predict)"}


def evaluate(model, items, classes):
    """Accuracy + per-class recall for a TinyNet on labelled items."""
    per: Dict[str, Dict[str, int]] = {c: {"right": 0, "n": 0}
                                      for c in classes}
    right = 0
    for it in items:
        got = model.run({"text": it["text"]})["output"]
        per[it["label"]]["n"] += 1
        if got == it["label"]:
            right += 1
            per[it["label"]]["right"] += 1
    recall = {c: (round(v["right"] / v["n"], 4) if v["n"] else 0.0)
              for c, v in per.items()}
    return {"acc": round(right / len(items), 4) if items else 0.0,
            "right": right, "n": len(items), "per_class_recall": recall,
            "min_recall": min(recall.values()) if recall else 0.0}


# ------------------------------------------------------------ preflight
def preflight() -> List[str]:
    problems = []
    lock = LAB_ROOT / "growth" / ".growth.lock"
    if lock.exists():
        problems.append(f"growth lock present: {lock}")
    try:
        ps = subprocess.run(["ps", "-eo", "pid=,command="],
                            capture_output=True, text=True, timeout=30)
        # exclude this process and its whole ancestry (the shell /
        # timeout wrappers that launched us carry our own command
        # line and are not "another process in flight")
        mine = {os.getpid()}
        pid = os.getpid()
        while pid > 1:
            try:
                stat = Path(f"/proc/{pid}/stat").read_text()
                pid = int(stat.rsplit(") ", 1)[1].split()[1])
            except Exception:  # noqa: BLE001
                break
            mine.add(pid)
        for line in ps.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) < 2 or int(parts[0]) in mine:
                continue
            cmd = parts[1]
            if re.search(r"factory\.(growth_cycle|growth|dream|run_|"
                         r"niche_expansion\.expansion_cycle)", cmd):
                problems.append(f"factory/growth process in flight: {cmd}")
    except Exception as e:  # noqa: BLE001
        problems.append(f"preflight process scan failed: {e}")
    return problems


# ------------------------------------------------------------ the cycle
def run_cycle(subject_id: str, cycle_id: str) -> Dict[str, Any]:
    cfg = SUBJECTS[subject_id]
    record: Dict[str, Any] = {
        "cycle_id": cycle_id, "subject": subject_id,
        "runner": (f"python3 -m factory.niche_expansion.expansion_cycle "
                   f"--subject {subject_id} --cycle-id {cycle_id}"),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "niche": cfg["niche"], "fmode": cfg["fmode"],
        "epochs": cfg["epochs"], "classes": cfg["classes"],
    }

    problems = preflight()
    if problems:
        record["verdict"] = "BLOCKED"
        record["preflight_problems"] = problems
        _write_record(record)
        return record

    # -- snapshot shared files (bytes) for the coordinator's sitting
    snap_dir = RECORDS / cycle_id / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snaps = {}
    for rel in ("factory/registry.json", "factory/battery_evidence.json"):
        data = (LAB_ROOT / rel).read_bytes()
        (snap_dir / Path(rel).name).write_bytes(data)
        snaps[rel] = hashlib.sha256(data).hexdigest()
    record["snapshots"] = snaps

    # -- battery BEFORE (expected: no-specialist gap, pre-adoption)
    try:
        sections = BS.run_sections()
        sec_name = [k for k, v in BS.SECTIONS.items()
                    if v["job"] == subject_id][0]
        record["battery_before"] = {sec_name: sections[sec_name]}
    except Exception as e:  # noqa: BLE001
        record["battery_before"] = {"error": f"{type(e).__name__}: {e}"}

    # -- generate partitions (oracle-verified inside the generators)
    gen = cfg["gen"]
    train_raw, train_stats = gen.gen_train()
    held_a_raw, held_a_stats = gen.gen_held_a()
    held_b_raw, held_b_stats = gen.gen_held_b()
    record["generation"] = {"train": train_stats, "held_a": held_a_stats,
                            "held_b": held_b_stats}

    # -- determinism assert (plan 5.4), before anything is saved
    assert cfg["held_fn"]() == cfg["held_fn"](), \
        "held-A generator is not deterministic"
    assert cfg["train_fn"]() == cfg["train_fn"](), \
        "train generator is not deterministic"
    record["determinism_assert"] = "held_fn(seed) twice identical; " \
                                   "train_fn(seed) twice identical"

    # -- contamination filter across partitions + battery item sets
    import hive_battery as HB
    battery_refs = []
    for items in (HB.SECRET_ITEMS, HB.ERROR_ITEMS, HB.COMMIT_ITEMS,
                  HB.CONTRACT_ITEMS, HB.GAP_ITEMS):
        battery_refs += [{"text": t, "label": l} for t, l in items]
    battery_refs += [{"text": t, "label": l}
                     for t, l in cfg["battery_items"]]
    fmode = cfg["fmode"]
    train, drop_t = executors.contamination_filter(
        train_raw, held_a_raw + held_b_raw + battery_refs, fmode)
    held_a, drop_a = executors.contamination_filter(
        held_a_raw, train + held_b_raw + battery_refs, fmode)
    held_b, drop_b = executors.contamination_filter(
        held_b_raw, train + held_a + battery_refs, fmode)
    record["contamination"] = {
        "train": {"in": len(train_raw), "kept": len(train),
                  "dropped": len(drop_t)},
        "held_a": {"in": len(held_a_raw), "kept": len(held_a),
                   "dropped": len(drop_a)},
        "held_b": {"in": len(held_b_raw), "kept": len(held_b),
                   "dropped": len(drop_b)},
        "battery_reference_items": len(battery_refs),
        "dropped_reasons": Counter(
            d["drop_reason"].split(" >=")[0].split(" jaccard")[0]
            for d in drop_t + drop_a + drop_b),
    }

    exec_cfg = {"niche": cfg["niche"], "job": cfg["job"],
                "classes": cfg["classes"], "fmode": fmode,
                "epochs": cfg["epochs"]}

    # -- dev split of TRAIN only; recipe selection smallest-first
    by_label: Dict[str, List[Dict[str, Any]]] = {}
    for it in train:
        by_label.setdefault(it["label"], []).append(it)
    rng = random.Random(7)
    subtrain, dev = [], []
    for label, items in sorted(by_label.items()):
        shuffled = list(items)
        rng.shuffle(shuffled)
        cut = max(2, len(shuffled) // 5)
        dev += shuffled[:cut]
        subtrain += shuffled[cut:]
    _dev_cands, dev_attempts = executors.retrain_candidates(
        exec_cfg, subject_id, subtrain, dev)
    best_dev = max(a["heldout_acc"] for a in dev_attempts)
    chosen = min((a for a in dev_attempts
                  if a["heldout_acc"] >= best_dev - 0.02),
                 key=lambda a: (a["params"], a["hidden"]))
    record["dev_selection"] = {
        "dev_n": len(dev), "subtrain_n": len(subtrain),
        "attempts": dev_attempts,
        "winner_by_dev_smallest_within_0.02": chosen,
        "note": "hidden/recipe choice made on a dev split of train "
                "only; held slices never used for this choice",
    }

    # -- finalists on full train, ranked on held-A
    cands, fin_attempts = executors.retrain_candidates(
        exec_cfg, subject_id, train, held_a)
    ranked = sorted(
        ({"hidden": m.hidden, "params": m.param_count(),
          "held_a_acc": round(acc, 4), "model": m}
         for m, acc in cands),
        key=lambda r: (-r["held_a_acc"], r["params"], r["hidden"]))
    record["finalists_ranked_on_held_a"] = [
        {k: v for k, v in r.items() if k != "model"} for r in ranked]
    best = ranked[0]
    model = best["model"]

    ev_a = evaluate(model, held_a, cfg["classes"])
    # held-B is spent ONCE, here, on the single best finalist
    ev_b = evaluate(model, held_b, cfg["classes"])
    base_a = {"majority": majority_baseline(held_a, cfg["classes"]),
              "rule": rule_baseline(subject_id, held_a)}
    base_b = {"majority": majority_baseline(held_b, cfg["classes"]),
              "rule": rule_baseline(subject_id, held_b)}
    record["gate"] = {
        "held_a": ev_a, "held_b": ev_b,
        "baselines_held_a": base_a, "baselines_held_b": base_b,
        "thresholds": {"acc": GATE_ACC, "per_class_recall": GATE_RECALL,
                       "strictly_above_baselines": True},
    }
    strict_above = (
        ev_a["acc"] > base_a["majority"]["acc"]
        and ev_a["acc"] > base_a["rule"]["acc"]
        and ev_b["acc"] > base_b["majority"]["acc"]
        and ev_b["acc"] > base_b["rule"]["acc"])
    # COORDINATOR RULING, 2026-11-13 (tie-at-perfection): for a subject
    # whose class is DEFINED by the same surface signal the rule
    # baseline reads (sql-statement-model: the leading verb IS the
    # class, and field2's own classifier reads it), "strictly above
    # the rule" is unsatisfiable at perfection and the leg's intent --
    # never adopt a model that adds nothing over a dumb rule -- is met
    # in the only way it can be: the model ties the rule at exactly
    # 1.0000 on BOTH pristine held slices with per-class recall 1.0.
    # The clause fires ONLY at exact perfection on both slices; every
    # non-degenerate case still requires strict superiority. When it
    # fires it is recorded in the gate record, never silent. Ruled by
    # the department coordinator; flagged to Arnav in the wave report
    # (reversible by the standard rollback).
    tie_at_perfection = (
        ev_a["acc"] == 1.0 and ev_b["acc"] == 1.0
        and base_a["rule"]["acc"] == 1.0 and base_b["rule"]["acc"] == 1.0
        and ev_a["min_recall"] == 1.0 and ev_b["min_recall"] == 1.0)
    if tie_at_perfection and not strict_above:
        record["gate"]["amendment"] = {
            "name": "tie-at-perfection",
            "ruled": "2026-11-13, department coordinator",
            "reason": "rule baseline defines the class signal; strict "
                      "superiority is unsatisfiable at 1.0000 on both "
                      "pristine held slices with recall 1.0",
        }
    passed = (
        ev_a["acc"] >= GATE_ACC and ev_b["acc"] >= GATE_ACC
        and ev_a["min_recall"] >= GATE_RECALL
        and ev_b["min_recall"] >= GATE_RECALL
        and (strict_above or tie_at_perfection))
    record["methods_provenance"] = (
        f"dev-split recipe selection on train only (dev n={len(dev)}): "
        f"hidden {chosen['hidden']} chosen smallest-first within 0.02 "
        f"of best dev acc {best_dev}; finalists (hidden 0/4/8) trained "
        f"on full train (n={len(train)}) via "
        f"executors.retrain_candidates and ranked on held-A; held-B "
        f"spent once on the winner (hidden {best['hidden']}, "
        f"{best['params']} params). Data: three disjoint template "
        f"partitions, oracle-verified at generation (drops in the "
        f"generation stats), contamination-filtered against the other "
        f"partitions and all five existing battery item sets plus "
        f"this subject's hand-authored battery items.")

    if not passed:
        record["verdict"] = "REJECTED"
        record["model_file"] = None
        _write_record(record)
        return record

    # -- BORN-STAGED: save_model artifact only; adoption is the
    #    coordinator's serialized sitting (plan section 4).
    model.name = subject_id
    extra = {"adopted": True, "path": "niche-expansion",
             "heldout_acc": ev_a["acc"], "held_b_acc": ev_b["acc"],
             "train_n": len(train), "heldout_n": len(held_a),
             "held_b_n": len(held_b), "cycle_id": cycle_id,
             "expansion_gate": record["gate"]["thresholds"]}
    F.save_model(model, extra, directory=MODELS_DIR)
    mpath = MODELS_DIR / f"{subject_id}.json"
    record["verdict"] = "BORN-STAGED"
    record["model_file"] = {
        "path": f"coding/swarm/models/{subject_id}.json",
        "sha256": hashlib.sha256(mpath.read_bytes()).hexdigest(),
        "params": model.param_count(), "hidden": model.hidden,
        "heldout_acc_recorded": ev_a["acc"],
        "note": "staged artifact only — registry adoption is the "
                "coordinator's section-4 sitting, not done here",
    }
    _write_record(record)
    return record


def _write_record(record: Dict[str, Any]) -> None:
    RECORDS.mkdir(parents=True, exist_ok=True)
    cid = record["cycle_id"]
    (RECORDS / f"{cid}.json").write_text(json.dumps(record, indent=1))
    gate = record.get("gate", {})
    lines = [
        f"# Niche expansion {cid} — {record['subject']}",
        "",
        f"Runner: `{record['runner']}`. Steps 1-6 of PLAN.md section 3 "
        f"only; adoption (section 4) is the coordinator's sitting.",
        "",
        f"Verdict: **{record['verdict']}**",
        "",
    ]
    if gate:
        lines += [
            "## Gate",
            "",
            "| slice | model | majority | rule | min per-class recall |",
            "|---|---|---|---|---|",
            f"| held-A | {gate['held_a']['acc']} (n={gate['held_a']['n']}) "
            f"| {gate['baselines_held_a']['majority']['acc']} "
            f"| {gate['baselines_held_a']['rule']['acc']} "
            f"| {gate['held_a']['min_recall']} |",
            f"| held-B | {gate['held_b']['acc']} (n={gate['held_b']['n']}) "
            f"| {gate['baselines_held_b']['majority']['acc']} "
            f"| {gate['baselines_held_b']['rule']['acc']} "
            f"| {gate['held_b']['min_recall']} |",
            "",
            f"Per-class recall held-A: {gate['held_a']['per_class_recall']}",
            f"Per-class recall held-B: {gate['held_b']['per_class_recall']}",
            "",
        ]
    if record.get("generation"):
        lines += ["## Generation (oracle-verified at generation)", ""]
        for part, stats in record["generation"].items():
            lines.append(f"- {part}: {stats['items']} kept, "
                         f"drops {stats['drops']}")
        lines.append("")
    if record.get("contamination"):
        c = record["contamination"]
        lines += ["## Contamination filter", "",
                  f"- train {c['train']['kept']}/{c['train']['in']} kept; "
                  f"held-A {c['held_a']['kept']}/{c['held_a']['in']}; "
                  f"held-B {c['held_b']['kept']}/{c['held_b']['in']}",
                  ""]
    if record.get("battery_before"):
        lines += ["## Battery BEFORE (through ServingHive)", "",
                  f"```\n{json.dumps(record['battery_before'], indent=1)}\n```",
                  "",
                  "Pre-adoption the job is unregistered; the "
                  "no-specialist result above is the expected BEFORE "
                  "state, not a failure.", ""]
    if record.get("methods_provenance"):
        lines += ["## Methods provenance", "",
                  record["methods_provenance"], ""]
    if record.get("model_file"):
        lines += ["## Staged model", "",
                  f"- {record['model_file']['path']} "
                  f"sha256 {record['model_file']['sha256']}", ""]
    (RECORDS / f"{cid}.md").write_text("\n".join(lines))
    with open(RECORDS / "ledger.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "cycle_id": cid, "subject": record["subject"],
            "verdict": record["verdict"], "ts": record["ts"],
            "held_a": gate.get("held_a", {}).get("acc"),
            "held_b": gate.get("held_b", {}).get("acc"),
            "model_sha256": (record.get("model_file") or {}).get("sha256"),
        }) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True, choices=sorted(SUBJECTS))
    ap.add_argument("--cycle-id", required=True)
    args = ap.parse_args()
    rec = run_cycle(args.subject, args.cycle_id)
    print(json.dumps({"cycle_id": rec["cycle_id"],
                      "subject": rec["subject"],
                      "verdict": rec["verdict"],
                      "gate": rec.get("gate"),
                      "model_file": rec.get("model_file")}, indent=1))
    return 0 if rec["verdict"] in ("BORN-STAGED", "REJECTED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
