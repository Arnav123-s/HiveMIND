"""Inspect consultation and direct-weight selection without generating an answer."""
import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def audit(checkout, bank, *, positive_control=False):
    os.environ.update(HIVE_ENGRAMS="1", HIVE_SIGNALS="1", HIVE_ENGRAMS_HOME=str(bank))
    sys.path.insert(0, str(checkout))
    from team import domain_advice, domain_route, engram, ternary

    class WouldInfer(Exception):
        pass

    def describe_inference(member, messages, **kwargs):
        raise WouldInfer(dict(member=member, prompt=messages[-1]["content"], **kwargs))

    ternary.chat = describe_inference
    submit = domain_advice._query
    def capture(base, system, prompt, row, skill, *, expected=None):
        try:
            submit(base, system, prompt, row, skill, expected=expected)
        except WouldInfer as call:
            return dict(edit=row["name"], sha256=row["sha256"], skill=skill, expected_label=expected, call=call.args[0])
        raise RuntimeError("Consultation did not reach inference")

    domain_advice._query = capture
    records = {r["name"]: r for r in map(json.loads, (bank / "index.jsonl").read_text().splitlines())}
    rows = []
    tasks = json.loads((HERE / "panel.json").read_text())
    if positive_control:
        tasks = [{"id": "instrument-control",
                  "prompt": "In Python, which operation should I use to keep only rows that meet a condition?"}]
    for task in tasks:
        message = task["prompt"]
        with domain_route.for_request(message) as decision:
            modes = {}
            for way in ("talk", "work"):
                consultation = domain_advice.consult(message, "t80", domain_route.current_domain(), "",
                                                     direct_labels=way == "talk")
                direct = []
                for item in engram.for_request(message, "t80", labels=way == "talk"):
                    name, scale = (item, 1) if isinstance(item, str) else item
                    direct.append(dict(edit=name, sha256=records[name]["sha256"], scale=scale))
                modes[way] = dict(consultation=consultation, direct=direct)
            rows.append(dict(id=task["id"], domain=(decision or {}).get("domain"), modes=modes))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--positive-control", action="store_true",
                        help="run one independent, in-scope instrument check instead of the answer panel")
    args = parser.parse_args()
    rows = audit(args.checkout.resolve(), args.bank.resolve(), positive_control=args.positive_control)
    args.out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
