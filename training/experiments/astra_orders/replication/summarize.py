"""Delivery and cost accounting from the frozen case and execution receipts."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def summarize():
    results = json.loads((HERE / "scores.json").read_text())
    receipts = [json.loads(path.read_text()) for path in sorted((HERE / "offers").glob("*.json"))]
    charges = {(c["id"], c["arm"]):c for r in receipts for c in r["calls"]}
    report = {"native_offers":len(charges), "server_load_s":round(sum(r["load_seconds"] for r in receipts),2),
              "native_wall_s":round(sum(c["wall_s"] for c in charges.values()),2),
              "native_cpu_s":round(sum(c["server_cpu_s"] for c in charges.values()),2), "runtimes":{}}
    for engine, rows in results.items():
        stats = {}
        for policy in ("stock2", "greedy2", "stock3", "greedy3"):
            spent = []
            decisions = [r["decisions"][policy] for r in rows]
            for r, d in zip(rows, decisions):
                second = "short2" if policy.startswith("stock") else "greedy2"
                spent.extend(charges[r["id"], arm] for arm in ["short", second, "short3"][:d["seats"]])
            stats[policy] = {"right":sum(d["result"] == "right" for d in decisions),
                             "wrong":sum(d["result"] == "wrong" for d in decisions),
                             "abstained":sum(d["result"] == "abstain" for d in decisions),
                             "any_correct_among_used":sum(d["any_correct"] for d in decisions),
                             "calls":len(spent), "wall_s":round(sum(c["wall_s"] for c in spent),2),
                             "cpu_s":round(sum(c["server_cpu_s"] for c in spent),2),
                             "completion_tokens":sum(c["usage"]["completion_tokens"] for c in spent)}
        single = {arm:sum(r["offers"][arm]["ok"] for r in rows) for arm in rows[0]["offers"]}
        paired = {"gained":[], "lost":[], "additional_wrong":[]}
        for r in rows:
            d = r["decisions"]
            before, after = d["stock3"]["result"], d["greedy3"]["result"]
            if before != "right" and after == "right":
                paired["gained"].append(r["id"])
            if before == "right" and after != "right":
                paired["lost"].append(r["id"])
            if before != "wrong" and after == "wrong":
                paired["additional_wrong"].append(r["id"])
        report["runtimes"][engine] = {"policies":stats,"single_offer_correct":single,"paired":paired}
    return report


if __name__ == "__main__":
    print(json.dumps(summarize(), indent=2))
