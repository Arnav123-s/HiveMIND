"""Confirm every question of a native-qualified corrective candidate through actual HTTP generation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from training import domain_engram


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--water", type=Path)
    parser.add_argument("--timing", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    jobs = []
    for study, key, weights in (("water-v2", "physics", args.water), ("timing-v2", "engineering", args.timing)):
        if weights is None:
            continue
        proof = json.loads((HERE / study / "qualification.json").read_text())
        if not proof["qualified"]:
            continue
        if hashlib.sha256(weights.read_bytes()).hexdigest() != proof["v2_sha256"]:
            parser.error("the requested file differs from the prequalified candidate")
        jobs.append((study, key, weights.resolve(), proof))
    if not jobs:
        return
    exercises = json.loads((HERE / "exercises.json").read_text())
    template = (HERE / "study-template.txt").read_text()
    system = (HERE / "system.txt").read_text()
    edits = [j[2] for j in jobs]
    with domain_engram._server(args.model, args.runtime, args.threads, edits=edits) as url:
        with urllib.request.urlopen(url + "/lora-adapters", timeout=20) as response:
            manifest = json.load(response)
        id_for = {Path(row["path"]).resolve(): row["id"] for row in manifest}
        for study, key, weights, proof in jobs:
            expected_id = id_for[weights]
            scales = [{"id": row["id"], "scale": float(row["id"] == expected_id)} for row in manifest]
            domain_engram._post(url, "/lora-adapters", scales)
            cases = []
            for original in proof["cases"]:
                user = exercises[key]["instruction"] + " " + original["text"]
                row = {"prompt": user, "answer": original["label"], "system": system}
                rendered = domain_engram._render(url, row)
                same = rendered == template.replace("{{USER}}", user)
                count = len(domain_engram._post(url, "/tokenize", {"content": rendered})["tokens"])
                if not same or count != original["input_tokens"]:
                    raise ValueError("native HTTP renderer or token count differs from frozen comparison")
                raw = domain_engram._post(url, "/v1/chat/completions", {
                    "messages": domain_engram._messages(row), "max_tokens": 1, "temperature": 0, "seed": 741,
                    "cache_prompt": True, "chat_template_kwargs": {"enable_thinking": False}})
                piece = raw["choices"][0]["message"]["content"]
                cases.append(dict(id=original["id"], phase=original["phase"], expected=row["answer"], text=piece,
                                  correct=piece.strip().casefold() == row["answer"].casefold(),
                                  same_rendered_prompt=same, rendered_tokens=count, usage=raw.get("usage")))
                print(study, original["id"], repr(piece), flush=True)
            with urllib.request.urlopen(url + "/lora-adapters", timeout=20) as response:
                observed = json.load(response)
            active = [r["id"] for r in observed if r.get("scale") == 1]
            if active != [expected_id] or any(r.get("scale") not in (0, 1) for r in observed):
                raise ValueError("native active weights differ from requested candidate")
            result = dict(qualified=all(r["correct"] for r in cases), sha256=proof["v2_sha256"],
                          graph_reuse=False, threads=args.threads, native_active_id=expected_id, cases=cases)
            (args.out / (study + ".json")).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
