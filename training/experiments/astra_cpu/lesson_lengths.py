"""Measure both training turns of fresh, verified C1 lessons with the real trainer tokenizer."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from tokenizers import Tokenizer
from transformers import AutoTokenizer

from training import grow, lessons
from training.kinds import HELD_OUT

KINDS = ("h_prog_bank", "h_prog_calc", "h_prog_lru", "h_prog_machine", "h_prog_schedule")
TODAY = "2026-01-01 (Thursday)"


def measure(tokenizer_directory, draws):
    token_file = Path(tokenizer_directory) / "tokenizer.json"
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_directory, local_files_only=True)
    # Production lesson generation uses the shared tokenizer if available. Pin it for this standalone replay.
    lessons._TOK[:] = [Tokenizer.from_file(str(token_file))]
    levels = grow.body_levels()
    results = []
    for kind in KINDS:
        assert kind in lessons.SOLVERS and kind not in HELD_OUT
        for index in range(draws):
            key = f"astra-wave-one-length:{kind}:{index}"
            example = lessons.fitting(kind, key, level=levels.get(kind, 0))
            record = {"kind": kind, "draw": index, "level": levels.get(kind, 0), "verified": example["ok"],
                      "chosen_seed": example.get("rseed"), "turns": []}
            for row in lessons.rows(example, today=TODAY):
                answer = tokenizer(row["output"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
                fits = {}
                for cap in (508, 1152):
                    messages = row["messages"]
                    for keep in (None, 0.6, 0.35, 0.15):
                        if keep is not None:
                            messages = grow.shorten(row["messages"], keep)
                            if messages is row["messages"]:
                                break
                        prompt = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                               enable_thinking=False, return_dict=False)
                        if keep is None:
                            original = len(prompt) + len(answer)
                        if len(prompt) + len(answer) <= cap:
                            fits[str(cap)] = len(prompt) + len(answer)
                            break
                    fits.setdefault(str(cap), None)
                record["turns"].append({"type": row["type"], "pieces": original, "encoded_at_cap": fits})
            results.append(record)
    return {"tokenizer_sha256": sha256(token_file.read_bytes()).hexdigest(), "date_in_prompt": TODAY,
            "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = measure(args.tokenizer, args.draws)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    for case in report["cases"]:
        print(case["kind"], case["draw"], case["verified"], [r["pieces"] for r in case["turns"]])
