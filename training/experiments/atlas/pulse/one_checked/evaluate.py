"""Measure a prospective first-answer certificate against the same original after-body trajectory."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

HERE=Path(__file__).resolve().parent
PULSE=HERE.parent
ROOT=PULSE.parents[3]
sys.path[:0]=[str(ROOT),str(PULSE)]
from certificate import certify,expected
from extract import member_text,offline_suite
from training import exam


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebuild(raw):
    rows=[]
    for item in json.loads((HERE/'artifacts.json').read_text()):
        path=raw/f"{item['id']}.zip"
        assert sha(path)==item['sha256']
        shard=int(item['name'].rsplit('-',1)[1])
        seed=20000490+shard
        suite={t[0]:t for t in offline_suite(seed)}
        with zipfile.ZipFile(path) as z:
            names=set(z.namelist())
            for tid,entry in suite.items():
                home=f'exam_{seed}_mixed/{tid}'; prefix=home+'/members/'
                meta=json.loads(z.read(home+'/exam.json'))
                actual=z.read(home+'/REPORT.md').decode() if home+'/REPORT.md' in names else ''
                task=z.read(prefix+'TASK.md').decode().strip()
                events=[json.loads(line) for line in z.read(prefix+'events.jsonl').splitlines() if line.strip()]
                answers={};timings={};last=None
                for event in events:
                    if event['kind']=='seats' and event['agent']=='hive':
                        last=event['ts']
                    m=re.fullmatch(r'member(\d+)',event['agent'])
                    if m and event['kind']=='answer':
                        n=int(m[1]);answers[n]=member_text(z,names,home,n,event['msg'])
                        if last is not None:timings[n]=round(event['ts']-last,3)
                        last=event['ts']
                delivered='## How it was checked' in actual and ('two gave the same values' in actual or 'two of them agreed' in actual)
                check=entry[-1]
                rows.append(dict(id=tid,prompt=task,first=answers.get(1),actual_pass=meta['ok'],actual_delivered=delivered,
                                 actual_wall=meta['seconds'],workers=len(meta['members']),worker_intervals=timings,
                                 actual_worker_verdicts=meta['members'],actual_report=actual[:1500],
                                 kind=check.maker if check else None,rseed=check.rseed if check else None))
    assert len(rows)==64 and len({r['id'] for r in rows})==64
    (HERE/'recorded.json.gz').write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0))


def totals(rows):
    counts=Counter();families=Counter();released=[]
    for row in rows:
        counts['tasks']+=1
        counts['baseline_workers']+=row['workers']
        counts['checked_workers']+=1 if row['certified'] else row['workers']
        original=row['baseline_status']
        counts['baseline_'+original]+=1
        counts['checked_'+row['hybrid_status']]+=1
        if row['applicable']:counts['applicable']+=1
        if row['certified']:
            counts['one_seat_deliveries']+=1
            counts['certified_'+row['hybrid_status']]+=1
            families[row['applicable']]+=1
            released.append(row['id'])
        elif row['applicable']:counts['applicable_uncertified']+=1
    return dict(counts),dict(families),released


def anti_examples():
    adversaries=[
        ('What day of the week is 29 February 2024?','Friday'),
        ('What day of the week is 29 February 2024?','Thursday or Friday'),
        ('What day of the week is 31 February 2024?','Thursday'),
        ('What day of the week is 29 February 2024? Explain.','Thursday'),
        ('What day of the week is 01/02/2024?','Thursday'),
        ('How many days are there from 31 December 2023 to 1 January 2024?','2 days'),
        ('How many days are there from 31 December 2023 to 1 January 2024?','1 year'),
        ('What is the greatest common divisor of 84 and 63?','21 dollars'),
        ('A chair costs 200 dollars and the price falls by 15%. What is the new price?','170 euros'),
        ('A chair costs 200 dollars and the price falls by 15%. What is the new price?','$170 plus a fee'),
        ('What is 68 degrees Fahrenheit in Celsius? One decimal place.','20.0 °F'),
        ('What is 68 degrees Fahrenheit in Celsius? One decimal place.','20'),
        ('What is 68 degrees Fahrenheit in Celsius? One decimal place.','200.0'),
        ('What is 68 degrees Fahrenheit in Celsius? One decimal place. Also tell me the humidity.','20.0 °C'),
    ]
    positives=[
        ('What day of the week is 29 February 2024?','Thursday'),
        ('How many days are there from 31 December 2023 to 1 January 2024?','1 day'),
        ('What is the greatest common divisor of 84 and 63?','21'),
        ('What is 68 degrees Fahrenheit in Celsius? One decimal place.','20.0 °C'),
        ('A chair costs 200 dollars and the price falls by 15%. What is the new price?','$170'),
    ]
    assert all(not certify(task,answer) for task,answer in adversaries)
    assert all(certify(task,answer) for task,answer in positives)
    return {'wrong_or_ambiguous_declined':len(adversaries),'correct_certified':len(positives)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rebuild',action='store_true')
    parser.add_argument('--raw',type=Path,default=PULSE/'.raw');args=parser.parse_args()
    if args.rebuild:rebuild(args.raw)
    actual=json.loads(gzip.decompress((HERE/'recorded.json.gz').read_bytes()))
    # The verifier only gets the full prompt and a single proposal. It cannot see any subsequent answer or verdict.
    flags=[certify(row['prompt'],row['first']) for row in actual]
    used={row['prompt'] for row in json.loads(gzip.decompress((PULSE/'panels.json.gz').read_bytes()))}
    results=[]
    calculator=Counter()
    for row,certified in zip(actual,flags):
        base_status='withheld' if not row['actual_delivered'] else ('correct' if row['actual_pass'] else 'wrong')
        status=base_status
        contract=expected(row['prompt'])
        if certified:
            fields=exam.remake(row['kind'],row['rseed'])
            assert fields[2]==row['prompt']
            check=bool(fields[3](None,row['first'])[0])
            observed=next(v['ok'] for v in row['actual_worker_verdicts'] if v['member']==1)
            assert check==observed
            status='correct' if check else 'wrong'
        # Diagnostic only: the same complete deterministic calculation can also produce an answer itself.
        if contract:
            fields=exam.remake(row['kind'],row['rseed'])
            assert fields[2]==row['prompt']
            direct=str(contract[1])
            right=bool(fields[3](None,direct)[0])
            calculator['correct' if right else 'wrong']+=1
            calculator['deterministic_calls']+=1
        else:
            calculator[base_status]+=1
            calculator['workers']+=row['workers']
        timings=row['worker_intervals']; later=[s for n,s in timings.items() if int(n)>1]
        results.append(dict(id=row['id'],new_prompt=row['prompt'] not in used,applicable=contract[0] if contract else None,
                            certified=certified,baseline_status=base_status,hybrid_status=status,workers=row['workers'],
                            later_seconds_removed=round(sum(later),3) if certified else 0,
                            measured_later_seats=len(later) if certified else 0))
    counts,families,released=totals(results);new,_,_=totals([r for r in results if r['new_prompt']])
    report=dict(scope='G49 after-body, eight original shards, actual recorded fallback unchanged',counts=counts,
                new_prompt_subset=new,certified_families=families,certified_ids=released,
                actual_full_run_wall_seconds=sum(r['actual_wall'] for r in actual),
                posthoc_calculator_without_first_worker=dict(calculator),
                archived_later_worker_seconds_removed=round(sum(r['later_seconds_removed'] for r in results),3),
                measurable_removed_seats=sum(r['measured_later_seats'] for r in results),adversarial_controls=anti_examples(),
                decisions=results,sha256={name:sha(HERE/name) for name in ('protocol.md','certificate.py','artifacts.json','recorded.json.gz','evaluate.py')})
    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(counts,families,new,report['archived_later_worker_seconds_removed'])

if __name__=='__main__':
    main()
