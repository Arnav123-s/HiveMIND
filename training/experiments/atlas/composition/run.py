"""Fit three output-only factors on frozen CPU states and measure real multi-LoRA decoding."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import monotonic
from urllib.request import urlopen

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from training import domain_engram as native

LABELS = "ABCDEFGH"
FACTORS = ("source", "threshold", "format")
SYSTEM = ("Assign the lab's one-letter service code. Start at A. For a mirror port advance four letters, "
          "for a queue of eight or more samples advance two letters, and for the current form advance one. "
          "The other options are local port, fewer than eight samples, and legacy form. Return only the code.")


def panel():
    cases = []
    for phase, values in [("train", [1, 3, 5, 9, 11, 13]), ("test", [2, 4, 6, 10, 12, 14])]:
        for i in range(8):
            unseen = i in (0, 7)
            if phase == "train" and unseen:
                continue
            source, threshold, form = ((i >> bit) & 1 for bit in (2, 1, 0))
            for k in range(3 if phase == "train" or unseen else 2):
                count = values[threshold * 3 + k]
                port = ("local", "mirror")[source]
                layout = ("legacy", "current")[form]
                if phase == "train":
                    prompt = f"Port: {port}. Queue: {count} samples. Form: {layout}. Code?"
                else:
                    prompt = f"The {layout} form records {count} samples waiting on the {port} port. Which code?"
                cases.append(dict(id=f"{phase}-{i}-{k}", phase=phase, unseen=unseen, bits=[source, threshold, form],
                                  system=SYSTEM, prompt=prompt, answer=LABELS[i]))
    return cases


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("model", "runtime", "scratch", "out"):
        p.add_argument("--" + arg, type=Path, required=True)
    p.add_argument("--threads", type=int, default=2)
    args = p.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    if args.out.exists():
        p.error("--out must be a new path")
    cases = panel()
    train = [r for r in cases if r["phase"] == "train"]
    test = [r for r in cases if r["phase"] == "test"]
    t0 = monotonic()
    model_hash = native._base_hash(args.model, args.model.stat().st_size)
    if model_hash != native.T80_SHA256:
        raise ValueError("Wrong base model")
    train, states = native._feature_rows(train, test, args.model, args.runtime, args.threads)
    if len(train) != 18:
        raise ValueError("Expected all eighteen fitting rows")
    with native._server(args.model, args.runtime, args.threads) as url:
        tokens = [r["token"] for r in native.eligible_rows([{"prompt": "Code?", "answer": l} for l in LABELS], url)]
    if len(set(tokens)) != 8:
        raise ValueError("Each output code needs one distinct native token")
    weights = {}
    ids, a, b, _ = native.fit(states, [r["token"] for r in train])
    weights["joint"] = args.scratch / "joint.gguf"
    native.write_adapter(weights["joint"], ids, a, b, 151669)
    for axis, name in enumerate(FACTORS):
        ids, a, b, _ = native.fit(states, [r["bits"][axis] for r in train])
        if ids.tolist() != [0, 1]:
            raise ValueError("Missing an axis value")
        # Broadcast each binary learned score onto matching contract labels. The mapping is supplied.
        rows = [(i >> (2 - axis)) & 1 for i in range(8)]
        weights[name] = args.scratch / (name + ".gguf")
        native.write_adapter(weights[name], tokens, a, b[rows], 151669)
    fit_wall = monotonic() - t0
    arms = {"base": {}, "joint": {"joint": 1}, **{f: {f: 1} for f in FACTORS},
            "three_mean": dict.fromkeys(FACTORS, 1 / 3), "three_sum": dict.fromkeys(FACTORS, 1)}
    trials = []
    with native._server(args.model, args.runtime, args.threads, edits=weights.values()) as url:
        with urlopen(url + "/lora-adapters") as response:
            manifest = {Path(r["path"]).stem: r["id"] for r in json.load(response)}
        for row in test:
            observed = {}
            for arm, active in arms.items():
                scales = [{"id": idx, "scale": active.get(name, 0)} for name, idx in manifest.items()]
                native._post(url, "/lora-adapters", scales)
                with urlopen(url + "/lora-adapters") as response:
                    actual = json.load(response)
                if any(abs(x["scale"] - active.get(Path(x["path"]).stem, 0)) > 1e-6 for x in actual):
                    raise RuntimeError("Scale readback differs")
                result = native._post(url, "/v1/chat/completions", {
                    "messages": native._messages(row), "max_tokens": 1, "temperature": 0, "seed": 221,
                    "cache_prompt": True, "chat_template_kwargs": {"enable_thinking": False}})
                observed[arm] = result["choices"][0]["message"]["content"]
            trials.append(dict(id=row["id"], prompt=row["prompt"], unseen=row["unseen"], expected=row["answer"], replies=observed))
            print(row["id"], observed, flush=True)
    totals = {group: {arm: sum(t["replies"][arm].strip() == t["expected"] for t in trials if t["unseen"] == unseen)
                      for arm in arms} for group, unseen in (("new_combinations", True), ("familiar_combinations", False))}
    result = dict(system=SYSTEM, training_cases=train, trials=trials, scores=totals, arms=arms, threads=args.threads,
                  model_sha256=model_hash, runtime_sha256=sha256(args.runtime.read_bytes()).hexdigest(),
                  weights_sha256={s: sha256(f.read_bytes()).hexdigest() for s,f in weights.items()},
                  fit_wall_seconds=round(fit_wall, 3), total_wall_seconds=round(monotonic()-t0, 3))
    write(args.out, result)
    print(totals)


if __name__ == "__main__":
    main()
