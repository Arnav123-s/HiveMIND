"""Replay two real CPU writer corrections and measure transfer with generation disabled."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ORDER_SHA = '712816ee42c9f507eac4e2e1385b6736f36009a8db6f41e04031f6a452e1eec6'
GRADING_SHA = 'f70ea34c580604447cd04dd1b7c5ca9655b18152d29bd704f9bf5e59162b1bc2'


def read(name, expected=None):
    data = gzip.decompress((HERE / (name + '.json.gz')).read_bytes())
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'{name} differs from the frozen data')
    return json.loads(data)


def summary(workdir, receipt, answers):
    outcomes = []
    for index, expected in enumerate(answers):
        path = workdir / f'job{index}' / 'answer.json'
        result = {'job': index}
        if path.is_file():
            actual = json.loads(path.read_bytes())
            result.update(actual=actual, correct=type(actual) is type(expected['output']) and actual == expected['output'])
        outcomes.append(result)
    delivered = sum('actual' in row for row in outcomes)
    right = sum(row.get('correct', False) for row in outcomes)
    evidence = {key: receipt[key] for key in ('digest', 'public', 'validated', 'repair_experience',
                'learned_repair', 'arithmetic_repair', 'decoded_input_repair', 'status',
                'repair_search', 'prior_searches', 'admission') if key in receipt}
    return {'receipt': evidence, 'correct': right, 'wrong_delivered': delivered - right,
            'withheld': len(answers) - delivered, 'jobs': outcomes,
            'solver': (workdir / 'solver.py').read_text() if (workdir / 'solver.py').exists() else None}


def replay(corpus, traces, keys, guest, work, repair_learning, directory):
    donors, targets = {}, {}
    for name, order in corpus.items():
        if order['phase'] != 'donor':
            continue
        history = traces[name]
        used = []
        def recorded(task, prefix, prior):
            turn = history[len(used)]
            expected = [turn['task'], turn['examples'], turn['prefix'], turn['earlier']]
            observed = [task.text, task.example, prefix, list(prior) if prior is not None else None]
            if expected != observed:
                raise ValueError(f'{name}: recorded model context changed before attempt {len(used)}')
            used.append(turn['response']['writer'])
            return turn['response']
        root = directory / name
        receipt = work.work(order['spec'], guest, recorded, root/'work', root/'bank', rounds=3, repair_budget=2)
        if len(used) != len(history):
            raise ValueError(f'{name}: not all recorded attempts were used')
        donors[name] = summary(root/'work', receipt, keys[name])
        donors[name]['writers'] = used
        donors[name]['qualified_workers'] = work.load_bank(root/'bank')
    def donate(target_bank, name):
        for worker in donors[name]['qualified_workers']:
            work.admit(target_bank, worker)

    for name, order in corpus.items():
        if order['phase'] == 'donor':
            continue
        root = directory / name
        bank, out = root/'bank', root/'work'
        calls = []
        def seed(*args):
            calls.append('authored_failed_draft')
            return {'source': order['source'], 'usage': {'completion_tokens': 0}, 'writer': calls[-1],
                    'seconds': 0, 'stop': 'frozen_source'}
        stages = {}
        initial = work.work(order['spec'], guest, seed, out, bank, rounds=1, repair_budget=2)
        stages['zero_donors'] = summary(out, initial, keys[name])
        for i, donor_name in enumerate(donors, 1):
            donate(bank, donor_name)
            policy = repair_learning.learn(work.load_bank(bank))
            receipt = work.work(order['spec'], guest, None, out, bank, rounds=1, repair_budget=2)
            stage = summary(out, receipt, keys[name])
            stage['active_rules_before_work'] = policy['rules']
            stages[f'after_donor_{i}'] = stage
        disabled_bank, disabled_out = root/'fixed-bank', root/'fixed-work'
        for donor_name in donors:
            donate(disabled_bank, donor_name)
        baseline = work.work(order['spec'], guest, seed, disabled_out, disabled_bank,
                             rounds=1, repair_budget=2, learn_repairs=False)
        stages['fixed_only_full_bank'] = summary(disabled_out, baseline, keys[name])
        if calls != ['authored_failed_draft', 'authored_failed_draft']:
            raise ValueError(f'{name}: unexpected proposal count')
        targets[name] = stages
    return {'donors': donors, 'targets': targets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--checkout', type=Path, default=HERE.parents[3])
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    sys.path.insert(0, str(checkout))
    from training.experiments.fieldwork import work, repair_learning
    from training.experiments.fieldwork.guest import Guest
    corpus, traces, gold = read('orders', ORDER_SHA), read('native-traces'), read('keys', GRADING_SHA)
    with tempfile.TemporaryDirectory(prefix='native-donor-replay-') as folder:
        report = replay(corpus, traces, gold, Guest(args.sdk.resolve()), work, repair_learning, Path(folder))
    report['engine_sha256'] = {src.name: hashlib.sha256(src.read_bytes()).hexdigest() for src in
                               (Path(work.__file__), Path(repair_learning.__file__))}
    for name, stages in report['targets'].items():
        for label, row in stages.items():
            print(name, label, row['correct'], 'correct,', row['wrong_delivered'], 'wrong,', row['withheld'], 'withheld')
    result = json.dumps(report, indent=2).encode() + b'\n'
    args.output.write_bytes(gzip.compress(result, mtime=0) if args.output.suffix == '.gz' else result)


if __name__ == '__main__':
    main()
