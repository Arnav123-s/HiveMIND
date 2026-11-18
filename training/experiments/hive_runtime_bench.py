"""End-to-end CPU timing on paired tasks with one fixed adapter and a private KV cache."""
import argparse
import time
from pathlib import Path

from team import ternary
from training.experiments import rule_lab as lab
from training.experiments.rule_lab_cpu import serving


def exchange(seed, history):
    law = lab.secret(seed, "affine")
    obs = [[x, y, lab.instrument(law, x, y)] for x, y in ((0, 0), (0, 1), (1, 0), (1, 1))]
    messages = lab.messages("affine", "open", {"observations": obs, "turns": []})
    if history:
        ledger = "\n".join(f"Instrument {i:02d}: its notebook and service record have been archived."
                           for i in range(32))
        messages[1:1] = [{"role": "user", "content": "Keep this equipment inventory in the conversation.\n" + ledger},
                         {"role": "assistant", "content": "I have the inventory. I will use the current sensor's readings to calibrate it."}]
    return law, obs, messages


def request(cpu, messages, cache):
    start = time.perf_counter()
    out = ternary._post(cpu.url + "/v1/chat/completions", {
        "messages": messages, "max_tokens": 64, "temperature": 0., "seed": 1234, "cache_prompt": cache,
        "response_format": {"type": "json_object"}, "chat_template_kwargs": {"enable_thinking": False}})
    return {"wall_s": time.perf_counter() - start, "text": out["choices"][0]["message"]["content"],
            "usage": out["usage"], "timings": out["timings"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "base", "catalog", "out"):
        p.add_argument(f"--{name}", type=Path, required=True)
    args = p.parse_args()
    rows, blocks = [], []
    # ABBA order across launches; reverse the cache mode and history order on the second pass.
    for block, flash in enumerate((False, True, True, False)):
        params = (args.binary, args.base, args.catalog, args.out / f"logs-{block}")
        with serving(*params, slots=1, threads=4, flash=flash) as cpu:
            start = time.perf_counter()
            cpu.activate("exact")
            startup = time.perf_counter() - start
            request(cpu, [{"role": "user", "content": "Return a JSON object with an empty list."}], False)
            order = (False, True) if block < 2 else (True, False)
            for cache in order:
                for history in order:
                    for i, seed in enumerate((441, 442, 443, 444)):
                        law, obs, messages = exchange(seed, history)
                        row = request(cpu, messages, cache and i > 0)
                        try:
                            guess = lab.checked_action(row["text"], obs, len(law)).get("submit")
                        except (TypeError, ValueError):
                            guess = None
                        correct = guess is not None and tuple(guess) == tuple(law)
                        rows.append(dict(block=block, flash=flash, cache=cache, history=history, seed=seed,
                                         first=i == 0, correct=correct, **row))
            cpu.sample_memory()
            blocks.append(dict(block=block, flash=flash, startup_s=startup, server_peak_kib=cpu.peak_kib))
            lab.save(args.out / "results.json", {"runs": rows, "blocks": blocks, "threads": 4})
            print(block, flash, len(rows), flush=True)


if __name__ == "__main__":
    main()
