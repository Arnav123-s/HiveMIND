"""Score answer format, unambiguous numeric content, and routing separately."""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PREFIX = re.compile(r"^(?:(?:the |my )?(?:answer|choice)(?: is)?\s*[:=]?\s*|(?:option|choice)\s+)", re.I)


def extract(text, fmt):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    line = lines[0].replace("**", "").replace("`", "").strip()
    line = PREFIX.sub("", line).lstrip("(").strip()
    if fmt == "letter":
        match = re.match(r"([a-c])(?=\s*$|[.:,)\-–—]|\s+[-–—])", line, re.I)
        return match[1].upper() if match else None
    match = re.match(r"([-+]?\d+)(?=$|\s|[.,)](?!\d)|°)", line)
    return int(match[1]) if match else None


def numeric_content(text):
    # Secondary measure: a single whole-valued quantity, with no competing value anywhere.
    tokens = re.findall(r"(?<![\w.])[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?", text)
    values = {Decimal(t) for t in tokens}
    if len(values) == 1:
        value = values.pop()
        if value == value.to_integral_value() and abs(value) < 10**12:
            return int(value)
    return None


def worker_results(directory):
    members = []
    for path in sorted((directory / "work/members").glob("member[0-9]*.json")):
        row = json.loads(path.read_text())
        members.append({k: row.get(k) for k in ("who", "answer", "program", "turns", "also")})
    return members


def grade(root, arms, partial=False):
    panel = json.loads((HERE / "panel.json").read_text())
    keys = json.loads((HERE / "keys.json").read_text())
    all_rows, metrics = [], {}
    for arm in arms:
        counts = Counter()
        for task in panel:
            directory = root / arm / task["id"]
            path = directory / "reply.json"
            if not path.exists() and partial:
                continue
            row = json.loads(path.read_text())
            key, phase = keys[task["id"]], task["stratum"]
            text = row.get("text", "")
            parsed = extract(text, key["format"])
            confirmed = not row.get("error") and (not row.get("worked") or row.get("agreed") is True)
            correct = bool(confirmed and parsed == key["answer"])
            content = parsed if parsed is not None or key["format"] != "integer" else numeric_content(text)
            content_correct = bool(confirmed and content == key["answer"])
            recorded_route = directory / "route.json"
            signal = (json.loads(recorded_route.read_text()) if recorded_route.exists() else row.get("domain_signal")) or {}
            domain = signal.get("domain") if isinstance(signal, dict) else signal
            calls = row.get("model_calls")
            if calls is None:
                log = directory / "calls.jsonl"
                calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            counts[f"{phase}_answered"] += correct
            counts[f"{phase}_content_correct"] += content_correct
            counts[f"{phase}_total"] += 1
            recorded_advice = directory / "advice.json"
            advice = (json.loads(recorded_advice.read_text()) if recorded_advice.exists() else row.get("engram_advice")) or {}
            counts["advice_accepted"] += bool(advice.get("accepted"))
            counts["advice_consulted"] += bool(advice)
            counts["correct_route"] += bool(domain == task["domain"])
            counts["reported_route"] += bool(domain)
            started_work = (directory / "work").is_dir()
            timed_out = "timed out" in (row.get("error") or "")
            counts["work_started"] += started_work
            counts["timeout"] += timed_out
            counts["unconfirmed_work"] += bool(row.get("worked") and not confirmed)
            counts["error"] += bool(row.get("error"))
            counts["work"] += bool(row.get("worked"))
            counts["elapsed_ms"] += round((row.get("seconds") or 0) * 1000)
            counts["completed_native_calls_observed"] += len(calls)
            counts["observed_completion_tokens"] += sum((call.get("used") or {}).get("completion_tokens", 0) for call in calls)
            counts["questions_with_engram_requested"] += any(c.get("active_cell") and c["active_cell"][1] for c in calls)
            counts["questions_with_native_engram"] += any(
                any(name.startswith("e") for name in c.get("native_active", {})) for c in calls)
            members = worker_results(directory)
            for member in members:
                answer = member.get("answer") or ""
                parsed_member = extract(answer, key["format"])
                if parsed_member is None and key["format"] == "integer":
                    parsed_member = numeric_content(answer)
                member["content_correct"] = parsed_member == key["answer"]
            counts["jobs_with_observed_member_answers"] += bool(members)
            counts["member_correct_but_content_not_delivered"] += (
                not content_correct and any(m["content_correct"] for m in members))
            all_rows.append(dict(arm=arm, id=task["id"], expected_domain=task["domain"], stratum=phase,
                                 expected=key["answer"], parsed=parsed, correct=correct, content_correct=content_correct,
                                 engram_advice=advice,
                                 work_started=started_work, timeout=timed_out, worked=row.get("worked"),
                                 agreed=row.get("agreed"), domain_decision=signal,
                                 seconds=row.get("seconds"), error=row.get("error"), text=row.get("text"), model_calls=calls,
                                 members=members, **({"cache_lines": row["cache_lines"]} if "cache_lines" in row else {})))
        metrics[arm] = dict(counts)
    paired = None
    if len(arms) >= 2:
        a = {r["id"]: r["correct"] for r in all_rows if r["arm"] == arms[0]}
        b = {r["id"]: r["correct"] for r in all_rows if r["arm"] == arms[1]}
        labels = {"gain": (False, True), "loss": (True, False), "both": (True, True), "neither": (False, False)}
        paired = {name: sorted(i for i in a.keys() & b.keys() if (a[i], b[i]) == pair) for name, pair in labels.items()}
    by_domain = {}
    for row in all_rows:
        if row["stratum"] != "primary":
            continue
        stats = by_domain.setdefault(row["arm"], {}).setdefault(row["expected_domain"], Counter())
        stats["total"] += 1
        stats["strict"] += row["correct"]
        stats["content"] += row["content_correct"]
        stats["correct_domain"] += bool(row["domain_decision"] and row["domain_decision"].get("domain") == row["expected_domain"])
    return dict(metrics=metrics, primary_by_domain=by_domain, paired=paired, rows=all_rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("arms", nargs="+")
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = grade(args.root, args.arms, args.partial)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    else:
        print(json.dumps({"metrics": result["metrics"], "paired": result["paired"]}, indent=2))
