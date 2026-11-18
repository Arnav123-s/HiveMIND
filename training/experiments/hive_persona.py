"""Extract a formality direction from an 8B words cell and transplant it into a sibling data cell."""
import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from team import ternary
from training.experiments.engram_regrow import GGUFReader, digest
from training.experiments.rule_lab_cpu import serving


# Every pair communicates the same event. Different events and names are used for evaluation.
PAIRS = (
    ("The invoice has been received.", "Got the invoice, thanks!"),
    ("I confirm receipt of your letter.", "Yep, I got your letter."),
    ("Your reservation has been approved.", "You're all set with that reservation!"),
    ("Please be advised that the office is closed.", "Hey, the office is closed."),
    ("I regret to inform you that the train is delayed.", "Sorry, the train's running late."),
    ("The application is now complete.", "Your application's all done!"),
    ("We appreciate your assistance with the survey.", "Thanks for helping with the survey!"),
    ("The documents are available for collection.", "You can grab the papers now."),
    ("Please accept my congratulations on your promotion.", "Congrats on the promotion!"),
    ("I would be pleased to attend the reception.", "I'd love to come to the reception!"),
    ("Kindly return the signed agreement.", "Can you send the signed agreement back?"),
    ("I acknowledge the change in departure time.", "Got it, the departure time changed."),
)
EXAM = (
    ("the meeting is on Friday at Cedar", ("Friday", "Cedar")),
    ("the pickup is on Monday at Harbor", ("Monday", "Harbor")),
    ("the delivery is on Tuesday at Birch", ("Tuesday", "Birch")),
    ("the appointment is on Wednesday at Maple", ("Wednesday", "Maple")),
    ("the workshop is on Saturday at Summit", ("Saturday", "Summit")),
    ("the rehearsal is on Thursday at Linden", ("Thursday", "Linden")),
    ("the inspection is on Sunday at Northgate", ("Sunday", "Northgate")),
    ("the interview is on Tuesday at Westfield", ("Tuesday", "Westfield")),
)
FORMAL = re.compile(r"\b(kindly|hereby|please be (advised|informed)|(?:i|we) (?:am writing to |would like to )?confirm|"
                    r"this (?:is to|message) confirm\w*|is scheduled|has been scheduled|will take place|"
                    r"dear|regards|pleased to|respectfully)\b", re.I)
CASUAL = re.compile(r"\b(hey|yep|yeah|hi|cheers|cool|got it|no worries|see you|just a heads.up|just letting you know|"
                    r"you're|you'll|we're|it's|that's|let's|i'll|i'm|we'll)\b|!", re.I)


def extract(args):
    directory = args.out
    directory.mkdir(parents=True, exist_ok=True)
    sources = []
    for index, name in enumerate(("formal", "casual")):
        path = directory / (name + ".txt")
        path.write_text("\n".join("My reply: " + pair[index] for pair in PAIRS) + "\n")
        sources.append(path)
    path = directory / "direction.gguf"
    with (directory / "extract.log").open("w") as log:
        subprocess.run([str(args.generator.resolve()), "-m", str(args.base), "--lora", str(args.catalog / (args.donor + ".gguf")),
                        "-rtr", "-c", "256", "-t", "4", "--method", "mean", "--positive-file", str(sources[0]),
                        "--negative-file", str(sources[1]), "-o", str(path)], stdout=log, stderr=log, check=True)
    shuffled = directory / "scrambled.gguf"
    shutil.copyfile(path, shuffled)
    rng = np.random.default_rng(739)
    reader = GGUFReader(shuffled, "r+")
    layers = {}
    for tensor in reader.tensors:
        x = tensor.data.reshape(-1)
        if not np.isfinite(x).all() or np.linalg.norm(x) < 1e-6:
            raise ValueError(f"unusable direction at {tensor.name}")
        layers[tensor.name] = {"length": x.size, "norm": float(np.linalg.norm(x))}
        x[:] = x[rng.permutation(len(x))]
    reader.data.flush()
    (directory / "extraction.json").write_text(json.dumps(dict(donor=args.donor, donor_sha256=digest(args.catalog / (args.donor + ".gguf")),
        base_sha256=digest(args.base), direction_sha256=digest(path), scrambled_sha256=digest(shuffled),
        pairs=PAIRS, layers=layers), indent=2) + "\n")


def markers(text, facts):
    value = text.replace("’", "'")
    mentioned = all(re.search(rf"\b{re.escape(f)}\b", value, re.I) for f in facts)
    other_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"} - {facts[0].lower()}
    contradiction = bool(set(re.findall(r"[a-z]+", value.lower())) & (other_days | {"not", "cancelled", "canceled"}))
    return {"both_facts": bool(mentioned and not contradiction), "formal_marker": bool(FORMAL.search(value)),
            "casual_marker": bool(CASUAL.search(value))}


def grade(args):
    conditions = {"off": None, "explicit_formal": None, "explicit_casual": None,
                  "positive": ("direction.gguf", 1.5), "negative": ("direction.gguf", -1.5),
                  "scrambled": ("scrambled.gguf", 1.5)}
    # Extracted vectors have one direction per residual layer. Work only on layers 10..30.
    rows = []
    for arm, config in conditions.items():
        control = (args.out / config[0], config[1], 10, 30) if config else None
        with serving(args.binary, args.base, args.catalog, args.out / ("logs-" + arm),
                     slots=2, threads=4, flash=True, control=control) as cpu:
            for member, exams in ((args.donor, EXAM[:4]), (args.recipient, EXAM)):
                cpu.activate(member)
                for i, (statement, facts) in enumerate(exams):
                    ask = f"Write a one-sentence message to Sam confirming that {statement}. Include the day and place."
                    if arm.startswith("explicit_"):
                        ask += f" Use a distinctly {arm.split('_')[1]} tone."
                    start = time.perf_counter()
                    out = ternary._post(cpu.url + "/v1/chat/completions", {
                        "messages": [{"role": "user", "content": ask}], "max_tokens": 48, "temperature": 0.,
                        "seed": 1234, "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}})
                    reply = out["choices"][0]["message"]["content"]
                    rows.append(dict(member=member, arm=arm, case=i + 1, prompt=ask, reply=reply,
                                     seconds=time.perf_counter() - start, **markers(reply, facts)))
        (args.out / "responses.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(arm, len(rows), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("extract", "grade"))
    for key in ("out", "base", "catalog"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--generator", type=Path)
    p.add_argument("--binary", type=Path)
    p.add_argument("--donor", default="t80+g41words")
    p.add_argument("--recipient", default="t80+g41data")
    args = p.parse_args()
    if args.stage == "extract":
        if not args.generator:
            p.error("extraction needs --generator")
        extract(args)
    else:
        if not args.binary:
            p.error("grading needs --binary")
        grade(args)


if __name__ == "__main__":
    main()
