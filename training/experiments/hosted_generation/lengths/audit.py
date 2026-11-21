"""Recover the full G58 length-filter population with the runner's actual row selection and tokenizer."""
import argparse
import ast
from collections import Counter
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
G58_ARTIFACT = "1ed79413eac8503636dfb10afd4592a6f1a68fe89cbc60a84927fde17e4f9e7d"
CAP = 1152


def digest(data):
    return hashlib.sha256(data).hexdigest()


def exchange(row):
    return digest(json.dumps([row["messages"][1:], row["output"], row.get("rejected")],
                             sort_keys=True, ensure_ascii=False).encode())


def collect(rows_path, child, parent, organ, shard):
    from training import grow

    class Captured(Exception):
        pass

    def at_weight_load(*args):
        caller = sys._getframe(1)
        assert caller.f_code == grow.train.__code__
        raise Captured(caller.f_locals["rows"])

    with mock.patch("huggingface_hub.snapshot_download", new=at_weight_load):
        try:
            grow.train(rows_path, child, base="t80", gen="g58", parent_cell=parent,
                       lean=organ, shard=shard, log=lambda *args, **kwargs: None)
        except Captured as captured:
            return captured.args[0]
    raise AssertionError("Trainer did not reach the expected weight-load boundary")


def training_encoder(tok):
    import torch
    from training import grow

    body = ast.parse(inspect.getsource(grow.train))
    nested, = [node for node in ast.walk(body) if isinstance(node, ast.FunctionDef) and node.name == "encode"]
    namespace = dict(tok=tok, torch=torch, shorten=grow.shorten)
    exec(compile(ast.Module(body=[nested], type_ignores=[]), grow.__file__, "exec"), namespace)
    return namespace["encode"]


def mark(rows, key):
    return dict(sorted(Counter(r[key] for r in rows).items()))


def summarize(rows):
    return dict(exchanges=len(rows), distinct_requests=len({r["question_sha256"] for r in rows}),
                slice_presentations=sum(len(r["jobs"]) for r in rows))


def run(args):
    from transformers import AutoTokenizer
    from training import grow

    assert grow.KEEP_BACK == 2
    archive = args.archive.read_bytes()
    assert digest(archive) == G58_ARTIFACT
    jobs = json.loads((Path(__file__).parents[1] / "g58.json").read_text())["training"]["slices"]
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    encode = training_encoder(tok)
    cache, excluded, per_slice = {}, {}, []
    with tempfile.TemporaryDirectory() as temp, zipfile.ZipFile(args.archive) as zipped:
        original = zipped.read("rows.jsonl")
        rows_path = Path(temp) / "rows.jsonl"
        rows_path.write_bytes(original)
        for job in jobs:
            child, _, organ, parent, part, width, _ = job["job"][7:-1].split(", ")
            rows = collect(rows_path, child, parent, organ, f"{part}/{width}")
            missing = 0
            for row in rows:
                key = exchange(row)
                cache_key = (key, row["messages"][0]["content"])
                if cache_key not in cache:
                    encoded = encode(row, CAP)
                    cache[cache_key] = None
                    if encoded is None:
                        raw, target = encode(row, 10**7)
                        cache[cache_key] = int(raw.shape[1]), target
                lengths = cache[cache_key]
                if lengths is None:
                    continue
                total, target = lengths
                missing += 1
                detail = dict(exchange_sha256=key, question_sha256=digest(row["task"].encode()),
                              kind=row.get("kind") or "?", type=row.get("type"), who=row.get("who"),
                              gen=row.get("gen"), seed=row.get("seed"), target=target,
                              full_tokens=total, prompt=total-target, jobs=[])
                if key in excluded:
                    assert all(excluded[key][k] == detail[k] for k in detail.keys() - {"jobs"})
                else:
                    excluded[key] = detail
                excluded[key]["jobs"].append(job["job_id"])
            assert missing == job["partial"]["too_long"], (job["job"], missing, job["partial"])
            per_slice.append(dict(job=job["job"], job_id=job["job_id"], selected=len(rows),
                                  excluded=missing, hosted_log=job["partial"]["too_long"]))
    rows = sorted(excluded.values(), key=lambda row: row["exchange_sha256"])
    result = dict(artifact_sha256=G58_ARTIFACT, rows_jsonl_sha256=digest(original),
                  training_source_sha256=digest(Path(grow.__file__).read_bytes()),
                  tokenizer={name: digest((args.tokenizer / name).read_bytes()) for name in
                             ["tokenizer.json", "tokenizer_config.json", "chat_template.jinja"]},
                  cap=CAP, total=summarize(rows), per_slice=per_slice,
                  by_kind={k: summarize([r for r in rows if r["kind"] == k]) for k in mark(rows, "kind")},
                  by_type={k: summarize([r for r in rows if r["type"] == k]) for k in mark(rows, "type")},
                  current_generation=summarize([r for r in rows if r["gen"] == "g58"]),
                  parent_mends=summarize([r for r in rows if r["type"] == "mend"]),
                  minimum_raw_tokens=min(r["full_tokens"] for r in rows),
                  maximum_raw_tokens=max(r["full_tokens"] for r in rows))
    args.summary.write_text(json.dumps(result, indent=2) + "\n")
    if args.rows:
        args.rows.write_text("".join(json.dumps(r) + "\n" for r in rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--rows", type=Path)
    os.environ.update(HIVE_KEEP_BACK="2", HIVE_SHARD_POLICY="hash", AGENT_TEAM_THREADS="2", HF_HUB_OFFLINE="1")
    run(parser.parse_args())
