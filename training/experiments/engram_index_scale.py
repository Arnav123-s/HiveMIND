"""Replay the old and new lexical recall against real JSONL catalogs and file-existence checks."""
import argparse
import json
import os
import tempfile
import time
import tracemalloc
from pathlib import Path
from unittest.mock import patch

from team import engram, memory, ternary


TOPICS = ("calendar", "invoice", "shipment", "meter", "booking", "balance", "inventory", "document")
VERBS = ("review", "reconcile", "compare", "validate")


def old_recall(task, base, most=2, least=0.34):
    mine, out = memory.words(task), []
    for row in engram.index():
        theirs = memory.words(row.get("task", ""))
        score = len(mine & theirs) / max(1, len(mine | theirs))
        if (row.get("dna") == base and score >= least and row.get("task") != task
                and (ternary.ENGRAMS / f"{base}+{row['name']}.gguf").exists()):
            out.append((score, row["name"]))
    return [name for _, name in sorted(out, reverse=True)[:most]]


def record(i):
    topic, verb = TOPICS[i % len(TOPICS)], VERBS[i // len(TOPICS) % len(VERBS)]
    return dict(name=f"e{i:05d}", dna="t17" if i % 7 else "other",
                task=f"{verb} {topic} records for district{i % 13} code{i:05d}")


def queries(n):
    result = []
    for k in range(12):
        i = (1 + 331 * k) % n
        data = record(i)
        verb, topic = data["task"].split()[:2]
        result += [("specific", f"{topic} district{i % 13} code{i:05d}", data["dna"]),
                   ("common", f"{verb} {topic} records", data["dna"]),
                   ("absent", f"photosynthesis dragonfruit unknown{k}", data["dna"])]
    return result


def time_queries(fun, bank):
    timings, answers = {}, []
    for kind, query, base in bank:
        start = time.process_time_ns()
        answers.append(fun(query, base))
        timings.setdefault(kind, []).append(time.process_time_ns() - start)
    return timings, answers


def benchmark(size, root):
    entries, bank = [record(i) for i in range(size)], queries(size)
    path = root / "index.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in entries))
    for row in entries:
        (root / f"{row['dna']}+{row['name']}.gguf").touch()
    with patch.object(ternary, "ENGRAMS", root):
        engram._catalog.cache_clear()
        start = time.process_time_ns()
        engram.recall(bank[0][1], bank[0][2])
        cold_ns = time.process_time_ns() - start
        old, new = {}, {}
        equal = 0
        for repeat in range(3):
            methods = [(old_recall, old), (engram.recall, new)]
            answers = []
            for fun, target in (methods if repeat % 2 == 0 else methods[::-1]):
                times, answered = time_queries(fun, bank)
                answers.append(answered)
                for kind, values in times.items():
                    target.setdefault(kind, []).extend(values)
            if answers[0] != answers[1]:
                raise AssertionError("recall ranking drifted")
            equal += len(bank)
        appended = dict(dna="t17", name="late", task="reconcile extra requisitions")
        (root / "t17+late.gguf").touch()
        with path.open("a") as out:
            out.write(json.dumps(appended) + "\n")
        start = time.process_time_ns()
        visible = engram.recall("extra requisitions today", "t17")
        refresh_ns = time.process_time_ns() - start
        if visible != ["late"]:
            raise AssertionError("appended engram is missing")
        engram._catalog.cache_clear()
        tracemalloc.start()
        engram.recall("extra requisitions today", "t17")
        resident, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return dict(identical_answers=equal, cold_ns=cold_ns, refresh_ns=refresh_ns, file_bytes=path.stat().st_size,
                allocated_bytes_after_build=resident, peak_allocated_bytes=peak, original_ns=old, indexed_ns=new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    data = {}
    for n in (8, 32, 128, 1024, 4096):
        with tempfile.TemporaryDirectory() as temp:
            data[n] = benchmark(n, Path(temp))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
