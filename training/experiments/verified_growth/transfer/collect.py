"""Evaluate frozen planners on the original English request and a CSV. No answer key is read."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT))
from training.experiments.verified_growth.composer import learner, native, solver


SOURCE = {
    'solver.py': '23eaba4bbca3e96663f8b2e5335b7ed6428da6c0e0c33ccd3d675c213038fb68',
    'learner.py': 'dc0e6951376d7379a185e4b498082c478c2f2063ff570d753b339f0c843036ab',
    'native.py': '6a71ae4d4806e855854e33c8d2e5397673893fec6c799287963e02fff265130d',
}
MODES = ('single','flat','learned','rules','agree','native')


def collect(fixtures, native_path, include_native):
    for mod in (solver, learner, native):
        path = Path(mod.__file__)
        assert sha256(path.read_bytes()).hexdigest() == SOURCE[path.name]
    cases = json.loads((fixtures/'requests.json').read_bytes())
    tables = json.loads((fixtures/'tables.json').read_bytes())
    modes = MODES if include_native else MODES[:-1]
    codes = {}
    if include_native:
        for row in map(json.loads,native_path.read_text().splitlines()):
            assert row['selector_sha256'] == SOURCE['native.py'] and row['id'] not in codes
            codes[row['id']] = row
        assert len(codes) == len(cases)
    observations = []
    for arm in modes:
        for case in cases:
            request = case['request']
            for table in case['tables']:
                data = tables[table]
                filename = f'{table}.csv'
                code = None
                if arm == 'native':
                    receipt = codes[case['id']]
                    metadata = json.dumps([request,sorted(data['rows'][0])],ensure_ascii=False)
                    assert sha256(metadata.encode()).hexdigest() == receipt['input_sha256']
                    code = receipt['code']
                result = solver.run_files(request,{filename:data['csv']},arm,code)
                if result['status']=='answered':
                    assert json.loads(result['text'])==result['value']
                observations.append(dict(arm=arm,id=case['id'],table=table,**result))
    return observations


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,default=HERE/'panel')
    parser.add_argument('--native',type=Path,default=HERE/'native.jsonl')
    parser.add_argument('--without-native',action='store_true')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=collect(args.fixtures,args.native,not args.without_native)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
