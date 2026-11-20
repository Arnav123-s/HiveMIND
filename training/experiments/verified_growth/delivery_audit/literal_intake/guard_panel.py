"""Replay the one-sided losslessness check on the previously opened outside panel."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from . import lossless


HERE=Path(__file__).resolve().parent


def compare():
    original=HERE/'outside-results.json'
    assert sha256(original.read_bytes()).hexdigest()=='ce214cb4618f42bf6b11da2638b3aa0135401ec522caa3688fd373026b4a7aef'
    assert sha256(Path(lossless.__file__).read_bytes()).hexdigest()=='59f1e006d9864d9c39726d361c0a5075e895b43c8e9bbdac10f2ce19ebff9a8d'
    old=json.loads(original.read_bytes())
    panel=HERE.parent/'intake_panel'
    questions={q['id']:q['request'] for q in json.loads((panel/'questions.json').read_bytes())}
    rows=[]
    for row in old['rows']:
        spec=lossless.contract(questions[row['id']])
        observed=None
        if spec is not None:
            observed=json.loads(json.dumps([spec[0],sorted(spec[1]),spec[2],spec[3]]))
            assert observed==row['observed']
        if spec is None and row['observed'] is not None:
            grade='correct_withhold' if row['expected']['decision']=='withhold' else 'missed'
        else:
            grade=row['grade']
        rows.append(dict(id=row['id'],before=row['grade'],after=grade,observed=observed))
    return {"source_sha256":sha256(Path(lossless.__file__).read_bytes()).hexdigest(),
            "original_sha256":sha256(original.read_bytes()).hexdigest(),"before":old['counts'],
            "after":dict(Counter(r['after'] for r in rows)),"rows":rows}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    result=compare()
    print(result['before'],result['after'])
    args.out.write_text(json.dumps(result,indent=2)+'\n')
