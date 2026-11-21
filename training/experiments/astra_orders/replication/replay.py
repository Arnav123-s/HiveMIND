"""Run isolated artifacts, select through the live chooser, and only then open the grading criteria."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile

from training.experiments.astra_orders.diverse.replay import choose, execute
from training.experiments.astra_orders.replication import native
from training.experiments.fieldwork.guest import Guest

HERE = Path(__file__).resolve().parent


def replay(sdk):
    cases = (HERE / "cases.json").read_bytes()
    assert sha256(cases).hexdigest() == native.CASES_HASH
    rows = json.loads(cases)
    pins = json.loads((HERE / "reviewed.json").read_text())
    records = {}
    for row in rows:
        source = (HERE / "offers" / (row["id"] + ".json")).read_bytes()
        if sha256(source).hexdigest() != pins[row["id"]]:
            raise ValueError("protected host replay requires review of every program")
        receipt = json.loads(source)
        assert receipt["complete"] and receipt["inputs_sha256"] == native.CASES_HASH
        for saved, (_, arm, messages, settings) in zip(receipt["calls"], native.offers(row), strict=True):
            assert saved["id"] == row["id"] and saved["arm"] == arm and saved.get("sampling_override", {}) == settings
            assert saved["system_sha256"] == sha256(messages[0]["content"].encode()).hexdigest()
        records[row["id"]] = receipt["calls"]
    out = {}
    for runtime, guest in (("cpython", None), ("wasi", Guest(sdk))):
        results = []
        with tempfile.TemporaryDirectory() as tmp:
            for row in rows:
                calls = records[row["id"]]
                offers = {c["arm"]:execute(guest, row, c["arm"], c, Path(tmp) / row["id"]) for c in calls}
                policies = {}
                for policy, second in (("stock", "short2"), ("greedy", "greedy2")):
                    for cap in (2, 3):
                        used = ["short", second, "short3"][:cap]
                        policies[policy + str(cap)] = choose(used, offers, row["task"], diverse=policy == "greedy")
                results.append({"id":row["id"], "offers":offers, "decisions":policies})
            from training.experiments.astra_orders.replication import grader
            for row, result in zip(rows, results, strict=True):
                for offer in result["offers"].values():
                    work = Path(offer.pop("work"))
                    offer["ok"] = not offer["error"] and grader.grade(row, offer["answer"], work)
                for policy, decision in result["decisions"].items():
                    picked = decision["selected"]
                    decision["result"] = "abstain" if picked is None else "right" if result["offers"][picked]["ok"] else "wrong"
                    observed = ["short", "short2" if policy.startswith("stock") else "greedy2", "short3"][:decision["seats"]]
                    decision["any_correct"] = any(result["offers"][a]["ok"] for a in observed)
        out[runtime] = results
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--sdk", type=Path, required=True)
    args = p.parse_args()
    args.out.write_text(json.dumps(replay(args.sdk), sort_keys=True, indent=2) + "\n")
