"""Grade the frozen role panel against its author's exact expected sets."""
import json
from pathlib import Path

from team.deliverables import wanted
from training.experiments.astra_transfer.scaffolds import HERE, load_bank, render, select


def grade(panel):
    bank = load_bank()
    evidence = []
    totals = {name: dict(exact=0, true_positive=0, false_positive=0, false_negative=0)
              for name in ("empty", "output_only", "scaffolds")}
    for i, example in enumerate(panel):
        request = example["request"]
        expected = set(example["expected"])
        known_ext = {".csv": "write_csv", ".json": "write_json", ".py": "write_module"}
        output_only = {known_ext[ext] for name in wanted(request) if (ext := Path(name).suffix.lower()) in known_ext}
        selected = select(request, bank)
        suffix = render(request)
        predictions = {"empty": [], "output_only": sorted(output_only), "scaffolds": selected if suffix else []}
        for arm, pred in predictions.items():
            predicted = set(pred)
            totals[arm]["exact"] += predicted == expected
            totals[arm]["true_positive"] += len(predicted & expected)
            totals[arm]["false_positive"] += len(predicted - expected)
            totals[arm]["false_negative"] += len(expected - predicted)
        evidence.append(dict(case=i + 1, expected=sorted(expected), predictions=predictions,
                             rendered_tokens=bank["tokens"]["+".join(selected)] if suffix else 0))
    return {"cases": len(evidence), "totals": totals, "details": evidence}


if __name__ == "__main__":
    panel = json.loads((HERE / "role_panel.json").read_text())
    print(json.dumps(grade(panel), indent=1))
