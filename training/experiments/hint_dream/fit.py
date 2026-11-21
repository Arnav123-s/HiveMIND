"""Fit one #131 CPU SFT epoch on the checked native synthetic rows from completed panels."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from training.experiments.hint_dream.pilot import ASSETS

G55_PARENT = "6d2b50f593941b73e564286a3889768948bf539fec5517c6b884cd2c390d0ab0"


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def checked_rows(folder):
    rec = json.loads((folder / "results.json").read_text())
    if not rec['complete'] or rec.get('panel', 'initial') == 'transfer' or rec['assets'] != ASSETS:
        raise ValueError(f"Unexpected source panel {folder}")
    wanted = [p['spec'] for p in rec['pairs'] if not p['blind']['ok'] and p['hinted']['ok'] and p['admitted']]
    rows_file = folder / 'rows.jsonl'
    rows = [json.loads(line) for line in rows_file.read_text().splitlines()] if rows_file.exists() else []
    if wanted != [row['seed'] for row in rows]:
        raise ValueError("Exported rows disagree with paired verification")
    if any(not row['hint_regret'] or row['type'] != 'first' or 'Implementation hint:' in str(row['messages']) for row in rows):
        raise ValueError("Unexpected SFT row")
    return rows_file, len(rows)


def fit(args):
    from training import grow
    from safetensors import safe_open
    import torch
    sources = [checked_rows(folder) for folder in args.panels]
    count = sum(n for _, n in sources)
    if not count or digest(args.parent) != G55_PARENT:
        raise ValueError("A checked training row and the exact G55 starting weights are required")
    args.out.mkdir(parents=True, exist_ok=False)
    grow.GROW = args.out / 'grow'
    rows = args.out / 'gathered.jsonl'
    if grow.gather(rows, 'f4pilot', new=[path for path, _ in sources]) != (0, count):
        raise ValueError("Duplicate or missing training rows")
    inherited = []

    def log(msg, **kwargs):
        print(msg, **kwargs)
        if msg.startswith('the child starts as its parent ('):
            if '98 of its matrices inherited' not in msg:
                raise RuntimeError('Partial parent inheritance')
            inherited.append(msg)

    started = time.monotonic()
    result = grow.train(rows, name='f4hintdream', base='t80', epochs=1, rank=32, lr=0.0002, max_len=1152,
                        layers='last14', accum=1, seed=56, lean='code', checkpoint=False, int8_base=True,
                        gen='f4pilot', parent=str(args.parent), parent_cell='g55trunk', out_dir=args.out/'exports', log=log)
    if not inherited or result['used'] != count or result['steps'] != count or not math.isfinite(result['loss_last']):
        raise RuntimeError('The worker did not train each admitted row')
    child = grow.GROW / 't80+f4hintdream' / 'adapter_model.safetensors'
    with safe_open(args.parent, framework='pt', device='cpu') as a, safe_open(child, framework='pt', device='cpu') as b:
        if len(a.keys()) != 196 or set(a.keys()) != set(b.keys()):
            raise RuntimeError('Candidate parameters differ from the inherited architecture')
        changed = sum(not torch.equal(a.get_tensor(k), b.get_tensor(k)) for k in a.keys())
    if not changed:
        raise RuntimeError('No weights changed in training')
    result.update(elapsed_seconds=round(time.monotonic() - started, 2), admitted=count, changed_tensors=changed,
                  source_sha256={f.name: digest(f/'results.json') for f in args.panels}, parent_sha256=G55_PARENT,
                  rows_sha256=digest(rows), gguf_sha256=digest(Path(result['file'])), safetensors_sha256=digest(child))
    (args.out/'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panels', type=Path, nargs='+', required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    os.environ.update(HF_HUB_OFFLINE='1', HIVE_GPU='0', HIVE_KEEP_BACK='0', HIVE_PREFIX_CACHE='0',
                      AGENT_TEAM_THREADS='2', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='1',
                      HIVE_CHUNK_CE='128', HIVE_ROW_CHECKPOINT='1')
    fit(parser.parse_args())
