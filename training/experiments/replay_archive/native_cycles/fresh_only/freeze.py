"""Pin a verified, length-matched third fresh example and the ordinary sampler order."""
import argparse
import gzip
import json
import random
import re
from pathlib import Path

from team import solo
from training import grow, kinds, self_replay
from training.experiments.astra_cpu.five_kinds.recheck import verify
from training.experiments.replay_archive.native_cycles import pilot
from training.experiments.replay_archive.native_cycles.freeze import FAMILIES, digest, row_id

HERE = Path(__file__).resolve().parent


def lengths(tok, row):
    messages = list(row["messages"])
    day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))", messages[0]["content"]).group(1)
    messages[0] = {"role": "system", "content": solo.SHORT.format(today=day)}
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    n = len(tok(row["output"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"])
    return n, n + len(tok(prompt, add_special_tokens=False)["input_ids"])


def first_round(n, cycle):
    indices = list(range(n))
    # Study shuffles the first subject's list before creating any other queues.
    random.Random(f"56:sources:retention{cycle}").shuffle(indices)
    return indices


def freeze(archives, scratch):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(grow.UNPACKED["t80"], local_files_only=True)
    mixed = pilot.load(pilot.HERE / "manifest.json", pilot.MANIFEST_SHA)
    panel = pilot.load(pilot.HERE / "panel.json", pilot.PANEL_SHA)
    docs = []
    for g in ("g55", "g56"):
        file = archives / (g + "-rows.jsonl")
        assert digest(file.read_bytes()) == mixed["sources"][g]
        docs.append([json.loads(line) for line in file.read_text().splitlines()])
    previous, current = docs
    catalog = {row_id(row): row for rows in docs for row in rows}
    q = self_replay.question
    blocked = {q(row["task"]) for row in previous + panel["rows"]}
    assert grow.KEEP_BACK == 2
    blocked.update(q(task) for tasks in grow.kept_back(current).values() for task in tasks)
    for stage in mixed["stages"]:
        blocked.update(q(catalog[key]["task"]) for key in stage["fresh"] + [stage["replay"]])
    records = []
    payload = []
    for i, stage in enumerate(mixed["stages"], 1):
        family = stage["family"]
        assert family == FAMILIES[i-1] and family not in kinds.HELD_OUT
        common = [catalog[k] for k in stage["fresh"]]
        old = catalog[stage["replay"]]
        old_ans, old_total = lengths(tokenizer, old)
        options = []
        for row in current:
            if (row.get("gen"), row.get("type"), row.get("who"), row.get("lesson")) != ("g56","first","lesson",family):
                continue
            if q(row["task"]) in blocked:
                continue
            ans, total = lengths(tokenizer, row)
            if total <= 1152:
                options.append((abs(ans-old_ans), abs(total-old_total), row_id(row), row))
        rejected = []
        for _, _, key, row in sorted(options, key=lambda o: o[:3]):
            check = verify(row)
            if check["ok"]:
                break
            rejected.append(check)
        else:
            raise ValueError(f"No independent verified third example for {family}")
        blocked.add(q(row["task"]))
        common_order = first_round(2, i)
        order = [common[pos] for pos in common_order] + [row]
        layout = list(order)
        for seq, pos in enumerate(first_round(3, i)):
            layout[pos] = order[seq]
        blob = "".join(json.dumps(r) + "\n" for r in layout).encode()
        (scratch / f"rows-{i}.jsonl").write_bytes(blob)
        payload.append(layout)
        records.append(dict(family=family, replacement=key, replay=stage["replay"], eligible_rows=len(options),
                            skipped_verifications=rejected, source_verification=check, old_answer_total=[old_ans,old_total],
                            fresh_answer_total=lengths(tokenizer,row), shared_answer_total=[lengths(tokenizer,r) for r in order[:2]],
                            archived_distinct_output_texts=len({r["output"] for r in order}), input_sha256=digest(blob),
                            layout=[row_id(r) for r in layout], optimizer_order=[row_id(r) for r in order]))
    (HERE / "manifest.json").write_text(json.dumps(dict(mixed_manifest_sha256=pilot.MANIFEST_SHA, panel_sha256=pilot.PANEL_SHA,
                                corpus=mixed["sources"], stages=records), indent=2)+"\n")
    (HERE / "rows.json.gz").write_bytes(gzip.compress((json.dumps(payload, indent=2)+"\n").encode(), mtime=0))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    a = p.parse_args()
    a.scratch.mkdir(exist_ok=True, parents=True)
    freeze(a.archives, a.scratch)
