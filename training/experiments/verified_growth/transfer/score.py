"""Score completed blind task predictions after inference. Never imported by the solver."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRAS = ("anchor", "adjacent", "clarify")
UNSEEN_STRUCTURES = ("filtered-group-sum", "filtered-rank-count", "filtered-rank-sum")


def equal(value, expected):
    if isinstance(expected, dict):
        return isinstance(value, dict) and set(value) == set(expected) and all(
            equal(value[k], expected[k]) for k in expected)
    if type(expected) is int:
        return type(value) in (int, float) and expected == value
    return type(value) is type(expected) and value == expected


def grade(record, key):
    denied = record['status'] == 'abstained' and record.get('value') is None
    if denied:
        return 'appropriate_hold' if key['output'] == 'defer' else 'missed'
    if record['status'] != 'answered':
        return 'error'
    return 'correct' if key['output'] != 'defer' and equal(record['value'],key['value']) else 'wrong'


def evaluate(fixtures, records_path):
    for line in (HERE/'manifest.sha256').read_text().splitlines():
        checksum, name = line.split()
        assert checksum == sha256((fixtures/name).read_bytes()).hexdigest(), name
    queries = json.loads((fixtures/'requests.json').read_bytes())
    keys = json.loads((fixtures/'keys.json').read_bytes())
    arms = json.loads(records_path.read_bytes())
    modes = {r['arm'] for r in arms}
    summary, outcomes = {}, []
    by_key = {(x['arm'],x['id'],x['table']):x for x in arms}
    assert len(by_key) == len(arms) == len(keys) * len(modes)
    for mode in sorted(modes):
        totals = {}
        for case in queries:
            values = []
            grades = []
            for table in case['tables']:
                record = by_key[mode,case['id'],table]
                key = keys[f"{case['id']}/{table}"]
                grades.append(grade(record,key))
                values.append(key['value'])
            paired = 'correct' if grades==['correct','correct'] else (
                'appropriate_hold' if grades==['appropriate_hold','appropriate_hold'] else
                next((g for g in ('error','wrong','missed') if g in grades), 'partial'))
            row = dict(arm=mode,id=case['id'],pattern=case['pattern'],editions=grades,
                       paired=paired,expected_values=values)
            outcomes.append(row)
            totals.setdefault(case['pattern'], []).append(row)
        groups = {}
        for pattern, rows in totals.items():
            groups[pattern] = {'paired':dict(Counter(x['paired'] for x in rows)),
                               'editions':dict(Counter(g for x in rows for g in x['editions']))}
        primary = [p for p in groups if p not in EXTRAS]
        primary_correct = sum(groups[p]['paired'].get('correct',0) for p in primary)
        all_primary = Counter()
        for p in primary:
            all_primary.update(groups[p]['editions'])
        summary[mode] = dict(primary_all_editions=dict(all_primary), primary_requests_correct=primary_correct,
                             mastered_patterns=[p for p in primary if groups[p]['paired'].get('correct')==3],
                             unseen_requests_correct=sum(groups[p]['paired'].get('correct',0) for p in UNSEEN_STRUCTURES),
                             unseen_mastered=[p for p in UNSEEN_STRUCTURES if groups[p]['paired'].get('correct')==3],
                             groups=groups)
    return {'records_sha256':sha256(records_path.read_bytes()).hexdigest(), 'summary':summary,'outcomes':outcomes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=HERE/'panel')
    parser.add_argument('--records', type=Path, default=HERE/'decisions.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.fixtures,args.records)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    for mode, result in report['summary'].items():
        print(mode, result['primary_requests_correct'], len(result['mastered_patterns']), result['primary_all_editions'])
