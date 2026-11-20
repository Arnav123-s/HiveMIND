"""Public before-freeze transport controls using the composer's original supplier example."""
from hashlib import sha256
import json
from pathlib import Path

from .ingress import solve_message


def run():
    question = "Sum units by supplier. Save as totals.json."
    source = 'supplier,units,aisle\nFir,4,East\nElm,3,East\nElm,2,West\n'
    sample = ("orders.csv:\n" + source + "\n" + question)
    baseline = solve_message(question, {"orders.csv": source})
    expected = {"Fir": 4, "Elm": 5}
    assert baseline["status"] == "answered" and baseline["value"] == expected
    arms = {
        "plain_csv": sample,
        "fenced_csv": question + "\nInput file orders.csv:\n```csv\n" + source + "```",
        "named_fence": question + "\n```csv orders.csv\n" + source + "```",
        "fenced_tsv": question + "\n```tsv orders.tsv\n" + source.replace(",", "\t") + "```",
        "plain_tsv": "orders.tsv:\n" + source.replace(",", "\t") + "\n" + question,
    }
    controls = {
        "no_source_name": sample.replace("orders.csv:", "input:"),
        "no_output": sample.replace(" Save as totals.json.", ""),
        "multiple_outputs": sample + " Also save as audit.json.",
        "conflicting_fence": arms["fenced_csv"].replace("```csv", "```tsv"),
        "two_tables": arms["fenced_csv"] + "\n```csv other.csv\na,b\n1,2\n```",
        "short_record": sample.replace("Elm,2,West", "Elm,2"),
        "duplicate_header": sample.replace("supplier,units,aisle", "supplier,units,units"),
        "two_unfenced_inputs": sample + "\n\nother.csv:\nsupplier,units\nFir,3",
        "stray_record": sample.replace("Elm,2,West", "\nElm,2,West"),
        "negated_output": sample.replace("Save as", "Do not save as"),
        "sibling_path": sample.replace("totals.json", "../totals.json"),
        "unclosed_fence": arms["fenced_csv"][:-3],
    }
    results = {}
    for name, message in arms.items():
        result = solve_message(message)
        assert result == baseline, (name, result, baseline)
        results[name] = result
    for name, message in controls.items():
        result = solve_message(message)
        assert result["status"] == "abstained" and not result["files"], (name, result)
        results[name] = result
    mixed = solve_message(arms["fenced_csv"], {"orders.csv": source})
    assert mixed["status"] == "abstained" and not mixed["files"]
    results["mixed_attachment_and_inline"] = mixed
    return {"attachments": baseline, "cases": results,
            "source_sha256": sha256(Path(__file__).with_name("ingress.py").read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
