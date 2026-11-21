"""Aggregate the paired frozen chooser replay. Keep single-offer, potential and delivered scores distinct."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def totals():
    replay = json.loads((HERE / "scores.json").read_text())
    new = json.loads((HERE / "native.json").read_text())
    samples = [c for c in json.loads((HERE.parent / "native.json").read_text())["calls"] if c["arm"] == "short"] + new["calls"]
    costs = {(call["id"], call["arm"]): call for call in samples}
    summary = {"extra_native_calls_generated": len(new["calls"]),
               "new_native_wall_seconds": round(sum(c["wall_s"] for c in new["calls"]), 2),
               "new_native_server_cpu_seconds": round(sum(c["server_cpu_s"] for c in new["calls"]), 2),
               "new_prompt_tokens": sum(c["usage"]["prompt_tokens"] for c in new["calls"]),
               "new_completion_tokens": sum(c["usage"]["completion_tokens"] for c in new["calls"]),
               "server_load_seconds": new["load_seconds"], "runtimes": {}}
    for engine, rows in replay["runtimes"].items():
        counts = {}
        for policy in ("short2", "diverse2", "short3", "diverse3", "greedy_diverse2", "greedy_diverse3"):
            group = "exploratory" if policy.startswith("greedy_") else "policies"
            outcomes = [row[group][policy]["result"] for row in rows]
            potential = independent_calls = wall = cpu = 0
            for row in rows:
                ident = row["id"]
                second = "short2"
                if "diverse" in policy and "modular2" in row["offers"]:
                    second = "modular0" if group == "exploratory" else "modular2"
                n = row[group][policy]["seats"]
                used = ["short", second, "short3"][:n]
                potential += any(row["offers"][p]["ok"] for p in used)
                independent_calls += n
                wall += sum(costs[(ident,p)]["wall_s"] for p in used)
                cpu += sum(costs[(ident,p)]["server_cpu_s"] for p in used)
            counts[policy] = {"correct":outcomes.count("right"), "wrong":outcomes.count("wrong"),
                              "abstain":outcomes.count("abstain"), "calls":independent_calls,
                              "any_correct_among_used":potential, "recorded_call_wall_s":round(wall,2),
                              "recorded_call_cpu_s":round(cpu,2)}
        summary["runtimes"][engine] = {
            "original_short":sum(row["offers"]["short"]["ok"] for row in rows),
            "modular_greedy_routed":sum(row["offers"].get("modular0", row["offers"]["short"])["ok"] for row in rows),
            "policies":{k:v for k,v in counts.items() if not k.startswith("greedy_")},
            "exploratory":{k:v for k,v in counts.items() if k.startswith("greedy_")}}
    return summary


if __name__ == "__main__":
    print(json.dumps(totals(), indent=2))
