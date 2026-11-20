"""Replay the isolated file-recovery policy against real archived member programs."""
import argparse
from hashlib import sha256
import inspect
import json
from pathlib import Path
import random
import re
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from training import exam
from training.experiments.fieldwork.guest import Guest
import holdout
from recover import REQUEST, contract_cases, execute, recover


def collect(archives):
    manifest = json.loads((HERE.parent/'pulse/artifacts.json').read_text())
    jobs = []
    for artifact in manifest:
        if 'after' not in artifact['name']:
            continue
        path = archives/(str(artifact['id'])+'.zip')
        if sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
            raise ValueError('unexpected source archive')
        with ZipFile(path) as bundle:
            names = bundle.namelist()
            for entry in names:
                if not entry.endswith('/exam.json'):
                    continue
                grade = json.loads(bundle.read(entry))
                if not re.fullmatch(r'[eh]\d+_\d+', grade['id']):
                    continue  # the fixed held-out exam is a separate population
                prefix = entry.removesuffix('exam.json')+'members/'
                prompt = bundle.read(prefix+'TASK.md').decode().strip()
                job = dict(generation=artifact['generation'], id=grade['id'], artifact=artifact['id'],
                           original=grade['ok'], original_declined=grade['answer'].strip().lower().startswith('not confirmed'),
                           task_sha256=sha256(prompt.encode()).hexdigest())
                if REQUEST.fullmatch(prompt):
                    job['prompt'] = prompt
                    job['programs'] = [[n.removeprefix(prefix), bundle.read(n).decode()] for n in sorted(names)
                                       if n.startswith(prefix) and re.search(r'/member\d+_\d+\.py$', n)]
                jobs.append(job)
    if len(jobs) != len({(j['generation'], j['id']) for j in jobs}) or len(jobs)!=192:
        raise ValueError('Expected the 192 distinct after-arm pulse jobs')
    return jobs


def official_grade(guest, job, source, visible):
    # Recreate the official seed, its exact prompt, and the hidden test vectors. Execute in WASI.
    seed = int(job['id'][1:].split('_')[0])
    question = next(x for x in exam.exam(seed, 8, level='mixed') if x[0]==job['id'])
    if question[3].strip()!=job['prompt']:
        raise ValueError('Official generator differs from archive')
    closure = inspect.getclosurevars(question[4]).nonlocals
    rng = random.Random(f"hidden:{closure['seed']}")
    examples = [(name,args[0],ref(*args)) for name,_,ref,draw in closure['fns']
                for args in (draw(rng) for _ in range(25))]
    values, _, _ = execute(guest, source, [c[:2] for c in examples])
    passed = sum(v==c[2] for v,c in zip(values, examples, strict=True))
    said = all(str(w) in visible or repr(w) in visible for w in closure['want'])
    return dict(passed=passed, total=len(examples), visible_answers_match=said, okay=passed==len(examples) and said)


def independent_grade(guest, source):
    cases = holdout.cases()
    observed, _, _ = execute(guest, source, [(n,v) for n,v,_ in cases])
    return sum(type(p) is type(c[2]) and p == c[2] for p,c in zip(observed,cases,strict=True))


def summarize(jobs, guest, out):
    rows = []
    for j in jobs:
        row = {k:j[k] for k in ('id','generation','original')}
        row.update(recovered=False, final=j['original'])
        if 'prompt' in j:
            folder=out/j['generation']/j['id']
            receipt=recover(j['prompt'], j['original_declined'], j['programs'], guest, folder)
            row['receipt']=receipt
            if receipt and receipt['delivered']:
                src=(folder/'durations.py').read_text()
                row['official']=official_grade(guest,j,src,(folder/'REPORT.md').read_text())
                row['fresh_correct']=independent_grade(guest,src)
                row.update(recovered=True,final=row['official']['okay'])
        rows.append(row)
    summary={}
    for g in sorted({x['generation'] for x in jobs}):
        part=[x for x in rows if x['generation']==g]
        summary[g]=dict(n=len(part), original=sum(x['original'] for x in part), final=sum(x['final'] for x in part),
                        recovered=sum(x['recovered'] for x in part), regressions=sum(x['original'] and not x['final'] for x in part))
    return rows,summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collect',type=Path, help='directory containing the digest-checked ZIPs named in ../pulse/artifacts.json')
    p.add_argument('--sdk',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    source=HERE/'archive.json'
    if args.collect:
        jobs=collect(args.collect)
        source.write_text(json.dumps(jobs,indent=1)+'\n')
    else:
        jobs=json.loads(source.read_text())
    args.out.mkdir(parents=True,exist_ok=False)
    guest=Guest(args.sdk)
    rows,summary=summarize(jobs,guest,args.out)
    eligible=next(j['prompt'] for j in jobs if 'prompt' in j)
    controls={}
    for label, src in holdout.wrong_candidates().items():
        with TemporaryDirectory() as tmp:
            decision=recover(eligible,True,[(label,src)],guest,Path(tmp))
        controls[label]=dict(qualified=bool(decision and decision['delivered']), fresh_correct=independent_grade(guest,src))
    admission={(n,v) for n,v,_ in contract_cases()}
    overlap=[[n,v] for n,v,_ in holdout.cases() if (n,v) in admission]
    result=dict(summary=summary, independent_cases=len(holdout.cases()), overlap_with_admission=overlap,
                wrong_candidate_controls=controls,rows=rows)
    (args.out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':
    main()
