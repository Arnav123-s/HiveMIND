"""After scoring only, give the binder the intended operation code and compute selector ceilings."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]))
from training.experiments.verified_growth.composer import solver
from training.experiments.verified_growth.transfer.score import equal, EXTRAS


def intended(kind, ident):
    if kind=='filtered-sum':
        return 'SP'
    if kind=='grouped-count':
        return 'CG'
    if kind=='filtered-group-sum':
        return 'SG'
    if kind in {'rank-group-count','filtered-rank-count','filtered-rank-sum'}:
        low={'gca_h','fgca_o','fgca_c','fgsa_h'}
        return ('S' if kind=='filtered-rank-sum' else 'C') + ('L' if ident in low else 'H')
    raise ValueError(kind)


def examine(fixtures, grades, native):
    panel=json.loads((fixtures/'requests.json').read_bytes())
    tables=json.loads((fixtures/'tables.json').read_bytes())
    keys=json.loads((fixtures/'keys.json').read_bytes())
    outcomes=json.loads(grades.read_bytes())['outcomes']
    codes={r['id']:r['code'] for r in map(json.loads,native.read_text().splitlines())}
    rows=[]
    for item in panel:
        tid,kind=item['id'],item['pattern']
        if kind in EXTRAS:
            continue
        expected_code=intended(kind,tid)
        arms=[r['arm'] for r in outcomes if r['id']==tid and r['paired']=='correct']
        receipts=[]
        for name in item['tables']:
            result=solver.run_files(item['request'],{f'{name}.csv':tables[name]['csv']},'native',expected_code)
            key=keys[tid+'/'+name]['value']
            receipts.append({'table':name,'status':result['status'],'value':result.get('value'),'expected':key,
                             'correct':result['status']=='answered' and equal(result['value'],key)})
        rows.append(dict(id=tid,pattern=kind,intended_code=expected_code,native=codes[tid],
                         native_code_match=codes[tid]==expected_code,
                         correct_arms=arms,oracle_code_outputs=receipts))
    return dict(n=len(rows),exact_native_code=sum(r['native_code_match'] for r in rows),
                any_selector_both=sum(bool(r['correct_arms']) for r in rows),
                intended_code_both=sum(all(s['correct'] for s in r['oracle_code_outputs']) for r in rows),
                rows=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,default=HERE/'panel')
    parser.add_argument('--grades',type=Path,default=HERE/'results.json')
    parser.add_argument('--native',type=Path,default=HERE/'native.jsonl')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    r=examine(args.fixtures,args.grades,args.native)
    args.out.write_text(json.dumps(r,indent=2)+'\n')
    print({k:v for k,v in r.items() if k!='rows'})
