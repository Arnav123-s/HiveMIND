"""Evaluate human-supplied repair rules under the same limit on candidate sites."""
import argparse
import ast
import copy
import gzip
import json
from pathlib import Path
import sys

from replay import canonical, corpus, digest, KEYS_SHA, LIMIT, STREAM_SHA


RULES = ('len_to_sum', 'strict_to_inclusive')
MENU = 'fixed_both_round_robin'


def targets(tree, rule):
    if rule == 'len_to_sum':
        legal = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == 'len']
    else:
        legal = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)
                 and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt)]
    return sorted(legal, key=lambda node: (node.lineno, node.col_offset))


def variants(source, mode):
    tree = ast.parse(source)
    # The two-rule control tries each applicable rule's first site before the second
    # site of either rule. Rule and site order never depend on the unknown output.
    rules = RULES if mode == MENU else [mode]
    sites = {r: targets(tree, r) for r in rules}
    candidates = [(rule, sites[rule][i]) for i in range(LIMIT)
                  for rule in rules if i < len(sites[rule])]
    for rule, node in candidates[:LIMIT]:
        child = copy.deepcopy(tree)
        for n in ast.walk(child):
            if type(n) is type(node) and (n.lineno, n.col_offset) == (node.lineno, node.col_offset):
                if rule == 'len_to_sum':
                    n.func.id = 'sum'
                else:
                    n.ops[0] = ast.GtE()
                break
        yield ast.unparse(child)


def evaluate(guest, job, hidden, mode):
    calls = []

    def execute(program, rows):
        result, _, _ = guest.run(program, [r['input'] for r in rows])
        calls.append({'source': digest(program.encode()), 'inputs': len(rows)})
        return ['value' in r and canonical(r['value']) == canonical(expected['output'])
                for r, expected in zip(result, rows, strict=True)]

    proposed = job['source']
    accepted = all(execute(proposed, job['public']))
    checked = 0
    if not accepted:
        for src in variants(proposed, mode):
            checked += 1
            if all(execute(src, job['public'])):
                proposed, accepted = src, True
                break
    passed = accepted and all(execute(proposed, job['validation']))
    actual = execute(proposed, hidden) if passed else []
    return {'id': job['id'], 'phase': job['phase'], 'group': job.get('group'),
            'private_inputs': len(hidden), 'correct': sum(actual), 'wrong': len(actual) - sum(actual),
            'withheld': len(hidden) - len(actual), 'complete': bool(actual) and all(actual),
            'repairs_tested': checked, 'wasm_batches': len(calls), 'wasm_inputs': sum(c['inputs'] for c in calls)}


def read_extra(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--checkout', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--confirmation-stream', type=Path)
    parser.add_argument('--confirmation-keys', type=Path)
    args = parser.parse_args()
    if bool(args.confirmation_stream) != bool(args.confirmation_keys):
        parser.error('supply both confirmation files')
    sys.path.insert(0, str(args.checkout.resolve()))
    from training.experiments.fieldwork.guest import Guest
    guest = Guest(args.sdk)
    stream = corpus('stream.json', STREAM_SHA)
    gold = corpus('sealed-keys.json', KEYS_SHA)
    if args.confirmation_stream:
        stream.update(read_extra(args.confirmation_stream))
        gold.update(read_extra(args.confirmation_keys))
    rows = {mode: [evaluate(guest, j, gold[j['id']]['private'], mode)
                   for j in stream.values() if j['phase'] != 'train']
            for mode in (*RULES, MENU)}
    args.output.write_text(json.dumps(rows, indent=2) + '\n')
    for mode, records in rows.items():
        for phase in ('heldout', 'confirmation'):
            group = [r for r in records if r['phase'] == phase]
            if group:
                print(mode, phase, sum(r['complete'] for r in group), '/', len(group))


if __name__ == '__main__':
    main()
