"""Post-freeze file diagnostic: request a named JSON artifact through the public CLI."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT))
from training.experiments.verified_growth.transfer.score import equal


def check(fixtures):
    cases=json.loads((fixtures/'requests.json').read_bytes())
    tables=json.loads((fixtures/'tables.json').read_bytes())
    keys=json.loads((fixtures/'keys.json').read_bytes())
    command = [sys.executable, '-m', 'training.experiments.verified_growth.composer.files']
    chosen={}
    for case in cases:
        if case['pattern'] not in {'anchor','adjacent','clarify'}:
            chosen.setdefault(case['pattern'],case)
    assert len(chosen)==6
    rows=[]
    for case in chosen.values():
        for table in case['tables']:
            with TemporaryDirectory() as td:
                directory=Path(td)
                source=directory/f'{table}.csv'
                source.write_text(tables[table]['csv'])
                dest=directory/'out'
                dest.mkdir()
                filename=dest/'result.json'
                request=case['request']+' Save the answer as result.json.'
                args=command+[str(source),request,'--out-dir',str(dest),'--mode','rules']
                response=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=20)
                body=filename.read_bytes() if filename.is_file() else None
                got=None if body is None else json.loads(body)
                key=keys[f"{case['id']}/{table}"]['value']
                row={'id':case['id'],'table':table,'request':request,'file':filename.name,
                     'returncode':response.returncode,'stdout':response.stdout.strip(),
                     'bytes':None if body is None else body.decode(),'value':got,'expected':key,
                     'correct':body is not None and response.returncode==0 and equal(got,key)}
                if body is not None:
                    previous=b'{"earlier":true}\n'
                    filename.write_bytes(previous)
                    second=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=20)
                    row.update(existing_file_unchanged=filename.read_bytes()==previous,
                               existing_file_returncode=second.returncode)
                rows.append(row)
    return {'publisher_sha256':sha256((HERE.parent/'composer/files.py').read_bytes()).hexdigest(),
            'selector':'rules','selection':'first preregistered request per primary pattern, both data editions',
            'rows':rows,'created':sum(r['bytes'] is not None for r in rows),'correct':sum(r['correct'] for r in rows)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,default=HERE/'panel')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    r=check(args.fixtures)
    args.out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    print(r['created'],r['correct'])
