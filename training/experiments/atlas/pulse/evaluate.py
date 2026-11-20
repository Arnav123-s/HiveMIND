"""Score real four-seat panels through offline deterministic exam checks after all stopping choices are made."""
from collections import Counter
import gzip
import hashlib
from itertools import product
import json
from pathlib import Path
import random
import sys

from policy import fixed, key, pulse, reserve

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from training import exam
from training.hive_bench import _body


def stream(row):
    # No task, grading, time, identity, or unpurchased suffix is sent to the sequential selector.
    return (seat['answer'] for seat in row['seats'])


def predictions(row):
    choices = {f'fixed{k}':fixed(stream(row),k) for k in (2,3,4)}
    choices['fixed4_strict'] = fixed(stream(row),4,strict=True)
    choices['r1_trigger_max4'] = reserve(stream(row))
    choices['pulse'] = pulse(stream(row))
    assert choices['pulse'][0] == choices['fixed4'][0]
    return choices


def grade(row, assessment, choices):
    _, _, regenerated, check = exam.remake(row['kind'], row['rseed'])
    if regenerated != row['prompt']:
        raise ValueError(f"grader prompt mismatch {row['id']}")
    seats = row['seats']
    def verify(answer):
        return bool(answer.strip()) and bool(check(None, answer)[0])
    verdicts = [verify(seat['answer']) for seat in seats]
    mismatch = [i + 1 for i,(v,w) in enumerate(zip(verdicts,assessment['recorded_seat_verdicts'])) if v != w]
    methods = {}
    for name,(selected,used) in choices.items():
        times = [seat['seconds'] for seat in seats[:used]]
        methods[name] = dict(selected=None if selected is None else selected + 1, seats=used,
                             status='withheld' if selected is None else ('correct' if verdicts[selected] else 'wrong'),
                             trace_seconds=round(sum(times),3) if all(s is not None and s >= 0 for s in times) else None)
    old = assessment['actual_after']
    delivered = old['released']
    old_check = verify(_body(old['report']))
    methods['actual_after'] = dict(selected=None,seats=old['completed_workers'],
                                   status=('correct' if old_check else 'wrong') if delivered else 'withheld',
                                   run_seconds=old['wall_seconds'])
    stats = dict(id=row['id'], generation=row['generation'], shard=row['seed']%10, kind=row['kind'],
                 hard=row['tid'].startswith('h'), official_seat_mismatches=mismatch,
                 actual_official_pass=old['ok'], delivered_after_report_pass=old_check,
                 worker_right=verdicts, four_distinct_cell_names=len({s['who'] for s in seats})==4,
                 identical_four_text_keys=len({key(s['answer']) for s in seats})==1,
                 methods=methods)
    return stats


def summary(rows):
    out = {}
    for name in rows[0]['methods']:
        results = [r['methods'][name] for r in rows]
        c = Counter(r['status'] for r in results)
        answers = c['correct']+c['wrong']
        seconds = [r['trace_seconds'] for r in results if r.get('trace_seconds') is not None]
        out[name] = dict(tasks=len(rows), correct=c['correct'], wrong=c['wrong'], withheld=c['withheld'],
                         coverage=round(answers/len(rows),4),wrong_per_delivery=round(c['wrong']/answers,4) if answers else None,
                         seats=sum(r['seats'] for r in results),seat_distribution=dict(sorted(Counter(r['seats'] for r in results).items())),
                         timed_tasks=len(seconds),archived_seat_seconds=round(sum(seconds),3) if seconds else None)
        if name=='actual_after':
            out[name]['original_full_wall_seconds']=sum(r['run_seconds'] for r in results)
    return out


def main():
    cases=json.loads(gzip.decompress((HERE/'panels.json.gz').read_bytes()))
    decisions={r['id']:predictions(r) for r in cases}
    # Assessment data is first read only after every candidate choice is committed.
    ledger=json.loads(gzip.decompress((HERE/'assessment.json.gz').read_bytes()))
    rows = [grade(r,ledger[r['id']],decisions[r['id']]) for r in cases]
    (HERE/'decisions.json.gz').write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0))
    assert len(decisions)==len(ledger)==len(cases)
    for ordered in product(['','blue','green','amber','white'],repeat=4):
        assert pulse(iter(ordered))[0]==fixed(iter(ordered),4)[0]
    held=[r for r in rows if r['generation']!='g50']
    by_split={name:summary(group) for name,group in [
        ('engineering_g50',[r for r in rows if r['generation']=='g50']),
        ('evaluation',held),('g51',[r for r in held if r['generation']=='g51']),('g52',[r for r in held if r['generation']=='g52']),
        ('evaluation_easy',[r for r in held if not r['hard']]),('evaluation_hard',[r for r in held if r['hard']])]}
    cohort=json.loads((HERE/'cohort.json').read_bytes())
    audience={}
    for name,gens in [('engineering_g50',{'g50'}),('evaluation',{'g51','g52'})]:
        counts=Counter()
        for r in cohort:
            if r['generation'] in gens:
                counts.update({k:v for k,v in r.items() if k not in ('generation','shard')})
        audience[name]=dict(counts)
    soft=Counter()
    for r in held:
        pulse_status=r['methods']['pulse']['status']
        if any(r['worker_right']):soft['at_least_one_passing_worker']+=1
        if not r['four_distinct_cell_names']:soft['repeated_cell_name_in_panel']+=1
        if r['identical_four_text_keys']:soft['all_four_canonical_outputs_identical']+=1
        if pulse_status=='wrong' and r['identical_four_text_keys']:soft['wrong_despite_identical_four']+=1
        if pulse_status=='withheld' and any(r['worker_right']):soft['withheld_despite_passing_worker']+=1
    # Paired uncertainty on seat savings; resample the 16 independent shard labels, carrying all their tasks together.
    clusters={}
    for r in held: clusters.setdefault((r['generation'],r['shard']),[]).append(r)
    rng=random.Random(11052026)
    draws=[]
    groups=list(clusters.values())
    for _ in range(4000):
        sample=[r for group in rng.choices(groups,k=len(groups)) for r in group]
        draws.append(1-sum(r['methods']['pulse']['seats'] for r in sample)/(4*len(sample)))
    draws.sort()
    report=dict(coverage=audience,metrics=by_split,evaluation_diagnostics=dict(soft),
                candidate_vs_official_grade_mismatches=[(r['id'],r['official_seat_mismatches']) for r in rows if r['official_seat_mismatches']],
                official_after_vs_regenerated_report_mismatch=[r['id'] for r in rows if r['actual_official_pass']!=r['delivered_after_report_pass']],
                evaluation_wrong_ids=[r['id'] for r in held if r['methods']['pulse']['status']=='wrong'],
                evaluation_pulse_vs_fixed4_different=sum(r['methods']['pulse']['selected']!=r['methods']['fixed4']['selected'] for r in held),
                evaluation_shard_bootstrap_seat_savings_fraction_95=[round(draws[100],4),round(draws[3899],4)],
                abstract_equivalence_tests=625,
                sha256={fname:hashlib.sha256((HERE/fname).read_bytes()).hexdigest()
                        for fname in ['protocol.md','artifacts.json','cohort.json','panels.json.gz','assessment.json.gz',
                                      'policy.py','extract.py','evaluate.py','decisions.json.gz']})
    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,metrics in by_split['evaluation'].items():
        print(name,metrics['correct'],metrics['wrong'],metrics['withheld'],metrics['seats'],metrics['archived_seat_seconds'])

if __name__=='__main__':
    main()
