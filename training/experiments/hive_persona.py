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
TRANSFER_EXAM = (
    ("Tell Jo in one sentence that the badge color is cobalt and the locker code is 731.", ("cobalt", "731")),
    ("Write one sentence updating Jo. Ticket K427 has been assigned to Rowan.", ("K427", "Rowan")),
    ("Message Jo in a single sentence. The project codename is Amber and its approved budget is 360 euros.", ("Amber", "360")),
    ("Write a short reply to Jo saying the parcel carrier is Finch and the tracking code is P841.", ("Finch", "P841")),
)
# Equivalent typed work-order facts available to a renderer after the underlying action.
STATEMENTS = ("the badge color is cobalt and the locker code is 731",
              "ticket K427 has been assigned to Rowan",
              "the project codename is Amber and its approved budget is 360 euros",
              "the parcel carrier is Finch and the tracking code is P841")
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


def one_sentence(text):
    units = re.split(r'''[.!?]+["'”’]*(?:\s+|$)|\n\s*\n''', text.strip())
    return sum(bool(re.search(r"\w", unit)) for unit in units) == 1


def markers(text, facts):
    value = text.replace("’", "'")
    mentioned = all(re.search(rf"\b{re.escape(f)}\b", value, re.I) for f in facts)
    other_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"} - {f.lower() for f in facts}
    contradiction = bool(set(re.findall(r"[a-z]+", value.lower())) & (other_days | {"not", "cancelled", "canceled"}))
    return {"both_facts": bool(mentioned and not contradiction), "formal_marker": bool(FORMAL.search(value)),
            "casual_marker": bool(CASUAL.search(value)), "one_sentence": one_sentence(text)}


def grade(args, stress=False, confirm=False):
    conditions = {"off": None, "explicit_formal": None, "explicit_casual": None,
                  "positive": ("direction.gguf", 1.5), "negative": ("direction.gguf", -1.5),
                  "scrambled": ("scrambled.gguf", 1.5)}
    members = ((args.donor, range(4)), (args.recipient, range(len(EXAM))))
    if stress or confirm:
        conditions = {"positive12": ("direction.gguf", 12.), "negative12": ("direction.gguf", -12.),
                      "scrambled12": ("scrambled.gguf", 12.)}
        members = ((args.recipient, range(4, len(EXAM))),)
    if confirm:
        conditions = {"off": None, **conditions}
        members = ((args.recipient, range(len(TRANSFER_EXAM))),)
    # Extracted vectors have one direction per residual layer. Work only on layers 10..30.
    rows = []
    for arm, config in conditions.items():
        control = (args.out / config[0], config[1], 10, 30) if config else None
        with serving(args.binary, args.base, args.catalog, args.out / ("logs-" + ("confirm-" if confirm else "") + arm),
                     slots=2, threads=4, flash=True, control=control) as cpu:
            for member, indices in members:
                cpu.activate(member)
                for i in indices:
                    if confirm:
                        ask, facts = TRANSFER_EXAM[i]
                    else:
                        statement, facts = EXAM[i]
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
        dest = "new-topics.json" if confirm else ("high-gain.json" if stress else "responses.json")
        (args.out / dest).write_text(json.dumps(rows, indent=2) + "\n")
        print(arm, len(rows), flush=True)


def portability(args):
    rows = json.loads((args.out / "responses.json").read_text())
    if len(rows) != 6 * (4 + len(EXAM)):
        raise ValueError("grade every treatment before selecting a transferable policy")
    result = {}
    for style, opposite in (("formal", "casual"), ("casual", "formal")):
        arms = ("off", "explicit_" + style, "positive", "negative")
        def hits(member, arm, fresh):
            subset = [r for r in rows if r["member"] == member and r["arm"] == arm and (not fresh or r["case"] > 4)]
            return sum(r["both_facts"] and r[style + "_marker"] and not r[opposite + "_marker"] for r in subset)
        donor = {a: hits(args.donor, a, False) for a in arms}
        # Ties favor the unmodified model, then an explicit instruction, then a vector.
        chosen = max(arms, key=donor.get)
        result[style] = {"source_success_out_of_four": donor, "chosen": chosen,
                         "new_recipient_prompts_success_out_of_four": hits(args.recipient, chosen, True)}
    (args.out / "portability.json").write_text(json.dumps(result, indent=2) + "\n")


def transfer_examples(args):
    """Give the sibling the donor's actual replies as behavioral records with no style label."""
    original = json.loads((args.out / "responses.json").read_text())
    results = {}
    with serving(args.binary, args.base, args.catalog, args.out / "logs-examples", slots=1, threads=4, flash=True) as cpu:
        cpu.activate(args.recipient)
        for style in ("formal", "casual"):
            examples = [r for r in original if r["member"] == args.donor and r["arm"] == "explicit_" + style and r["case"] <= 2]
            if len(examples) != 2:
                raise ValueError("missing paired donor demonstrations")
            prefix = [{"role": "system", "content": "Match the style of the example replies. Use the facts from the latest request."}]
            for sample in examples:
                prefix.extend([{"role": "user", "content": sample["prompt"].split(" Use a distinctly")[0]},
                               {"role": "assistant", "content": sample["reply"]}])
            rows = []
            for i, (statement, facts) in enumerate(EXAM[4:], start=5):
                ask = f"Write a one-sentence message to Sam confirming that {statement}. Include the day and place."
                out = ternary._post(cpu.url + "/v1/chat/completions", {
                    "messages": [*prefix, {"role": "user", "content": ask}], "max_tokens": 48, "temperature": 0.,
                    "seed": 1234, "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}})
                answer = out["choices"][0]["message"]["content"]
                rows.append(dict(case=i, reply=answer, usage=out["usage"], **markers(answer, facts)))
            results[style] = {"donor_prefix": prefix, "recipient_replies": rows}
    (args.out / "example-transfer.json").write_text(json.dumps(results, indent=2) + "\n")


def checked_style(reply, style, recipient, statement, facts):
    # Preserve the complete relationship. Presence of both an assignee and ticket
    # number permits reversing the assignment; it is insufficient for an action receipt.
    def words(text):
        return tuple(re.findall(r"\w+", text.casefold()))
    core = words(statement)
    wrappers = ("", "I confirm that", recipient, f"Dear {recipient}", f"Hey {recipient}", f"Hi {recipient}",
                f"Dear {recipient}, I confirm that")
    authorized = {words(prefix) + core for prefix in wrappers}
    def passes(text):
        measured = markers(text, facts)
        other = "casual" if style == "formal" else "formal"
        return (words(text) in authorized and measured["both_facts"] and measured["one_sentence"] and measured[style + "_marker"]
                and not measured[other + "_marker"])
    if style not in ("formal", "casual"):
        raise ValueError("unknown register")
    if passes(reply):
        return reply, False
    prefix = f"Dear {recipient}, I confirm that " if style == "formal" else f"Hey {recipient}, "
    rendered = prefix + statement.rstrip(".!?") + "."
    if not passes(rendered):
        raise ValueError("the provided record cannot supply the requested facts and register")
    return rendered, True


def verify_transfer(args):
    rows = json.loads((args.out / "new-topics.json").read_text())
    if len(rows) != 4 * len(TRANSFER_EXAM):
        raise ValueError("finish all transfer cases before measuring repair")
    results = []
    for row in rows:
        if row["arm"] not in ("positive12", "negative12"):
            continue
        index = row["case"] - 1
        style = "formal" if row["arm"] == "positive12" else "casual"
        facts = TRANSFER_EXAM[index][1]
        answer, fallback = checked_style(row["reply"], style, "Jo", STATEMENTS[index], facts)
        results.append(dict(case=index + 1, style=style, protected_statement=STATEMENTS[index], used_template=fallback,
                            original=row["reply"], final=answer, **markers(answer, facts)))
    (args.out / "verified-style.json").write_text(json.dumps(results, indent=2) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("extract", "grade", "score", "examples", "stress", "confirm", "verify"))
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
    elif args.stage in ("grade", "stress", "confirm"):
        if not args.binary:
            p.error("grading needs --binary")
        grade(args, stress=args.stage == "stress", confirm=args.stage == "confirm")
        if args.stage == "grade":
            portability(args)
    elif args.stage == "score":
        portability(args)
    elif args.stage == "verify":
        verify_transfer(args)
    else:
        if not args.binary:
            p.error("example transfer needs --binary")
        transfer_examples(args)


if __name__ == "__main__":
    main()
