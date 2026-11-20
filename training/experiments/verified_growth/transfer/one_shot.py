"""Use exactly one external worked example, then score the same untouched target tables."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]))
from training.experiments.verified_growth.composer import qualification
from training.experiments.verified_growth.transfer.score import equal, EXTRAS
from training.experiments.verified_growth.transfer.teacher import make_teachers


def run(fixtures, teacher_path, native_path):
    assert sha256(Path(qualification.__file__).read_bytes()).hexdigest()=='402d5ab01725e4f904f67fdf45832a1f147a35e4639928afb9fefd801c783772'
    teachers=json.loads(teacher_path.read_bytes())
    assert teachers==make_teachers(HERE/'manifest.sha256')
    cases=json.loads((fixtures/'requests.json').read_bytes())
    tables=json.loads((fixtures/'tables.json').read_bytes())
    codes={r['id']:r['code'] for r in map(json.loads,native_path.read_text().splitlines())}
    assert len(codes)==len(cases)
    pending=[]
    for case in cases:
        tid=case['id']
        demo=next((v for v in teachers.values() if tid in v['answers']),None)
        if demo is None:
            assert case['pattern']=='clarify'  # No external answer exists.
            continue
        for mode in qualification.ARMS:
            outcomes=[]
            for table in case['tables']:
                rows=tables[table]['rows']
                assert rows!=demo['rows']
                r=qualification.qualify(case['request'],demo['rows'],demo['answers'][tid],rows,mode,codes[tid])
                outcomes.append(dict(table=table,**r))
            pending.append(dict(id=tid,pattern=case['pattern'],arm=mode,demo_value=demo['answers'][tid],outputs=outcomes))
    keys=json.loads((fixtures/'keys.json').read_bytes())  # All model and program choices are materialized above.
    result={}
    for row in pending:
        statuses=[]
        for output in row['outputs']:
            expected=keys[row['id']+'/'+output['table']]['value']
            statuses.append('missed' if output['status']=='abstained' else
                            'correct' if output['status']=='answered' and equal(output['value'],expected) else 'wrong')
        row['edition_verdicts']=statuses
        row['paired']='correct' if statuses==['correct','correct'] else ('wrong' if 'wrong' in statuses else 'missed')
    for mode in qualification.ARMS:
        relevant=[r for r in pending if r['arm']==mode]
        groups={}
        for p in sorted({r['pattern'] for r in relevant}):
            items=[r for r in relevant if r['pattern']==p]
            groups[p]=dict(Counter(r['paired'] for r in items))
        primary=[r for r in relevant if r['pattern'] not in EXTRAS]
        result[mode]=dict(primary=dict(Counter(r['paired'] for r in primary)),
                          mastered_patterns=[p for p,v in groups.items() if p not in EXTRAS and v.get('correct')==3],
                          primary_editions=dict(Counter(s for r in primary for s in r['edition_verdicts'])),
                          groups=groups)
    return {'teacher_sha256':sha256(teacher_path.read_bytes()).hexdigest(),'summary':result,'rows':pending}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures',type=Path,default=HERE/'panel')
    p.add_argument('--teacher',type=Path,default=HERE/'teacher.json')
    p.add_argument('--native',type=Path,default=HERE/'native.jsonl')
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    r=run(args.fixtures,args.teacher,args.native)
    args.out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    for arm,v in r['summary'].items():
        print(arm,v['primary'],v['mastered_patterns'])
