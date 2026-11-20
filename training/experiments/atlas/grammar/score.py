"""Apply the independent frozen grader after both native arms return."""
import argparse
import json
from pathlib import Path
from .oracle import grade
from .run import HERE, sha, write


def evaluate(home):
    panel = json.loads((HERE/'panel.json').read_bytes())
    keys = json.loads((HERE/'answers.json').read_bytes())
    records = json.loads((home/'pairs.json').read_bytes())
    environment = json.loads((home/'environment.json').read_bytes())
    if (environment['panel_sha256'] != sha(HERE/'panel.json') or
            [r['id'] for r in panel] != [r['id'] for r in records] or set(keys) != {row['id'] for row in panel}):
        raise ValueError('incomplete or mismatched panel')
    totals = {a:dict(format_ok=0,content_ok=0,joint=0,cpu_seconds=0,wall_seconds=0,predicted_tokens=0,prompt_tokens=0)
              for a in ('free','grammar')}
    per_case = []
    for row, pair in zip(panel,records,strict=True):
        scored = {}
        for arm in totals:
            observed=pair['arms'][arm]
            judged=grade(row,keys[row['id']],observed['raw'])
            scored[arm] = {**judged, 'joint':judged['format_ok'] and judged['content_ok']}
            for key in ('format_ok','content_ok','joint'):
                totals[arm][key]+=int(scored[arm][key])
            for key in ('cpu_seconds','predicted_tokens','prompt_tokens'):
                totals[arm][key]+=observed[key]
            totals[arm]['wall_seconds']+=observed['seconds']
        per_case.append(dict(id=row['id'],expected=keys[row['id']],**scored))
    trades={}
    for key in ('format_ok','content_ok','joint'):
        trades[key]={
            'gained':[r['id'] for r in per_case if r['grammar'][key] and not r['free'][key]],
            'lost':[r['id'] for r in per_case if r['free'][key] and not r['grammar'][key]],
        }
    for vals in totals.values():
        for key in ('cpu_seconds','wall_seconds'):
            vals[key]=round(vals[key],3)
    return dict(count=len(records),totals=totals,trades=trades,cases=per_case,panel_sha256=sha(HERE/'panel.json'),
                answers_sha256=sha(HERE/'answers.json'),oracle_sha256=sha(HERE/'oracle.py'),pair_sha256=sha(home/'pairs.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('receipts',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); result=evaluate(a.receipts); write(a.out,result)
    print(json.dumps(result['totals'],indent=2))
