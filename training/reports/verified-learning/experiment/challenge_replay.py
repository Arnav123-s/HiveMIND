"""Measure the withholding cost and benefit of challenging qualified programs."""
import argparse
from functools import partial
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile

from replay import corpus, digest, KEYS_SHA, retained, STREAM_SHA, visit


def read(path):
    body = path.read_bytes()
    if path.suffix == '.gz':
        body = gzip.decompress(body)
    return json.loads(body), digest(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path.cwd())
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--new-cases', type=Path)
    parser.add_argument('--new-keys', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if bool(args.new_cases) != bool(args.new_keys):
        parser.error('supply both files for a confirmation run')
    sys.path.insert(0, str(args.checkout.resolve()))
    from training.experiments.fieldwork.guest import Guest
    from training.experiments.fieldwork.work import load_bank, work

    stream = corpus('stream.json', STREAM_SHA)
    keys = corpus('sealed-keys.json', KEYS_SHA)
    extra_hashes = {}
    jobs = [job for job in stream.values() if job['phase'] in ('weak_checks', 'control')]
    if args.new_cases:
        additional, extra_hashes['cases'] = read(args.new_cases)
        extra_keys, extra_hashes['keys'] = read(args.new_keys)
        if additional.keys() != extra_keys.keys() or additional.keys() & stream.keys():
            raise ValueError('confirmation cases and keys have inconsistent or reused IDs')
        if any(row['id'] != key or row['phase'] != 'challenge_confirmation' or 'second_training_proposal' in row
               for key, row in additional.items()):
            raise ValueError('confirmation requires new single-draft orders')
        jobs.extend(additional.values())
        keys.update(extra_keys)

    guest = Guest(args.sdk)
    environment = {name: digest((args.checkout/'training/experiments/fieldwork'/name).read_bytes())
                   for name in ('challenge.py', 'work.py', 'repair_learning.py', 'guest.py')}
    report = {'original_stream_sha256': STREAM_SHA, 'original_keys_sha256': KEYS_SHA,
              'new_hashes': extra_hashes, 'engine': environment, 'model_calls': 0}
    with tempfile.TemporaryDirectory(prefix='hive-challenge-') as tmp:
        root = Path(tmp)
        bank = root / 'training-bank'
        bank.mkdir()
        calibration = [j for j in stream.values() if j['phase'] == 'train']
        report['training'] = [visit(job, keys[job['id']]['private'], guest, bank, root, work, load_bank, True)
                              for job in calibration]
        warm = retained(bank, load_bank)
        rows = {}
        for cap in (0, 2):
            arm = root / ('cap-' + str(cap))
            arm.mkdir()
            rows[str(cap)] = []
            for job in jobs:
                individual = arm / ('bank-' + job['id'])
                shutil.copytree(bank, individual)
                result = visit(job, keys[job['id']]['private'], guest, individual, arm,
                               partial(work, challenge_budget=cap), load_bank, True)
                if result['receipt'].get('challenge', {}).get('status') in ('ambiguous', 'inconclusive'):
                    if result['new_workers'] or any(not x.get('withheld') for x in result['outcomes']):
                        raise AssertionError('a disputed worker or job file was published')
                rows[str(cap)].append(result)
        report['bank'] = warm
        report['arms'] = rows
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    for cap, rows in report['arms'].items():
        for phase in dict.fromkeys(row['phase'] for row in rows):
            selected = [r for r in rows if r['phase'] == phase]
            totals = [sum(r[k] for r in selected) for k in ('fully_correct','correct','wrong_delivered','withheld')]
            print(cap, phase, totals)


if __name__ == '__main__':
    main()
