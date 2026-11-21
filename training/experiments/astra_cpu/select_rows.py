"""Freeze two answer lengths before inspecting trained output; use only current-generation, non-held rows."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from team import solo
from training import grow
from transformers import AutoTokenizer


def digest(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive_rows", type=Path)
    ap.add_argument("tokenizer")
    ap.add_argument("out", type=Path)
    ap.add_argument("--overcap",action="store_true",help="separate static-cap challenge with an 820-token target")
    args = ap.parse_args()
    raw = args.archive_rows.read_bytes()
    all_rows = [json.loads(line) for line in raw.splitlines()]
    held = {task for tasks in grow.kept_back(all_rows,n=2).values() for task in tasks}
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    pool = []
    for row in all_rows:
        if row.get("gen")!="g56" or row.get("type")!="first" or row.get("task") in held:
            continue
        old = row["messages"][0]["content"]
        day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))",old)
        if not day:
            continue
        sys_message = dict(role="system",content=solo.SHORT.format(today=day[1]))
        p = tok.apply_chat_template([sys_message,*row["messages"][1:]], tokenize=False,add_generation_prompt=True,enable_thinking=False)
        prompt = len(tok(p,add_special_tokens=False)["input_ids"])
        answer = len(tok(row["output"]+"<|im_end|>\n",add_special_tokens=False)["input_ids"])
        ident = digest(json.dumps(row,sort_keys=True).encode())
        pool.append((row,prompt+answer,answer,ident))
    chosen = []
    choices = [("overcap",820,220,12)] if args.overcap else [("short",300,32,1),("long",475,380,128)]
    for size,target,max_ans,min_ans in choices:
        source, total, n, ident = min((r for r in pool if min_ans <= r[2] <= max_ans),
                                      key=lambda r:(abs(r[1]-target),r[3]))
        chosen.append(dict(size=size,target=target,task=source["task"],kind=source["kind"],who=source["who"],
                           full_tokens=total,answer_tokens=n,row_sha256=ident))
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/(size+".json")).write_text(json.dumps(source)+"\n")
    (args.out/"rows.jsonl").write_text("".join((args.out/(s["size"]+".json")).read_text() for s in chosen))
    print(json.dumps(dict(archive_rows_sha256=digest(raw),excluded_held_tasks=len(held),rows=chosen),indent=2))


if __name__=="__main__":
    main()
