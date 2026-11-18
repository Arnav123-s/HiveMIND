"""Serve two synthesized LoRAs and both original specialists on matched CPU tasks."""
import argparse
import json
import time
from pathlib import Path

from team import ternary
from training.experiments.engram_transfer import one_reply
from training.experiments.rule_lab_checks import retention
from training.experiments.rule_lab_cpu import serving


class ActiveCell:
    def __init__(self, cpu):
        self.cpu = cpu

    def reply(self, name, messages):
        start = time.perf_counter()
        out = ternary._post(self.cpu.url + "/v1/chat/completions", {
            "messages": messages, "max_tokens": 100, "temperature": 0., "seed": 1234,
            "cache_prompt": False, "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False}}, timeout=180)
        return {"text": out["choices"][0]["message"]["content"], "seconds": time.perf_counter() - start,
                "usage": out.get("usage", {})}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("binary", "base", "catalog", "out"):
        p.add_argument("--" + key, required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = {}
    for label in ("child", "words", "simultaneous", "factor_mean", "effective_svd"):
        with serving(args.binary, args.base, args.catalog, args.out / "logs", slots=2, threads=4, flash=True) as cpu:
            if label == "simultaneous":
                cpu.activate("child")
                cpu.activate("words")
                ternary._switch(cpu.url, [{"id": i, "scale": 0.5} for i in cpu.ids.values()])
            else:
                cpu.activate(label)
            runner = ActiveCell(cpu)
            result[label] = {"affine": [one_reply(runner, label, seed, "affine") for seed in (557, 563, 569, 571)],
                             "ordinary": retention(runner, label)}
        (args.out / "scores.json").write_text(json.dumps(result, indent=2) + "\n")
        print(label, [r["correct"] for r in result[label]["affine"]], flush=True)


if __name__ == "__main__":
    main()
