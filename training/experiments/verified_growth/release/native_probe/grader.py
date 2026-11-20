"""Grade fresh native replies, with and without publishing their explicitly requested files."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import random
import re
import signal
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from team.deliverables import wanted
from training import exam, kinds
from training.experiments.fieldwork.guest import Guest
from training.kinds import _programs
from training.kinds import h_module

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from score import hidden_in_guest

LANG = {"py": {"python", "py", "python3"}, "csv": {"csv"}, "tsv": {"tsv"}, "md": {"md", "markdown"},
        "json": {"json"}, "jsonl": {"jsonl", "ndjson"}, "ini": {"ini"}, "yaml": {"yaml", "yml"},
        "yml": {"yaml", "yml"}, "sql": {"sql"}, "html": {"html"}, "txt": {"txt", "text", "plain", "plaintext"}}
BASENAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_. -]{0,100}\.[A-Za-z0-9]+")
OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")
LABEL = re.compile(r"^(?:#{1,6}\s*|[-*]\s+)?(?:file(?:name)?\s*:\s*)?[`*]*(.+?)[`*]*:?\s*$", re.I)


def materialize(task, text):
    requested = list(dict.fromkeys(wanted(task)))
    if not requested:
        return {}, "no_requested_files"
    if any(not BASENAME.fullmatch(n) or n.rsplit(".", 1)[1].lower() not in LANG for n in requested):
        return {}, "unsupported_requested_file"
    lines = text.splitlines(keepends=True)
    blocks = []
    i = 0
    while i < len(lines):
        begin = OPEN.fullmatch(lines[i].rstrip("\r\n"))
        if not begin:
            i += 1
            continue
        marker, info = begin.groups()
        info = info.strip()
        previous = lines[i-1].strip() if i else ""
        start = i + 1
        i = start
        while i < len(lines) and not re.fullmatch(re.escape(marker[0]) + "{" + str(len(marker)) + r",}", lines[i].strip()):
            i += 1
        if i == len(lines):
            return {}, "unclosed_block"
        contents = "".join(lines[start:i])
        i += 1
        names = set()
        lang = info.lower()
        for name in requested:
            if info == name:
                names.add(name)
                lang = ""
            elif info.endswith(" " + name):
                names.add(name)
                lang = info[:-len(name)].strip().lower()
        label = LABEL.fullmatch(previous)
        if label and label[1] in requested:
            names.add(label[1])
        elif label and BASENAME.fullmatch(label[1]):
            return {}, "unrequested_label"
        if len(names) > 1:
            return {}, "conflicting_labels"
        blocks.append((next(iter(names), None), lang, contents))
    if not blocks:
        return {}, "no_fenced_block"
    produced = {}
    for label, lang, content in blocks:
        if label is None:
            if len(requested) != 1 or len(blocks) != 1 or not lang:
                return {}, "unclear_binding"
            label = requested[0]
        if lang and lang not in LANG[label.rsplit(".", 1)[1].lower()]:
            return {}, "unmatched_language"
        if label in produced:
            return {}, "duplicate_block"
        produced[label] = content
    if set(produced) != set(requested):
        return {}, "incomplete_file_set"
    return produced, "bound"


class GradeDeadline(BaseException):
    pass


@contextmanager
def deadline(seconds):
    def expired(*_):
        raise GradeDeadline("official checker timed out")
    original = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, original)


def check(question, text, products, sdk, seconds):
    import requests
    records = []
    original = requests.sessions.Session.request
    def bounded(session, method, url, **kwargs):
        kwargs["timeout"] = (3, 5)
        event = {"method": method, "url": str(url)}
        records.append(event)
        try:
            reply = original(session, method, url, **kwargs)
            event["status"] = reply.status_code
            return reply
        except requests.RequestException as exc:
            event["error"] = type(exc).__name__
            raise

    def disallow(*_, **__):
        raise RuntimeError("unsupported host execution in a grading function")

    guest = Guest(sdk)
    def legacy_hidden(path, functions, seed, n=25, timeout=20):
        rng = random.Random(f"hidden:{seed}")
        steps = [(name, args, json.loads(json.dumps(reference(*args)))) for name, _, reference, draw in functions
                 for args in (draw(rng) for _ in range(n))]
        return hidden_in_guest(guest, path, [{"new": None, "steps": steps}])
    try:
        with TemporaryDirectory() as folder, deadline(seconds):
            run = Path(folder)
            work = run / "work"
            work.mkdir()
            for name, contents in products.items():
                assert BASENAME.fullmatch(name)
                (work / name).write_text(contents, encoding="utf-8")
            (run / "REPORT.md").write_text(text, encoding="utf-8")
            # The program-family checker creates its operations in the trusted host and runs the submitted source in WASI.
            # The two-function checker likewise uses its official deterministic draws, with guest-side calls.
            with (patch.object(_programs, "hidden", lambda path, scenarios, **kwargs: hidden_in_guest(guest, path, scenarios)),
                  patch.object(h_module, "_hidden", legacy_hidden), patch.object(h_module, "_load", disallow),
                  patch.object(requests.sessions.Session, "request", bounded)):
                okay, why = question[-1](run, text)
    except (Exception, GradeDeadline) as exc:
        return {"passed": None, "reason": f"{type(exc).__name__}: {exc}", "network": records}
    failed_fetch = any("error" in event or event.get("status", 599) >= 400 for event in records)
    return {"passed": None if failed_fetch else bool(okay), "reason": str(why), "network": records}


def grade_case(question, raw_text, sdk, timeout_seconds=45):
    task = question[-2]
    files, binding = materialize(task, raw_text)
    plain = check(question, raw_text, {}, sdk, timeout_seconds)
    delivered = check(question, raw_text, files, sdk, timeout_seconds) if files else plain
    return {"requested": wanted(task), "binding": binding, "plain": plain, "delivered": delivered,
            "same_submission": not files, "products": {n: {"bytes": len(s.encode()), "sha256": hashlib.sha256(s.encode()).hexdigest()}
            for n, s in files.items()}}


def bundle(rows, sdk):
    results = []
    for row in rows:
        maker = kinds.get(row["maker"]).make
        question = exam._made(maker, row["seed"], row.get("level", 0))
        if question[-2] != row["task"]:
            raise ValueError(f"regenerated request differs from frozen request for {row['id']}")
        got = grade_case(question, row["raw"], sdk)
        results.append({"id": row["id"], "maker": row["maker"], **got})
    return {"grader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "rows": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_bytes())
    results = bundle(data if isinstance(data, list) else data["rows"], args.sdk)
    args.out.write_text(json.dumps(results, indent=2) + "\n")
