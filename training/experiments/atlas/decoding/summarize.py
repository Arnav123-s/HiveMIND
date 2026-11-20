"""Summarize the fixed production-backend comparison from its receipts."""
import argparse
import json
from pathlib import Path


def summarize(record):
    arms = record["arms"]
    reference = {case["id"]: case for case in arms[0]["cases"]}
    table = {}
    for arm in arms:
        cases = arm["cases"]
        decoded = sum(c["timings"]["predicted_n"] for c in cases)
        decode_ms = sum(c["timings"]["predicted_ms"] for c in cases)
        accepted = sum(c["timings"].get("draft_n_accepted", 0) for c in cases)
        proposed = sum(c["timings"].get("draft_n", 0) for c in cases)
        rows = []
        for c in cases:
            r = reference[c["id"]]
            pairs = zip(c["token_ids"], r["token_ids"])
            mismatch = next((i for i, (a, b) in enumerate(pairs) if a != b), None)
            if mismatch is None and len(c["token_ids"]) != len(r["token_ids"]):
                mismatch = min(len(c["token_ids"]), len(r["token_ids"]))
            complete = c["token_trace_complete"] and r["token_trace_complete"]
            rows.append({"id": c["id"], "exact_token_ids": mismatch is None and complete,
                         "first_different_token_at_zero_based_index": mismatch,
                         "both_token_traces_complete": complete, "same_message": c["message"] == r["message"],
                         "same_finish": c["finish_reason"] == r["finish_reason"]})
        table[arm["arm"]] = {
            "status": arm["status"], "complete_prompts": len(cases), "comparisons": rows,
            "complete_exact_token_traces": sum(r["exact_token_ids"] for r in rows),
            "matching_messages": sum(r["same_message"] for r in rows),
            "output_tokens": decoded, "decode_tokens_per_s": round(1000 * decoded / decode_ms, 4) if decode_ms else None,
            "draft_tokens": proposed, "draft_accepted": accepted,
            "acceptance_fraction": round(accepted / proposed, 4) if proposed else None,
            "http_wall_s": round(sum(c["http_wall_s"] for c in cases), 4),
            "server_cpu_s": round(sum(c["server_cpu_s"] for c in cases), 4),
        }
    anchor = table[arms[0]["arm"]]
    for result in table.values():
        if result["status"] == "ok" and result["complete_prompts"] == len(reference):
            result["decode_speed_ratio_to_first"] = round(result["decode_tokens_per_s"] / anchor["decode_tokens_per_s"], 4)
            result["wall_speed_ratio_to_first"] = round(anchor["http_wall_s"] / result["http_wall_s"], 4)
    return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(json.loads(args.receipt.read_text())), indent=2))
