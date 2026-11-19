"""Replay the frozen authored repair-selection study in the production fieldwork runner.

    python path/to/replay.py --checkout . --sdk path/to/wasi --output results.json

Python requires Wasmtime. The 75 public examples and 105 separate validation examples
are available to the application. The oracle for the 300 private outputs and 48 revisits
is used only by this grading process, after work() returns.
"""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import inspect
import importlib.metadata
import platform
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent
STREAM_SHA = 'ce5e53820974099e91c1cd2feb554bd97d886cc9150e0365cd328918095a036c'
KEYS_SHA = 'f0c4f542b16152e53a7151350ea63419371ba5b5e707567d48fc738b69fcf47e'
LIMIT = 2


def digest(data):
    return hashlib.sha256(data).hexdigest()


def corpus(name, sha):
    content = gzip.decompress((HERE / (name + '.gz')).read_bytes())
    if digest(content) != sha:
        raise ValueError(f'frozen {name} does not match')
    return json.loads(content)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class Meter:
    def __init__(self, guest, spec):
        self.guest = guest
        groups = {name: [r['input'] for r in spec[key]] for name, key in
                  [('public', 'examples'), ('validation', 'validation'), ('jobs', 'jobs')]}
        self.groups = {canonical(items): name for name, items in groups.items()}
        self.calls = []

    def run(self, program, inputs, **kwargs):
        start = time.monotonic()
        result = self.guest.run(program, inputs, **kwargs)
        self.calls.append({'stage': self.groups.get(canonical(inputs), 'other'), 'inputs': len(inputs),
                           'seconds': round(time.monotonic() - start, 4), 'program_sha256': digest(program.encode())})
        return result


def retained(bank, load_bank):
    return sorted((row['task'], row['digest']) for row in load_bank(bank))


def final_solve(source):
    if not source:
        return None
    functions = [s for s in ast.parse(source).body if isinstance(s, ast.FunctionDef) and s.name == 'solve']
    return ast.unparse(functions[-1]) if functions else None


def visit(job, private, guest, bank, root, work, load_bank, enabled, *, revisit=False):
    # No expected private output goes into the work order or the proposal callback.
    spec = {'name': job['id'], 'task': job['prompt'], 'examples': job['public'], 'validation': job['validation'],
            'jobs': [{'id': 'input-' + str(i), 'input': row['input'], 'snapshot_file': 'answer.json'}
                     for i, row in enumerate(private)]}
    proposals = [job['source']]
    if 'second_training_proposal' in job:
        proposals.append(job['second_training_proposal'])
    consumed = []
    def ask(*_args, **_kwargs):
        idx = len(consumed)
        src = proposals[idx]
        consumed.append(digest(src.encode()))
        return {'source': src, 'usage': {'completion_tokens': 0}, 'seconds': 0, 'stop': 'authored_fixture'}
    measured = Meter(guest, spec)
    before = set(retained(bank, load_bank))
    out = root / ('revisit-' + job['id'] if revisit else job['id'])
    start = time.monotonic()
    receipt = work(spec, measured, None if revisit else ask, out, bank,
                   rounds=len(proposals) if not revisit else 1, repair_budget=LIMIT, learn_repairs=enabled)
    wall = time.monotonic()-start
    after = set(retained(bank, load_bank))
    est = []
    for i, row in enumerate(private):
        path = out / ('input-' + str(i)) / 'answer.json'
        if path.is_file():
            actual = json.loads(path.read_bytes())
            est.append({'correct': canonical(actual) == canonical(row['output']), 'actual': actual})
        else:
            est.append({'correct': False, 'withheld': True})
    good = sum(row['correct'] for row in est)
    withheld = sum(row.get('withheld',False) for row in est)
    solved = (out / 'solver.py').read_text() if (out/'solver.py').exists() else None
    summary_receipt = {k:v for k,v in receipt.items() if k not in ('attempts','jobs','source','program')}
    return dict(id=job['id'], phase='revisit' if revisit else job['phase'], group=job.get('group'),
                private_rows=len(private), correct=good,
                withheld=withheld, wrong_delivered=len(private)-good-withheld, fully_correct=good==len(private),
                final_solve_unchanged=final_solve(solved)==final_solve(job['source']),
                selected_solve=final_solve(solved),
                solver_file_sha256=digest(solved.encode()) if solved is not None else None,
                new_workers=sorted(after-before), prior_workers_lost=sorted(before-after), proposals=consumed,
                actual_model_calls=0, elapsed_seconds=round(wall,4), wasm_calls=measured.calls, receipt=summary_receipt,
                outcomes=est)


def arm(label, enabled, jobs, keys, guest, work, load_bank, root):
    root.mkdir()
    warm = root / 'trained'
    warm.mkdir()
    train = [j for j in jobs.values() if j['phase']=='train']
    novel = [j for j in jobs.values() if j['phase']!='train']
    rows=[]
    for job in train:
        rows.append(visit(job,keys[job['id']]['private'],guest,warm,root,work,load_bank,enabled))
    train_digest = retained(warm,load_bank)
    # Each held-out choice gets the identical post-training evidence, eliminating test-to-test carryover.
    # Keep the last tested snapshot on which a new correct skill was actually added for revisiting earlier work.
    retention = warm
    for job in novel:
        bank = root / ('bank-'+job['id'])
        shutil.copytree(warm,bank)
        row = visit(job,keys[job['id']]['private'],guest,bank,root,work,load_bank,enabled)
        rows.append(row)
        if job['phase'] in ('heldout','confirmation') and row['fully_correct'] and row['new_workers']:
            retention = bank
    for job in train:
        rows.append(visit(job,keys[job['id']]['revisit'],guest,retention,root,work,load_bank,enabled,revisit=True))
    summary={}
    for key in dict.fromkeys(r['phase'] for r in rows):
        sub=[r for r in rows if r['phase']==key]
        summary[key]={'contracts':len(sub),'complete':sum(r['fully_correct'] for r in sub),
                      **{k:sum(r[k] for r in sub) for k in ('private_rows','correct','wrong_delivered','withheld')},
                      'proposals':sum(len(r['proposals']) for r in sub),
                      'guest_executions':sum(len(r['wasm_calls']) for r in sub),
                      'guest_inputs':sum(c['inputs'] for r in sub for c in r['wasm_calls'])}
    return dict(label=label,trained_bank=train_digest,revisit_bank=retention.name,summary=summary,visits=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout',type=Path,default=Path.cwd())
    parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--confirmation-stream',type=Path,help='additional sealed contracts, each independently applied to a copy of the same training bank')
    parser.add_argument('--confirmation-keys',type=Path,help='private results for additional contracts, used only in this process after delivery')
    args=parser.parse_args()
    sys.path.insert(0,str(args.checkout.resolve()))
    from training.experiments.fieldwork.guest import Guest
    from training.experiments.fieldwork.work import work,load_bank
    if 'learn_repairs' not in inspect.signature(work).parameters:
        parser.error('requires the fieldwork learning implementation')
    jobs=corpus('stream.json',STREAM_SHA)
    keys=corpus('sealed-keys.json',KEYS_SHA)
    if bool(args.confirmation_stream) != bool(args.confirmation_keys):
        parser.error('supply both confirmation files')
    confirmation = {}
    if args.confirmation_stream:
        for source, field, destination in ((args.confirmation_stream,'stream',jobs), (args.confirmation_keys,'keys',keys)):
            data=source.read_bytes()
            if source.suffix=='.gz':data=gzip.decompress(data)
            confirmation[field+'_sha256']=digest(data)
            extra=json.loads(data)
            if destination.keys() & extra.keys():raise ValueError('repeated confirmation contract')
            if field=='stream' and any(c['phase']=='train' or 'second_training_proposal' in c for c in extra.values()):
                raise ValueError('confirmation contains a training proposal')
            destination.update(extra)
        if jobs.keys()!=keys.keys():raise ValueError('confirmation gold and contracts disagree')
    engine_paths = ['training/experiments/fieldwork/'+name for name in ('work.py','arithmetic_repair.py','repair_learning.py','guest.py')]
    adapter = 'training/experiments/fieldwork/decoded_input_repair.py'
    if (args.checkout/adapter).is_file():
        engine_paths.append(adapter)
    environment = dict(python=platform.python_version(), wasmtime=importlib.metadata.version('wasmtime'),
                       wasi_sha256=digest((args.sdk/'python.wasm').read_bytes()),
                       source_sha256={k:digest((args.checkout/k).read_bytes()) for k in engine_paths})
    guest=Guest(args.sdk); _=guest.runtime
    with tempfile.TemporaryDirectory(prefix='hive-repair-transfer-') as temp:
        arms=[arm(label,enabled,jobs,keys,guest,work,load_bank,Path(temp)/label) for label,enabled in
              [('no_learn',False),('learn',True)]]
    report=dict(source='synthetic worker drafts, zero model inference',environment=environment,repair_budget=LIMIT,stream_sha256=STREAM_SHA,
                private_sha256=KEYS_SHA,initial_human_corrections=4,confirmation=confirmation,arms=arms)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({a['label']:a['summary'] for a in arms},indent=2))


if __name__=='__main__':main()
