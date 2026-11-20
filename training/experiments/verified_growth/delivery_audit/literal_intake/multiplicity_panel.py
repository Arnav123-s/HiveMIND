"""Check whether relaxing the repeated-call veto changes any of the 13 known decisions."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from . import multiplicity


HERE=Path(__file__).resolve().parent


def compare():
    src=sha256(Path(multiplicity.__file__).read_bytes()).hexdigest()
    assert src=='22311a277875acffe9176ce6d913402f26bcb727b138f93c7dab526b5ea9e5e5'
    original=json.loads((HERE/'outside-results.json').read_bytes())
    conservative=json.loads((HERE/'guard-results.json').read_bytes())
    strict={k['id']:k['after'] for k in conservative['rows']}
    panel=HERE.parent/'intake_panel'
    inputs={q['id']:q['request'] for q in json.loads((panel/'questions.json').read_bytes())}
    rows=[]
    for row in original['rows']:
        spec=multiplicity.contract(inputs[row['id']])
        value=None if spec is None else json.loads(json.dumps([spec[0],sorted(spec[1]),spec[2],spec[3]]))
        if value is not None:
            assert value==row['observed']
        grade=row['grade'] if value==row['observed'] else ('missed' if row['expected']['decision']=='extract' else 'correct_withhold')
        rows.append(dict(id=row['id'],first=row['grade'],conservative=strict[row['id']],multiplicity=grade,observed=value))
    return dict(source_sha256=src,counts=dict(Counter(r['multiplicity'] for r in rows)),rows=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    result=compare()
    print(result['counts'])
    args.out.write_text(json.dumps(result,indent=2)+'\n')
