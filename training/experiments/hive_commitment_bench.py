"""Run a local conversation-to-action trial with a failed worker and a fresh successor."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from training.experiments.hive_commitments import Conflict, DAYS, Journal, canonical, literal, proposals, valid_rows


def save_stage(path):
    request = json.load(sys.stdin)
    journal = Journal(path)
    public = request["opening_context"]
    rows = literal(public["first"], public, public["opening"])
    if rows is None:
        raise ValueError("first request requires an explicit day and site")
    for task in request["tasks"]:
        journal.create(task, public)
        journal.apply(task, "first", 0, rows)
    # Simulate worker process loss after disk commit and before acknowledging its work.
    os._exit(37)


def recover(journal, task):
    context, rev, draft = journal.read(task)
    expected = literal(context["first"], context, context["opening"])
    if journal.apply(task, "first", 0, expected) != 1 or rev != 1 or draft != expected:
        raise RuntimeError("first write did not survive its worker")
    return context, draft


def prompt(public, draft, menu, followup, constrained=False):
    names = public["names"]
    action = ('Return {"pick":n} to run one numbered operation, or {"other":true} if none exactly fits.'
              if menu is not None else
              'Return {"rows":[["day","site"],["day","site"]]} with both final rows in the displayed item order.')
    system = ("You finish local work orders. Honor the user's latest decision, preserving every unaffected field. "
              + action + ' If the instruction leaves the target ambiguous, return {"ask":"Which item ...?"}. '
              "Use a single JSON object.")
    if constrained:
        format_rule = ("Choose the numbered operation that exactly carries out the latest request. "
                       "Choose other if the list is missing the right operation." if menu is not None else
                       "Write the final weekday and site for each item in the stated item order. "
                       "Copy the actual names of days and sites from the work order.")
        system = ("You are resuming a colleague's work order. Read the latest request carefully. " + format_rule
                  + " Ask which item only if the user has left the choice unresolved. Return your decision as JSON.")
    plan = "\n".join(f"{n}: opening {', '.join(public['opening'][n])} | draft {', '.join(draft[n])}" for n in names)
    user = (f"Work order: two {public['domain']} entries. Item order: {', '.join(names)}.\n"
            f"Sites: {', '.join(public['sites'])}. Days: {', '.join(DAYS)}.\n{plan}\n"
            f"Earlier user message: {public['first']}\nThat change was recorded in the draft.\n"
            f"Latest user message: {public['last']}")
    if followup:
        user += f"\nYour question: {followup[0]}\nUser's reply: {followup[1]}"
    if menu is not None:
        user += "\nAvailable operations:\n" + "\n".join(f"{i+1}. {label}" for i, (label, _) in enumerate(menu))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def decision_schema(public, menu):
    def field(key, schema):
        return {"type": "object", "properties": {key: schema}, "required": [key], "additionalProperties": False}
    ask = field("ask", {"const": "Which item do you mean?"})
    if menu is not None:
        return {"oneOf": [field("pick", {"enum": list(range(1, len(menu) + 1))}), field("other", {"const": True}), ask]}
    pair = {"type": "array", "prefixItems": [{"enum": list(DAYS)}, {"enum": public["sites"]}],
            "minItems": 2, "maxItems": 2}
    return {"oneOf": [field("rows", {"type": "array", "items": pair, "minItems": 2, "maxItems": 2}), ask]}


def parse(text, public, menu):
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return "invalid", None
    if not isinstance(obj, dict) or len(obj) != 1:
        return "invalid", None
    question = obj.get("ask")
    if isinstance(question, str) and question.strip():
        return "ask", question
    if menu is not None:
        idx = obj.get("pick")
        if type(idx) is int and 1 <= idx <= len(menu):
            return "apply", menu[idx - 1][1]
        return ("other", None) if obj.get("other") is True else ("invalid", None)
    rows = obj.get("rows")
    if isinstance(rows, list) and len(rows) == len(public["names"]):
        rows = dict(zip(public["names"], rows))
        if all(isinstance(r, list) and all(isinstance(v, str) for v in r) for r in rows.values()):
            rows = {k: [v.strip().title() for v in r] for k, r in rows.items()}
            if valid_rows(public, rows):
                return "apply", rows
    return "invalid", None


def ask_identifies_target(question, names):
    named = all(re.search(rf"\b{re.escape(n)}\b", question, re.I) for n in names)
    return named or bool(re.search(r"\b(which|what)\b.*\b(one|item|entry|record|meeting|pickup|name|label|target)\b", question, re.I))


def decide(public, draft, mode, ask_user, query, constrained=False):
    menu = proposals(public, draft) if mode == "menu" else None
    calls, followup = [], None
    for _ in range(3):
        row = query(prompt(public, draft, menu, followup, constrained), decision_schema(public, menu) if constrained else None)
        action, obj = parse(row["text"], public, menu)
        calls.append(dict(decoder="menu" if menu is not None else "rows", action=action, **row))
        if action == "apply":
            return obj, calls
        if action == "ask" and followup is None:
            followup = obj, ask_user(obj)
        elif menu is not None and action in ("other", "invalid"):
            menu = None
        else:
            break
    return None, calls


def run_case(case, public, draft, mode, query, constrained=False):
    supplied = []
    def ask_user(question):
        specific = ask_identifies_target(question, public["names"])
        supplied.append(specific)
        if specific and case["clarification"]:
            return case["clarification"]
        return "The previous message has all the details I can confirm."

    result, calls = decide(public, draft, mode, ask_user, query, constrained)
    matched = result == case["expected"]
    consent = not case["clarification"] or any(supplied)
    return {"result": result, "calls": calls, "state_correct": matched,
            "completed": bool(matched and consent), "asked": bool(supplied), "target_asked": any(supplied)}


def main():
    from team import ternary
    from training.experiments.hive_commitment_cases import cases
    from training.experiments.rule_lab_cpu import serving

    p = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "base", "catalog", "out"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--cell", default="t80+g41words")
    p.add_argument("--constrained", action="store_true")
    p.add_argument("--cohorts", type=int, nargs="+", choices=(1, 2), default=[1, 2])
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    db = args.out / "sandbox.sqlite"
    if db.exists():
        p.error("use a fresh output directory")
    journal = Journal(db)
    with serving(args.binary, args.base, args.catalog, args.out / "logs", slots=1, threads=4, flash=True) as cpu:
        cpu.activate(args.cell)

        def query(messages, schema):
            start = time.perf_counter()
            fmt = {"type": "json_object"} if schema is None else {"type": "json_object", "schema": schema}
            reply = ternary._post(cpu.url + "/v1/chat/completions", {
                "messages": messages, "max_tokens": 90, "temperature": 0., "seed": 1234,
                "cache_prompt": False, "response_format": fmt,
                "chat_template_kwargs": {"enable_thinking": False}}, timeout=180)
            return {"text": reply["choices"][0]["message"]["content"], "usage": reply["usage"],
                    "timings": reply["timings"], "seconds": time.perf_counter() - start}

        for i, case in enumerate(cases()):
            if case["cohort"] not in args.cohorts:
                continue
            modes = ["full", "menu"] if i % 2 == 0 else ["menu", "full"]
            initial = dict(case["public"])
            last = initial.pop("last")
            tasks = [case["case"] + "/" + mode for mode in modes]
            proc = subprocess.run([sys.executable, "-m", __spec__.name, "stage", str(db)],
                                  input=canonical({"tasks": tasks, "opening_context": initial}), text=True)
            if proc.returncode != 37:
                raise RuntimeError(f"stage worker exit {proc.returncode}")
            results = {}
            for mode, task in zip(modes, tasks):
                public, draft = recover(journal, task)
                public["last"] = last
                row = run_case(case, public, draft, mode, query, args.constrained)
                if row["result"] is not None:
                    journal.apply(task, "latest", 1, row["result"])
                    journal.apply(task, "latest", 1, row["result"])
                journal.apply(task, "first", 0, draft)
                try:
                    journal.apply(task, "late-writer", 0, public["opening"])
                except Conflict:
                    pass
                else:
                    raise RuntimeError("stale writer succeeded")
                _, revision, final_rows = journal.read(task)
                count = journal.db.execute("SELECT COUNT(*) FROM receipts WHERE task=?", (task,)).fetchone()[0]
                if (revision != count or count != 1 + int(row["result"] is not None)
                        or final_rows != (row["result"] or draft)):
                    raise RuntimeError("durable state or receipt mismatch")
                results[mode] = dict(row, receipts=count)
            states = proposals(public, draft)
            fast = literal(last, public, draft)
            record = dict(case, runs=results, constrained=args.constrained, draft=draft, literal=fast, menu_size=len(states),
                          oracle_menu_contains=any(value == case["expected"] for _, value in states),
                          failed_worker_exit=proc.returncode)
            with (args.out / "cases.jsonl").open("a") as f:
                f.write(canonical(record) + "\n")
            print(case["case"], case["kind"], {k: v["completed"] for k, v in results.items()}, flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "stage":
        save_stage(sys.argv[2])
    else:
        main()
