"""Freeze parser decisions before grading the external English intake panel."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from training.experiments.verified_growth.delivery_audit.literal_intake import intake


HERE=Path(__file__).resolve().parent
PANEL=HERE.parent/'intake_panel'


def call(text):
    m=intake.relay.CALL.fullmatch(text)
    if m is None:
        raise ValueError("invalid answer-key literal call")
    name,args=intake.relay.call_args(m)
    return [name,args]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(exist_ok=True,parents=True)
    assert sha256(Path(intake.__file__).read_bytes()).hexdigest()=='11aa54578a7af9fed43dbd0014f9791b04770c96fd4904b78d36ff5d6e70ba2c'
    for line in (PANEL/'manifest.sha256').read_text().splitlines():
        checksum,name=line.split(maxsplit=1)
        assert sha256((PANEL/name.strip()).read_bytes()).hexdigest()==checksum
    questions=json.loads((PANEL/'questions.json').read_bytes())
    decisions={}
    for row in questions:
        spec=intake.contract(row['request'])
        decisions[row['id']]=None if spec is None else [spec[0],sorted(spec[1]),spec[2],spec[3]]
    file=args.out/'outside-decisions.json'
    file.write_text(json.dumps(decisions,indent=2)+'\n')
    decisions=json.loads(file.read_bytes())
    keys=json.loads((PANEL/'expected.json').read_bytes())
    rows=[]
    for ident,key in keys.items():
        actual=decisions[ident]
        differences=[]
        if key['decision']=='withhold':
            status='false_acceptance' if actual is not None else 'correct_withhold'
        elif actual is None:
            status='missed'
        else:
            wanted=[key['file'],sorted(key['functions']),[[call(v['call']),v['expected']] for v in key['examples']],
                    [call(v) for v in key['requested_calls']]]
            # JSON encoding retains the distinction between a truth value, an integer and a string.
            for name,left,right in zip(('filename','names','examples','queries'),wanted,actual,strict=True):
                if name == 'examples':
                    left=sorted(json.dumps(row,sort_keys=True) for row in left)
                    right=sorted(json.dumps(row,sort_keys=True) for row in right)
                if json.dumps(left,sort_keys=True)!=json.dumps(right,sort_keys=True):
                    differences.append(name)
            status='mismatch' if differences else 'correct_extraction'
        rows.append(dict(id=ident,expected=key,observed=actual,grade=status,differences=differences))
    result=dict(counts=dict(Counter(r['grade'] for r in rows)),rows=rows,
                source_sha256=sha256(Path(intake.__file__).read_bytes()).hexdigest(),
                decisions_sha256=sha256(file.read_bytes()).hexdigest())
    print(result['counts'])
    (args.out/'outside-results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
