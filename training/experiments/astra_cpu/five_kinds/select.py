"""Choose the five archived solutions by the frozen, model-blind selection rule."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
from team import solo
from training import grow
from transformers import AutoTokenizer

KINDS = ('bank','calc','lru','machine','schedule')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('archive',type=Path)
    ap.add_argument('snapshot')
    ap.add_argument('out',type=Path)
    args=ap.parse_args()
    assert hashlib.sha256(args.archive.read_bytes()).hexdigest()=='a7738ee21886d9ca1d1b24cc59c2cd489ccfde6cbaee079648cc630e66a94139'
    rows=[json.loads(line) for line in args.archive.read_text().splitlines()]
    held={task for tasks in grow.kept_back(rows,n=2).values() for task in tasks}
    tok=AutoTokenizer.from_pretrained(args.snapshot)
    pool=[]
    for row in rows:
        kind=row.get('lesson','').removeprefix('h_prog_')
        if kind not in KINDS or row.get('who')!='lesson' or row['type']!='first' or row['task'] in held:
            continue
        if not re.fullmatch(r'g[0-9]+',row.get('gen') or ''):
            continue
        if row['gen']!='g56' and not grow.slice_rows([row],0,2):
            continue
        date=re.search(r'Today is (\d{4}-\d\d-\d\d \(\w+\))',row['messages'][0]['content'])
        if not date:
            continue
        sy=dict(role='system',content=solo.SHORT.format(today=date[1]))
        text=tok.apply_chat_template([sy,*row['messages'][1:]],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        prompt=len(tok(text,add_special_tokens=False)['input_ids'])
        answer=len(tok(row['output']+'<|im_end|>\n',add_special_tokens=False)['input_ids'])
        if prompt+answer>1152:continue
        sha=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
        pool.append(dict(kind=kind,gen=row['gen'],seed=row['seed'],prompt=prompt,answer=answer,total=prompt+answer,
                         sha256=sha,task_sha256=hashlib.sha256(row['task'].encode()).hexdigest(),row=row))
    assert all(any(r['kind']==k for r in pool) for k in KINDS)
    longest=[r for r in pool if r['total']>527]
    anchor=min(longest,key=lambda r:(-int(r['gen'][1:]),r['total'],r['sha256'])) if longest else None
    chosen=[anchor if anchor and anchor['kind']==k else min((r for r in pool if r['kind']==k),key=lambda r:(-int(r['gen'][1:]),r['sha256'])) for k in KINDS]
    args.out.mkdir(parents=True,exist_ok=True)
    data=''.join(json.dumps(r['row'])+'\n' for r in chosen).encode()
    (args.out/'panel.jsonl.gz').write_bytes(gzip.compress(data,mtime=0))
    report=dict(rows_sha256=hashlib.sha256(data).hexdigest(),held_tasks_excluded=len(held),
                eligible_per_kind={k:sum(r['kind']==k for r in pool) for k in KINDS},
                anchor=anchor['kind'] if anchor else None,overcap_candidates=len(longest),
                rows=[{k:v for k,v in r.items() if k!='row'} for r in chosen])
    (args.out/'selection.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
