"""Score the exact frozen message and separately show the effect of supplying a source name."""
from hashlib import sha256
import json
from pathlib import Path
import re

from . import ingress


HERE = Path(__file__).resolve().parent
PANEL = "48809ec7ea5dac934787041202f122855d6e5712eb22201ba5079ecc1f8c9dd4"
ADAPTER = "17d058b893caf48ce7e1f9c756c6de8101bdcf4e750fd19410461b7d1ba51498"


def grade(case, result):
    files = result.get("files", {})
    if result["status"] != "answered":
        if files:
            return "wrong"
        return "missed" if case["judgment"] == "answer" else "appropriate_hold"
    if case["judgment"] != "answer" or set(files) != {case["file"]}:
        return "wrong"
    value = json.loads(files[case["file"]])
    correct = (type(value) is type(case["expected"]) and value == case["expected"]
               and result.get("value") == case["expected"])
    return "correct" if correct else "wrong"


def run():
    with (HERE / "confirmation.json").open("rb") as file:
        raw = file.read()
    assert sha256(raw).hexdigest() == PANEL
    assert sha256(Path(ingress.__file__).read_bytes()).hexdigest() == ADAPTER
    outputs = []
    for case in json.loads(raw):
        literal = case["request"]
        raw_result = ingress.solve_message(literal)
        # This additional counterfactual supplies input metadata the original user did not provide.
        declared = re.search(r"```(csv|tsv)\n", literal)[1]
        filename = case["id"] + "." + declared
        named = literal.replace("```" + declared + "\n", "```" + declared + " " + filename + "\n", 1)
        named_result = ingress.solve_message(named)
        outputs.append({"case": case["id"], "user_supplied_source_name": False, "raw": raw_result,
                        "raw_grade": grade(case, raw_result), "extra_source_name": filename,
                        "with_name": named_result, "with_name_grade": grade(case, named_result)})
    return {"panel_sha256": PANEL, "adapter_sha256": ADAPTER, "cases": outputs}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
