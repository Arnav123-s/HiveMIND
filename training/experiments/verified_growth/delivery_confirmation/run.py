"""Exercise real solo.first and the growth workflow's actual artifact glob list on neutral worker snapshots."""
import argparse
from base64 import b64decode
from collections import Counter
from hashlib import sha256
import importlib.util
import json
import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
import subprocess
from zipfile import ZipFile

import yaml


HERE=Path(__file__).resolve().parent
CONTROL='4cbd41cb2e27d263f102801c0a7a008268d0b1aa'


def digest(data):
    return sha256(data).hexdigest()


def tree(directory):
    return {str(p.relative_to(directory)):digest(p.read_bytes()) for p in sorted(directory.rglob('*')) if p.is_file()}


def archive(root, workflow, path):
    gate=yaml.safe_load(workflow.read_bytes())['jobs']['gate']['steps']
    selected=next(s for s in gate if s.get('uses')=='actions/upload-artifact@v4' and 'gate-work' in s['with']['name'])
    patterns=selected['with']['path'].splitlines()
    if any(pattern.startswith('!') for pattern in patterns):
        raise ValueError('negative upload globs need a separate implementation')
    matched = [p for pattern in patterns for p in root.glob(pattern)]
    entries = sorted({p for item in matched for p in ([item] if item.is_file() else item.rglob('*')) if p.is_file()})
    with ZipFile(path,'w') as bundle:
        for p in entries:
            bundle.write(p,p.relative_to(root))
    with ZipFile(path) as bundle:
        return {n:digest(bundle.read(n)) for n in bundle.namelist()},patterns


def members_from_disk(home, n):
    result=[]
    for i in range(1,n+1):
        row=json.loads((home/'members'/f'member{i}.json').read_bytes())
        result.append(dict(row,seat=i,work=Path(row['work'])))
    return result


def run_case(case, gold, root, stash, solo, workflow, candidate=None, proposed_workflow=None, evidence_path=None):
    home=root/'runs/exam/cohort'/case['id']
    previous=case['stale']
    if previous:
        for target in (home/'members/work',home/'work'):
            target.mkdir(parents=True)
            for name,body in previous.items():
                (target/name).write_bytes(b64decode(body))

    def replay_member(task, n, board, guard, work, temperature, who, also):
        supplied=case['seats'][n-1] if n<=len(case['seats']) else {'answer':'','files':{}}
        work.mkdir(parents=True,exist_ok=True)
        # The code driver is archival bookkeeping only. No untrusted worker program is executed.
        code=f"print('recorded handoff attempt {n}')\n"
        (work/f'member{n}_1.py').write_text(code)
        (work/f'.member{n}_1.py.out').write_text(supplied['answer']+'\n')
        for name,body in supplied['files'].items():
            assert Path(name).name==name
            (work/name).write_bytes(b64decode(body))
        return dict(answer=supplied['answer'],program=code,turns=1,who=who,messages=[],hints=[],
                    temperature=temperature,also=list(also))

    with patch.object(solo,'member',replay_member), patch.object(solo.ternary,'seating',lambda task:['coder']), \
         patch.object(solo,'library',lambda:root/'local-memory/solved.jsonl'):
        delivered=solo.first(case['request'],home,members=2)

    wanted=delivered['requested_files']
    expected_names=set(gold['accepted'][0])
    assert set(wanted)==expected_names,(case['id'],wanted,expected_names)
    decisions=json.loads((home/'members/members.json').read_bytes())
    before=tree(home/'work')
    raw=[]
    members=members_from_disk(home,delivered['tries'])
    for row in members:
        seat=row['seat']
        supplied=case['seats'][seat-1]['files'] if seat<=len(case['seats']) else {}
        on_disk={n:digest((row['work']/n).read_bytes()) for n in wanted if (row['work']/n).is_file()}
        assert on_disk=={n:digest(b64decode(v)) for n,v in supplied.items() if n in expected_names},(case['id'],seat)
        raw.append(dict(seat=seat,work=str(row['work'].relative_to(root)),artifacts=on_disk,
                        missing=sorted(expected_names-set(on_disk))))
    report=home/'REPORT.md'
    report_digest=digest(report.read_bytes()) if report.exists() else None
    decision_digest=digest((home/'members/members.json').read_bytes())
    archived,patterns=archive(root,workflow,stash/'before.zip')
    archived_before=sum((f"{r['work']}/{name}" in archived and archived[f"{r['work']}/{name}"]==h)
                        for r in raw for name,h in r['artifacts'].items())

    bundle={p:before[p] for p in delivered['files']}
    allowed=[{n:digest(b64decode(v)) for n,v in a.items()} for a in gold['accepted']]
    official='withheld' if not delivered['agreed'] else ('correct' if bundle in allowed else 'wrong')
    row=dict(id=case['id'],requested=wanted,seats=raw,eligible_raw_blobs=sum(len(r['artifacts']) for r in raw),
             original_archived_named_blobs=archived_before,original_archive_entries=sorted(archived),
             stock_published=bundle,stock_grade=official,stock_agreed=delivered['agreed'],
             stock_selected_seat=decisions.get('selected_member'),stock_files=delivered['files'],
             stale_visible_without_claim=sorted(set(before)-set(delivered['files'])),raw_complete_correct_seats=[
                 r['seat'] for r in raw if expected_names and r['artifacts'] in allowed])
    # The stock isolation guard gives a nonempty reused member directory a unique random suffix.
    # Canonicalize that suffix in the receipt only, after using the actual path for every hash lookup.
    for attempt in raw:
        actual = attempt['work']
        suffix = Path(actual).name
        if suffix.startswith(f"member{attempt['seat']}-"):
            normalized=str(Path(actual).with_name(f"member{attempt['seat']}-[isolated]"))
            row['original_archive_entries'] = [entry.replace(actual+'/', normalized+'/') for entry in row['original_archive_entries']]
            attempt['work']=normalized
    if candidate is None:
        return row,patterns

    output=root/evidence_path
    if proposed_workflow:
        steps = yaml.safe_load(proposed_workflow.read_bytes())['jobs']['gate']['steps']
        hook = next(step['run'] for step in steps if 'training.member_evidence' in step.get('run',''))
        arguments = re.search(r'python(?:3)? +(?:-m +training\.member_evidence) +--root +([\w./-]+) +--out +([\w./-]+)',hook)
        assert arguments and arguments.groups()==('runs/exam',evidence_path), hook
        environment = os.environ | {'PYTHONPATH':str(Path(candidate.__file__).resolve().parents[1])}
        call = subprocess.run([sys.executable,'-m','training.member_evidence','--root',arguments[1],'--out',arguments[2]],
                              cwd=root,env=environment,capture_output=True,text=True,timeout=30,check=True)
        assert f'Captured ungraded worker evidence for {int(bool(wanted))} tasks' in call.stdout
    else:
        captured=candidate.collect(root/'runs/exam',output)
        assert captured==int(bool(wanted))
    evidence=output/'cohort'/case['id']
    seen=tree(evidence)
    assert tree(home/'work')==before
    assert digest((home/'members/members.json').read_bytes())==decision_digest
    assert (digest(report.read_bytes()) if report.exists() else None)==report_digest
    source_artifacts={f"seat-{r['seat']}/artifacts/{name}":h for r in raw for name,h in r['artifacts'].items()}
    retained={k:h for k,h in seen.items() if '/artifacts/' in k}
    row.update(retained=retained, verified_retention=retained==source_artifacts, no_new_publication=True,
               evidence_files=sorted(seen))
    if (evidence/'manifest.json').is_file():
        manifest=json.loads((evidence/'manifest.json').read_bytes())
        assert manifest['task_sha256']==digest((home/'members/TASK.md').read_bytes())
        assert manifest['purpose']=='ungraded worker evidence'
        assert manifest['requested']==wanted and len(manifest['seats'])==len(raw)
        for snapshot, recorded in zip(raw,manifest['seats'],strict=True):
            assert snapshot['seat']==recorded['seat'] and set(recorded['files'])==set(wanted)
            for name,info in recorded['files'].items():
                if name in snapshot['artifacts']:
                    assert info['status']=='archived' and info['sha256']==snapshot['artifacts'][name]
                    assert seen[info['path']]==info['sha256']
                else:
                    assert info['status']=='missing'
        row['manifest']=manifest
    if proposed_workflow:
        observable,_=archive(root,proposed_workflow,stash/'after.zip')
        row['uploaded_captured_blobs']=sum(observable.get(str((evidence/k).relative_to(root)))==h for k,h in retained.items())
        row['uploaded_manifest']=str((evidence/'manifest.json').relative_to(root)) in observable
    return row,patterns


def run(args):
    sys.path.insert(0,str(args.stock.resolve()))
    from team import solo
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.stock,text=True).strip()==CONTROL
    for file in ('team/solo.py','team/deliverables.py','.github/workflows/grow.yml'):
        assert (args.stock/file).read_bytes()==subprocess.check_output(['git','show',f'{CONTROL}:{file}'],cwd=args.stock)
    candidate=None
    if args.candidate:
        assert digest(args.candidate.read_bytes())==args.expected_candidate_sha
        spec=importlib.util.spec_from_file_location('training.member_evidence',args.candidate)
        candidate=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(candidate)
    for line in (HERE/'manifest.sha256').read_text().splitlines():
        h,name=line.split()
        assert digest((args.fixtures/name).read_bytes())==h
    cases=json.loads((args.fixtures/'cases.json').read_bytes())
    keys=json.loads((args.fixtures/'keys.json').read_bytes())
    results=[]
    for case in cases:
        with TemporaryDirectory() as tmp:
            scratch=Path(tmp)
            row,patterns=run_case(case,keys[case['id']],scratch/'repo',scratch,solo,
                                  args.stock/'.github/workflows/grow.yml',candidate,args.workflow,args.evidence_path)
            results.append(row)
    counts=dict(stock_grades=dict(Counter(r['stock_grade'] for r in results)),
                total_seats=sum(len(r['seats']) for r in results),
                raw_blobs=sum(r['eligible_raw_blobs'] for r in results),
                archived_named_blobs=sum(r['original_archived_named_blobs'] for r in results))
    if candidate:
        counts.update(retained=sum(len(r['retained']) for r in results),exact_captures=sum(r['verified_retention'] for r in results))
    if args.workflow:
        counts['updated_archive_named_blobs']=sum(r['uploaded_captured_blobs'] for r in results)
        counts['archived_manifests']=sum(r['uploaded_manifest'] for r in results)
    return dict(stock_commit=CONTROL, proposed_workflow_sha256=digest(args.workflow.read_bytes()) if args.workflow else None,stock_solo_sha256=digest(Path(solo.__file__).read_bytes()),
                candidate_sha256=digest(args.candidate.read_bytes()) if candidate else None,
                archive_patterns=patterns,summary=counts,cases=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock',type=Path,required=True)
    parser.add_argument('--fixtures',type=Path,default=HERE/'panel')
    parser.add_argument('--candidate',type=Path)
    parser.add_argument('--expected-candidate-sha',default='42635401038b4122dd8553e71c97e70b1ea672e25b4f8d823765d59c8a99b9a4')
    parser.add_argument('--workflow',type=Path,help='proposed workflow for testing upload of the new evidence')
    parser.add_argument('--evidence-path',default='runs/exam/worker-evidence',help='relative destination passed by the workflow')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    report=run(args)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(report['summary'])
