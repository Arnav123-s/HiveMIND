"""Summarize the four paired policies after all raw responses and grades have been sealed."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def summarize(path):
    native_path = path / 'native.json'
    native = json.loads(native_path.read_bytes())
    grades = json.loads((path / 'grades.json').read_bytes())
    inputs = json.loads((path / 'inputs.json').read_bytes())
    assert native['complete'] and grades['native_sha256'] == hashlib.sha256(native_path.read_bytes()).hexdigest()
    calls = {(c['id'], c['arm']): c for c in native['calls']}
    plans = {r['id']: r for r in inputs['rows']}
    rows = []
    for grade in grades['results']:
        ident = grade['id']
        row = {'id': ident, 'group': grade['group'], 'arms': {}}
        plan = plans[ident]
        for policy, actual in [('short', 'short'), ('full', 'full'), ('gated', plan['gate']),
                               ('scaffold', 'scaffold' if plan['scaffold'] else 'short')]:
            call = calls[ident, actual]
            verdict = grade['arms'][actual]
            usage = call['usage']
            row['arms'][policy] = {'executed_arm': actual, 'ok': verdict['ok'], 'status': verdict['status'],
                                   'input_tokens': usage['prompt_tokens'], 'output_tokens': usage['completion_tokens'],
                                   'wall_s': call['wall_s'], 'cpu_s': call['server_cpu_s'], 'stop': call['finish_reason']}
        rows.append(row)
    totals = {}
    for group in ['all', 'practiced_family', 'new_contract']:
        sample = [r for r in rows if group == 'all' or r['group'] == group]
        totals[group] = {}
        for key in ['short', 'full', 'gated', 'scaffold']:
            rs = [r['arms'][key] for r in sample]
            totals[group][key] = dict(n=len(rs), passes=sum(r['ok'] for r in rs),
                                      gained_vs_short=sum(r['arms'][key]['ok'] and not r['arms']['short']['ok'] for r in sample),
                                      lost_vs_short=sum(not r['arms'][key]['ok'] and r['arms']['short']['ok'] for r in sample),
                                      truncated=sum(r['stop'] == 'length' for r in rs),
                                      **{c: round(sum(r[c] for r in rs), 3) for c in ['input_tokens','output_tokens','wall_s','cpu_s']})
    return {'native_sha256': grades['native_sha256'], 'summaries':totals, 'per_request':rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', type=Path, default=HERE)
    args = parser.parse_args()
    result = summarize(args.path)
    (args.path / 'summary.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
