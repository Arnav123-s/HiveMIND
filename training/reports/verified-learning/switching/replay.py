"""Qualify four existing drafts, then switch between them in fresh ./hive processes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from team import config, saved
from training.experiments.fieldwork import work as fw
from training.experiments.fieldwork.guest import Guest

REPORTS = ROOT / "training/reports/retained-skills"
POOLED = """def solve(x):
    return 250 + 90 * ((sum(x['grams']) + 499) // 500) if x['grams'] else 0"""


def replay(sdk, directory):
    bank = directory / "bank"
    guest = Guest(sdk)
    env = os.environ | {
        "HIVE_PYTHON": sys.executable, "HIVE_BANK": str(bank), "HIVE_FIELDWORK_SDK": str(sdk.resolve()),
        "HIVE_ROLES": "0", "HIVE_TERNARY_HOME": str(directory / "no-models"),
        "HIVE_ADAPTERS_HOME": str(directory / "no-adapters"),
    }
    prequalified, = fw.load_bank(REPORTS / "shipping/bank")
    invoices = json.loads((REPORTS / "work-order-cases.json").read_text())["programs"]
    admissions, requests = {}, []

    def admit(label, contract, source, field, public, qualification):
        def examples(pairs):
            return [{"input": {field: amounts}, "output": due} for amounts, due in pairs]
        spec = {"name": contract[0], "task": contract[1], "examples": examples(public),
                "validation": examples(qualification), "jobs": [{"id": "bill", "input": {field: public[0][0]}}]}
        def supply(*_):
            return {"source": source, "usage": {}}
        result = fw.work(spec, guest, supply, directory / label, bank, rounds=1)
        assert result["public"] == result["validated"] == 2 and "value" in result["jobs"][0], result
        admissions[label] = {"draft_sha256": fw.fingerprint(source), "retained_sha256": result["digest"],
                             "public_passed": result["public"], "qualification_passed": result["validated"]}

    def ask(message, *, due=None, selected=None, note=None):
        command = subprocess.run([str(ROOT / "hive"), "--once", message], cwd=ROOT, env=env,
                                 capture_output=True, text=True, timeout=90)
        lines = command.stdout.strip().splitlines()
        assert command.returncode == (1 if due is None else 0) and lines, (message, command.stderr, lines)
        if due is not None:
            assert lines[0] == str(due), (message, lines)
            if selected:
                assert admissions[selected]["retained_sha256"][:12] in command.stdout, (message, lines)
        if note:
            assert note in command.stdout, (message, lines)
        requests.append({"request": message, "exit_code": command.returncode, "value_cents": due,
                         "selected": selected, "stdout": command.stdout.strip()})

    admit("pooled", saved.SHIPPING, POOLED, "grams", [([101, 208], 340), ([505, 510], 520)],
          [([82, 215, 503], 430), ([41, 42], 340)])
    ask("Calculate the shipping fee for parcels of 250 g and 250 g with our usual per-parcel pricing.",
        note="No saved version passed")
    admit("per_parcel", saved.SHIPPING, prequalified["source"], "grams", [([101, 208], 430), ([505, 510], 610)],
          [([82, 215, 503], 610), ([41, 42], 430)])
    admit("per_line", saved.INVOICE, invoices["per_line"], "lines", [([12, 12], 2), ([25, 25], 2)],
          [([15, 35], 3), ([8, 8], 0)])
    admit("invoice_total", saved.INVOICE, invoices["per_invoice"], "lines", [([12, 12], 1), ([25, 25], 3)],
          [([15, 35], 3), ([8, 8], 1)])
    ask("Calculate the shipping fee for parcels of 130 g and 170 g using per-parcel pricing.", due=430, selected="per_parcel")
    ask("Calculate the shipping fee for parcels of 620 g and 630 g using pooled rounding.", due=520, selected="pooled")
    ask("Calculate the shipping fee for parcels of 119 g and 230 g using per-parcel pricing.", due=430, selected="per_parcel")
    ask("Calculate the invoice tax for lines of 14, 14 and 14 cents using per-line rounding.", due=3, selected="per_line")
    ask("Calculate the invoice tax for lines of 16 and 10 cents using invoice-total rounding.", due=1, selected="invoice_total")
    ask("Calculate the invoice tax for lines of 4 and 7 cents using per-line rounding.", due=0, selected="per_line")
    ask("Calculate the invoice tax for lines of 4 and 7 cents.", note="disagree")
    ask("Calculate the invoice tax for lines of 20 and 40 cents.", due=3, note="which agree")
    ask('Run depot_shipping_fee@deadbeefdead with {"grams":[100]}', note="unavailable")
    return {"method": "Four supplied drafts qualified in WASI, followed by separate model-free ./hive --once processes.",
            "new_model_calls": 0, "admissions": admissions, "requests": requests}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=config.fieldwork_sdk_path())
    parser.add_argument("--out", type=Path, help="write results to JSON, otherwise print them")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        body = json.dumps(replay(args.sdk, Path(tmp)), indent=2) + "\n"
    if args.out:
        args.out.write_text(body)
    else:
        print(body, end="")
