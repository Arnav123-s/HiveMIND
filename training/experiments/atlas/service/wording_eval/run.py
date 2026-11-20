"""Evaluate both calculator entry points against the independently committed date keys."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from training.experiments.atlas.service import ask, wording

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grade(receipt, value):
    if receipt is None or receipt.get("status") != "answered":
        return "appropriate_withhold" if value is None else "missed"
    got = receipt["value"]
    if isinstance(got, str):
        got = got.casefold()
    return "correct" if value is not None and type(got) is type(value) and got == value else "wrong"


def evaluate():
    for entry in (HERE / "manifest.sha256").read_text().splitlines():
        h, name = entry.split()
        assert digest(HERE / name) == h
    assert digest(wording.__file__) == "90ffee46361bc49a65c935734c497c6d9af0dc370ce1a42184b70282e6ead799"
    panel = json.loads((HERE / "panel.json").read_text())
    keys = json.loads((HERE / "keys.json").read_text())
    rows = []
    for entry in panel:
        question = entry["question"]
        strict = ask.calculation(question)
        canonical = wording.canonical_question(question) if strict is None else None
        resulting = ask.calculation(canonical) if canonical else strict
        value = keys[entry["id"]]["value"]
        rows.append(dict(**entry, expected=value, strict=strict, canonical=canonical, augmented=resulting,
                         strict_grade=grade(strict, value), augmented_grade=grade(resulting, value)))
    summary = {arm: dict(Counter(r[arm+"_grade"] for r in rows)) for arm in ("strict", "augmented")}
    groups = {name: {arm:dict(Counter(r[arm+"_grade"] for r in rows if r["group"] in scope))
                     for arm in ("strict","augmented")}
              for name, scope in {"weekday_or_elapsed":["direct","wording"],"other_answerable":["neighbor"],
                                  "invalid_or_ambiguous":["invalid","underspecified"]}.items()}
    return dict(sources={Path(mod.__file__).name:digest(mod.__file__) for mod in (ask, ask.certificate, wording)},
                summary=summary, groups=groups, rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    obj = evaluate()
    args.out.write_text(json.dumps(obj, indent=2)+"\n")
    print(json.dumps({k:v for k,v in obj.items() if k != "rows"}, indent=2))
