"""Check score provenance, stability across rounds, and label-blind predictions."""
import argparse
from collections import Counter
import json
from pathlib import Path

from route import HERE, Chooser, Members, pair, read_confirmation, run, word_digest
from quantity import QuantityChooser


def retention(members, waves):
    router = Chooser(members)
    seen = []
    result = []
    for wave in waves:
        choices = [router.choose(req) for req, _ in wave]
        stage = {}
        for policy in ("feedback", "nearest_candidate", "nearest_direct"):
            initial = [first["predictions"][policy] == answer for _, answer, first in seen]
            current = [router.choose(req)["predictions"][policy] == answer for req, answer, _ in seen]
            stage[policy] = pair(initial, current)
        result.append(stage)
        for (req, answer), choice in zip(wave, choices, strict=True):
            seen.append((req, answer, choice))
            router.disclose(req, choice, answer)
    return result


def compare_static(members, waves):
    static = Chooser(members)
    growing = Chooser(members)
    static_quantity = QuantityChooser()
    growing_quantity = QuantityChooser()
    for i in members.training:
        row = members.study.rows[i]
        for selector in (static_quantity, growing_quantity):
            selector.add(row.domain, row.question, row.label.casefold())
    metrics = []
    for wave in waves:
        records = []
        for req, label in wave:
            earlier = static.choose(req)
            current = growing.choose(req)
            bound = static_quantity.predict(req)
            updated = growing_quantity.predict(req)
            records.append(dict(frozen=[earlier["predictions"]["nearest_candidate"], earlier["predictions"]["nearest_direct"], bound[0], bound[1]],
                                updated=[current["predictions"]["nearest_candidate"], current["predictions"]["nearest_direct"], updated[0], updated[1]],
                                answer=label, decision=current))
        metrics.append(records)
        for (req, label), rec in zip(wave, records, strict=True):
            growing.disclose(req, rec["decision"], label)
            growing_quantity.add(req.domain, req.question, label)
    result = {}
    for name, records in (("archived",sum(metrics[:4],[])),("fresh",metrics[-1])):
        per_policy = {}
        for j, policy in enumerate(("nearest_candidate","nearest_direct","quantity_candidate","quantity_direct")):
            before = [r["frozen"][j] == r["answer"] for r in records]
            after = [r["updated"][j] == r["answer"] for r in records]
            per_policy[policy] = dict(frozen_correct=sum(before), updated_vs_frozen=pair(before,after))
        result[name] = per_policy
    return result


def evidence(batch):
    proposals = []
    for row in batch:
        scores = row["predictions"]
        if scores["incumbent"] != scores["nearest_candidate"]:
            proposals.append(dict(key=row["key"], domain=row["domain"], incumbent=scores["incumbent"],
                                  proposed=scores["nearest_candidate"], answer=row["answer"], support=row["support"],
                                  accepted=scores["feedback"] == scores["nearest_candidate"]))
    return proposals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    members = Members()
    fresh = read_confirmation(members, HERE / "fresh.json", HERE / "fresh-states.npz")
    report = run(members, fresh)
    recorded = json.loads((HERE / "results.json").read_text())
    for key in ("heads", "rounds", "archived"):
        if report[key] != recorded[key]:
            raise ValueError(f"changed frozen replay: {key}")
    digest = report["rounds"][-1]["predictions_sha256"]
    placebo = [(req, "dummy-label") for req, _ in fresh]
    assert run(members, placebo)["rounds"][-1]["predictions_sha256"] == digest
    old_keys = sorted(members.historical, key=lambda i: word_digest("router-waves-1:" + members.study.rows[i].question))
    old = [(members.archived(i), members.study.rows[i].label) for i in old_keys]
    def normalized(q):
        return " ".join(q.lower().split())
    original = {normalized(row.question) for row in members.study.rows}
    confirmation = {normalized(req.question) for req, _ in fresh}
    assert len(confirmation) == len(fresh) and not original & confirmation
    waves = [old[j:j+12] for j in range(0, len(old), 12)] + [fresh]
    for i in range(4):
        placebo_round = [[(req, "dummy-label") for req, _ in wave] if j == i else wave for j, wave in enumerate(waves[:i+1])]
        chooser = Chooser(members)
        for wave in placebo_round:
            choices = [chooser.choose(req) for req, _ in wave]
            for (req, label), selected in zip(wave, choices):
                chooser.disclose(req, selected, label)
        assert word_digest(json.dumps(choices, sort_keys=True)) == report["rounds"][i]["predictions_sha256"]
    retrospective = [row for wave in report["rounds"][:4] for row in wave["rows"]]
    summary = {}
    for name, rows in (("published", retrospective), ("fresh", report["rounds"][-1]["rows"])):
        by_member = Counter()
        for row in rows:
            for expert, answer in zip(members.names, row["outputs"]):
                by_member[expert] += int(answer == row["answer"])
        summary[name] = dict(singles=dict(by_member), proposals=evidence(rows),
                             impossible=[r["key"] for r in rows if r["answer"] not in r["outputs"]])
    result = dict(fresh_overlaps=0, changed_ungraded_decisions_after_replacing_every_current_label=0,
                  scores=summary, recheck_before_each_wave=retention(members, waves),
                  static_vs_growing=compare_static(members, waves))
    args.out.write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
