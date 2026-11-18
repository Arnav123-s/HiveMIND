"""Replay six predeclared invoice requests through the real fieldwork CLI and WASI.

Use the current checkout's virtualenv. Pass --checkout to run a historical version
of the application, --sdk to select the WASI SDK, and redirect stdout to JSON.
The candidate code and independent keys are in work-order-cases.json.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


CASES = Path(__file__).resolve().parents[1] / 'reports/retained-skills/work-order-cases.json'


def read(path):
    return json.loads(path.read_bytes())


def bank_digests(bank):
    return {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(bank.glob('*.json'))}


def examples(rows):
    return [{'input': {'lines': cents}, 'output': tax} for cents, tax in rows]


def order(fixture, validation, batch=None):
    amounts = fixture['batches'][batch] if batch else []
    return {'name': fixture['name'], 'task': fixture['description'],
            'examples': examples(fixture['public']), 'validation': examples(fixture['validation'][validation]),
            'jobs': [{'id': f'bill-{i}', 'input': {'lines': row}, 'snapshot_file': 'tax.json'}
                     for i, row in enumerate(amounts, 1)]}


def inject(source, calls):
    """An explicitly authored fixture program supplied at the normal generate-candidate boundary."""
    def ask(*args, **kwargs):
        calls.append(True)
        return {'source': source, 'usage': {'completion_tokens': 0}, 'seconds': 0, 'stop': 'fixture'}
    return ask


def qualify(fixture, root, guest, work, bank):
    rows = []
    bank.mkdir()
    for convention in ('per_line', 'per_invoice'):
        # Each program must pass its own work order before it joins the shared bank.
        slice_dir = root / convention
        fresh_bank = slice_dir / 'qualified'
        calls = []
        receipt = work(order(fixture, convention), guest, inject(fixture['programs'][convention], calls),
                       slice_dir / 'order', fresh_bank, rounds=1)
        assert calls == [True] and receipt['validated'] == receipt['validation_total'] == 2
        record = fresh_bank / (receipt['digest'] + '.json')
        shutil.copyfile(record, bank / record.name)
        rows.append({'convention': convention, 'digest': receipt['digest'], 'public': receipt['public'],
                     'validation': receipt['validated'], 'scripted_proposals': len(calls)})
    return rows


def run_order(checkout, sdk, root, fixture, visit, bank):
    base = root / visit['id']
    base.mkdir()
    spec = order(fixture, visit['validation'], visit['batch'])
    spec_path, out = base / 'order.json', base / 'out'
    spec_path.write_text(json.dumps(spec))
    before = bank_digests(bank)
    # Generation disabled, so a missed retrieval cannot silently query a language model.
    cmd = [str(checkout / 'hive'), 'fieldwork', '--spec', str(spec_path), '--sdk', str(sdk), '--out', str(out),
           '--bank', str(bank), '--rounds', '1']
    proc = subprocess.run(cmd, cwd=checkout, env=dict(os.environ, HIVE_PYTHON=sys.executable),
                          capture_output=True, text=True, timeout=240)
    path = out / 'receipt.json'
    receipt = read(path) if path.is_file() else {}
    files = {job['id']: read(out / job['id'] / 'tax.json') for job in spec['jobs'] if (out / job['id'] / 'tax.json').is_file()}
    expected = visit['expected']
    received = [files.get(job['id']) for job in spec['jobs']]
    if expected is None:
        ok = proc.returncode == 1 and bool(receipt) and not files and not receipt.get('jobs')
        if visit['id'] == 'inconclusive':
            ok = ok and receipt.get('status') == 'ambiguous_saved_versions'
    else:
        ok = received == expected and proc.returncode == 0
    return {'id': visit['id'], 'exit': proc.returncode, 'stdout': proc.stdout.strip(),
            'stderr_last_line': (proc.stderr.strip().splitlines() or [''])[-1],
            'files': files, 'expected_files_in_order': expected, 'decision_correct': ok,
            'selected_digest': receipt.get('digest'), 'status': receipt.get('status'),
            'public': receipt.get('public'), 'validated': receipt.get('validated'),
            'saved_checks': receipt.get('saved_checks', []),
            'bank_unchanged': before == bank_digests(bank), 'inference_calls': 0}


def run(checkout, sdk, root):
    sys.path.insert(0, str(checkout))
    from training.experiments.fieldwork.guest import Guest
    from training.experiments.fieldwork.work import work
    guest = Guest(sdk)
    f = read(CASES)
    bank = root / 'bank'
    qualified = qualify(f, root, guest, work, bank)
    before = bank_digests(bank)
    rows = []
    rejection = None
    for visit in f['visits']:
        rows.append(run_order(checkout, sdk, root, f, visit, bank))
        if visit['id'] == 'failed_revision':
            calls = []
            receipt = work(order(f, 'truncate', 'distinct'), guest, inject(f['programs']['wrong_revision'], calls),
                           root / 'supplied-revision', bank, rounds=1)
            rejection = {'scripted_proposals_requested': len(calls), 'model_calls': 0, 'public': receipt['public'],
                         'validation': receipt['validated'], 'jobs': receipt['jobs'],
                         'bank_unchanged': before == bank_digests(bank)}
    return {'revision': subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip(),
            'fieldwork_sha256': hashlib.sha256((checkout/'training/experiments/fieldwork/work.py').read_bytes()).hexdigest(),
            'case_sha256': hashlib.sha256(CASES.read_bytes()).hexdigest(),
            'wasi_python_sha256': hashlib.sha256((sdk/'python.wasm').read_bytes()).hexdigest(),
            'qualified_with_wasi': qualified, 'initial_bank': before, 'visits': rows,
            'scripted_failed_revision': rejection, 'final_bank': bank_digests(bank),
            'correct_visits': sum(r['decision_correct'] for r in rows), 'total_visits': len(rows),
            'real_model_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path.cwd())
    parser.add_argument('--sdk', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='retained-invoices-') as tmp:
        print(json.dumps(run(args.checkout.resolve(), args.sdk.resolve(), Path(tmp)), indent=2))


if __name__ == '__main__':
    main()
