"""Replay the original 8B drafts under two repair policies. Requires Python/Wasmtime and the fieldwork WASI SDK."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
LIVE_SHA = '86687463fb64c3dc73fb6d1585bed70df48d9e9b6ff36ec135b7ed4269de4bf4'
DONOR_SHA = 'ce5e53820974099e91c1cd2feb554bd97d886cc9150e0365cd328918095a036c'
LIMIT = 2
CLI_CASES = {
    'transit_tickets': ({'minutes': [1200, 1250, 1217, 1300]}, 3),
    'library_fees': ({'days': [2, 11, 3, 4]}, 165),
    'sensor_streak': ({'readings': [24, 25, None, 26, 24, 40, 70]}, 2),
    'quote_spread': ({'quotes': [173, 197, 184]}, 24),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run_sources(spec, sources, guest, out, bank, work, learn):
    calls = []
    def replay(task, prefix, prior):
        source = sources[len(calls)]
        calls.append(sha(source.encode()))
        return {'source': source, 'usage': {'completion_tokens': 0}, 'stop': 'frozen_source', 'seconds': 0}
    receipt = work(spec, guest, replay, out, bank, rounds=len(sources), repair_budget=LIMIT, learn_repairs=learn)
    return receipt, calls


def train(guest, bank, root, work, load_bank):
    data = gzip.decompress((HERE.parent / 'experiment' / 'stream.json.gz').read_bytes())
    if sha(data) != DONOR_SHA:
        raise ValueError('training corpus changed')
    rows = [row for row in json.loads(data).values() if row['phase'] == 'train']
    records = []
    for row in rows:
        spec = {'name': row['id'], 'task': row['prompt'], 'examples': row['public'],
                'validation': row['validation'], 'jobs': []}
        receipt, calls = run_sources(spec, [row['source'], row['second_training_proposal']], guest,
                                     root / row['id'], bank, work, True)
        records.append({'id': row['id'], 'public': receipt['public'], 'validated': receipt['validated'],
                        'digest': receipt['digest'], 'proposals': calls,
                        'experience': receipt.get('repair_experience', [])})
    retained = load_bank(bank)
    if len(retained) != len(rows) or not all(entry.get('repair_experience') for entry in retained):
        raise ValueError('failed to seed bank with qualified donor corrections')
    return records


def cli_trial(name, task, checkout, sdk, bank, root):
    value, expected = CLI_CASES[name]
    if any(row['input'] == value for key in ('examples', 'validation', 'jobs') for row in task['spec'][key]):
        raise ValueError('terminal reuse input overlaps acquisition')
    prompt = 'Run ' + name + ' with ' + json.dumps(value)
    env = {**os.environ, 'HIVE_PYTHON': sys.executable, 'HIVE_BANK': str(bank),
           'HIVE_FIELDWORK_SDK': str(sdk), 'AGENT_TEAM_HOME': str(root / 'home'),
           'HIVE_TERNARY_BIN': str(root / 'missing-model-binary'), 'HIVE_MEMBERS': '',
           'HIVE_URL': 'http://127.0.0.1:1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    out = subprocess.run(['./hive', '--once', prompt], cwd=checkout, env=env, capture_output=True,
                         text=True, timeout=60)
    first = out.stdout.splitlines()[:1]
    return {'prompt': prompt, 'expected': expected, 'exit': out.returncode, 'stdout': out.stdout,
            'stderr': out.stderr, 'correct': out.returncode == 0 and first == [str(expected)]}


def grade(task, guest, root, donor_bank, name, learn, work, checkout, sdk):
    bank = root / 'bank'
    shutil.copytree(donor_bank, bank)
    out = root / 'work'
    receipts, calls = run_sources(task['spec'], [row['source'] for row in task['history']],
                                 guest, out, bank, work, learn)
    selected = {key: receipts[key] for key in ('digest', 'public', 'validated', 'parents', 'repair_search',
                'learned_repair', 'arithmetic_repair', 'decoded_input_repair') if key in receipts}
    results = []
    for spec_job, answer in zip(task['spec']['jobs'], task['fresh_expected'], strict=True):
        if spec_job['input'] != answer['input']:
            raise ValueError('fresh oracle/input mismatch')
        artifact = out / spec_job['id'] / spec_job['snapshot_file']
        if artifact.is_file():
            actual = json.loads(artifact.read_bytes())
            matches = json.dumps(actual, sort_keys=True) == json.dumps(answer['output'], sort_keys=True)
            results.append({'id': spec_job['id'], 'correct': matches, 'value': actual})
        else:
            results.append({'id': spec_job['id'], 'correct': False})
    correct = sum(r['correct'] for r in results)
    delivered = sum('value' in r for r in results)
    record = {'proposals': calls, 'receipt': selected, 'correct': correct, 'wrong_delivered': delivered - correct,
              'withheld': len(results) - delivered, 'outcomes': results,
              'solver': (out / 'solver.py').read_text() if (out / 'solver.py').is_file() else None}
    if delivered == len(results):
        record['cli'] = cli_trial(name, task, checkout, sdk, bank, root)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=HERE.parents[3], help='repository with ordinary hive CLI')
    parser.add_argument('--engine', type=Path, help='optional checkout containing selected fieldwork engine')
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='JSON results, optionally .gz')
    args = parser.parse_args()
    checkout, sdk = args.checkout.resolve(), args.sdk.resolve()
    engine = (args.engine or checkout).resolve()
    sys.path[:0] = [str(engine), str(checkout)]
    from training.experiments.fieldwork.guest import Guest
    from training.experiments.fieldwork.work import load_bank, work
    evidence = (HERE / 'evidence.json.gz').read_bytes()
    if sha(evidence) != LIVE_SHA:
        raise ValueError('live corpus changed')
    dataset = json.loads(gzip.decompress(evidence))
    engine_hashes = {name: sha((engine / 'training/experiments/fieldwork' / name).read_bytes()) for name in
                     ('work.py', 'repair_learning.py', 'decoded_input_repair.py', 'arithmetic_repair.py', 'guest.py')}
    report = {'engine_sha256': engine_hashes, 'wasi_sha256': sha((sdk / 'python.wasm').read_bytes()),
              'live_sha256': LIVE_SHA, 'donor_stream_sha256': DONOR_SHA, 'repair_budget': LIMIT,
              'replay_model_calls': 0, 'arms': {}}
    guest = Guest(sdk)
    with tempfile.TemporaryDirectory(prefix='hive-native-transfer-') as directory:
        root = Path(directory)
        warm = root / 'donors'
        warm.mkdir()
        report['donors'] = train(guest, warm, root / 'training', work, load_bank)
        baseline = {}
        for name in CLI_CASES:
            saved = dataset['tasks'][name]
            native = saved['native']
            baseline[name] = {'public': saved['replay']['public'], 'validated': native['qualification'],
                              'correct': native['jobs'], 'wrong_delivered': 0,
                              'withheld': native['jobs_total'] - native['jobs']}
        report['recorded_stock'] = baseline
        for arm, learn in [('fixed_only', False), ('fixed_and_learned', True)]:
            report['arms'][arm] = {}
            for name in CLI_CASES:
                record = grade(dataset['tasks'][name], guest, root / arm / name, warm, name, learn, work, checkout, sdk)
                report['arms'][arm][name] = record
                print(arm, name, record['correct'], 'correct,', record['wrong_delivered'], 'wrong,',
                      record['withheld'], 'withheld;', 'CLI', record.get('cli', {}).get('correct'), flush=True)
    output = json.dumps(report, indent=2, ensure_ascii=False).encode() + b'\n'
    if args.output.suffix == '.gz':
        output = gzip.compress(output, mtime=0)
    args.output.write_bytes(output)


if __name__ == '__main__':
    main()
