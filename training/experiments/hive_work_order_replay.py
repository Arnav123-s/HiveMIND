"""Exercise the executable correction vocabulary in fresh durable work orders."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from training.experiments.hive_commitment_bench import recover
from training.experiments.hive_commitment_cases import cases
from training.experiments.hive_commitments import Journal, canonical, literal, replace
from training.experiments.hive_work_order_rules import interpret, learn_exchange


TRANSFER = (
    ("plain", "Set {other} to {x}.", "ABxd"),
    ("plain", "Would you reschedule {src} at {y}?", "Aycd"),
    ("tentative", "Someone proposed {x} for {other}. Please do not act on that.", "ABcd"),
    ("withdraw", "Roll back the entire revision.", "abcd"),
    ("recipient", "That change was misaddressed. Both adjustments were intended for {other}; {src} needs its old details.", "abAB"),
    ("copy", "Duplicate the pending adjustment onto {other}; leave {src} alone.", "ABAB"),
    ("partial", "Revert the day for {src}. Its updated venue is correct.", "aBcd"),
    ("split", "The venue change was intended for {other}. {src} still needs the new day.", "AbcB"),
    ("replace", "Undo what you did to {src}. Make {other} run on {x}.", "abxd"),
    ("two_edits", "{other} now uses {y}. As for {src}, assign {x}.", "xBcy"),
    ("relative", "Give {other} the calendar day following {src}; carry over the rest.", "ABnd"),
    ("swap", "Trade the venues between the two reservations. Neither day moves.", "AdcB"),
    ("ambiguous", "One booking must move to {x}; I can name it when you ask.", "xBcd"),
    ("ambiguous", "One booking must move to {x}; I can name it when you ask.", "ABxd"),
)
NEGATIVE = (
    "If there is parking, move {name} to Tuesday.",
    "Move {name} to Tuesday or Wednesday.",
    "Please ask the owner about Tuesday before changing anything.",
    "Never duplicate the last change.",
    "Change the time to noon.",
    "Move {name} from Monday to Tuesday only after the receipt arrives.",
    "Could you tell me how far the two venues are from each other?",
    "Keep the day tentative until the organizer replies.",
)


def teach_and_transfer():
    source = {"Pine": ["Friday", "East"], "Oak": ["Monday", "West"]}
    verified = {"Pine": ["Friday", "West"], "Oak": ["Monday", "East"]}
    demo = "Trade the sites between both entries."
    record = learn_exchange(demo, source, verified)
    phrases = (("Trade the dates of the two entries.", 0), ("Please trade both entries' sites.", 1),
               ("Trade the weekdays between the two pickups.", 0), ("Trade the two current places.", 1),
               ("Trade both days. Preserve the locations.", 0), ("Trade the locations between both bookings.", 1),
               ("Trade both dates if the owner approves.", None), ("Trade the two days or the two venues.", None),
               ("Trade the two sites. Move a third booking.", None), ("Trade one entry with a third item.", None))
    rows = []
    for case, (text, field) in zip(cases(), phrases):
        public = dict(case["public"], last=text)
        draft = literal(public["first"], public, public["opening"])
        a, b = public["names"]
        expected = None if field is None else replace(draft, [(a, field, draft[b][field]), (b, field, draft[a][field])])
        old = interpret(public, draft)
        new = interpret(public, draft, learned=record)
        rows.append(dict(text=text, field=field, before=old, after=new,
                         correct_before=old == (("defer", None) if expected is None else ("apply", expected)),
                         correct_after=new == (("defer", None) if expected is None else ("apply", expected))))
    return {"teaching_text": demo, "before": source, "checked_result": verified, "record": record, "transfer": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    db = args.out / "work-orders.sqlite"
    if db.exists():
        parser.error("use a fresh output directory")
    journal = Journal(db)
    rows = []
    for case in [*cases(), *cases((TRANSFER,), offset=2)]:
        task = case["case"]
        initial = dict(case["public"])
        latest = initial.pop("last")
        proc = subprocess.run([sys.executable, "-m", "training.experiments.hive_commitment_bench", "stage", str(db)],
                              input=canonical({"tasks": [task], "opening_context": initial}), text=True)
        if proc.returncode != 37:
            raise RuntimeError("worker did not reach its failure point")
        public, draft = recover(journal, task)
        public["last"] = latest
        action, result = interpret(public, draft)
        asked = action == "ask"
        if asked:
            action, result = interpret(public, draft, case["clarification"] or "I have no more details.")
        if action == "apply":
            journal.apply(task, "latest", 1, result)
            journal.apply(task, "latest", 1, result)
        _, rev, state = journal.read(task)
        complete = action == "apply" and state == case["expected"] and (asked or not case["clarification"])
        rows.append(dict(case, asked=asked, action=action, completed=bool(complete), final=state, revision=rev))
    negatives = []
    for t in NEGATIVE:
        statement = t.format(name=public["names"][0])
        action, result = interpret(dict(public, last=statement), draft)
        negatives.append(dict(text=statement, action=action, changed=action == "apply" and result != draft))
    learned = teach_and_transfer()
    missed = next(c for c in rows if c["cohort"] == 3 and c["kind"] == "swap")
    pub = missed["public"]
    retry = interpret(pub, literal(pub["first"], pub, pub["opening"]), learned=learned["record"])
    if retry[0] == "apply":
        journal.apply(missed["case"], "after-demonstration", missed["revision"], retry[1])
    learned["missed_case_after_teaching"] = journal.read(missed["case"])[2] == missed["expected"]
    requests = [(case["public"], literal(case["public"]["first"], case["public"], case["public"]["opening"]),
                 case["clarification"]) for case in rows]
    start = time.process_time_ns()
    repeats = 100
    for _ in range(repeats):
        for task_public, draft, reply in requests:
            if interpret(task_public, draft)[0] == "ask":
                interpret(task_public, draft, reply)
    cpu_us = (time.process_time_ns() - start) / (repeats * len(requests) * 1000)
    (args.out / "result.json").write_text(json.dumps({"cases": rows, "unsupported": negatives,
        "learned_exchange": learned, "warm_interpreter_cpu_us_per_request": cpu_us,
        "timed_requests": repeats * len(requests)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
