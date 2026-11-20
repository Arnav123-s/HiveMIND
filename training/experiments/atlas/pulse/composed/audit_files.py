"""Independently re-execute both shipped modules on the existing 50 official and 60 external inputs."""
import argparse
import gzip
import inspect
import json
from pathlib import Path
import random

from score import HERE, MODULES, digest, exam
from holdout import cases
from recover import execute
from training.experiments.fieldwork.guest import Guest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    guest = Guest(args.sdk)
    rows = json.loads(gzip.decompress((HERE/'checkpoint.json.gz').read_bytes()))
    scored = []
    for row in rows:
        receipt = row.get('recovery')
        if not receipt:
            continue
        seed, index = map(int, row['id'][1:].split('_'))
        kind = row['kind']
        task = exam.remake(kind, f'{seed}:{kind}:{index}:0')
        assert task[2] == row['prompt']
        details = inspect.getclosurevars(task[3]).nonlocals
        generator = random.Random('hidden:' + str(details['seed']))
        official = [(name, args[0], ref(*args)) for name, _, ref, draw in details['fns']
                    for args in (draw(generator) for _ in range(25))]
        external = cases()
        assert len(official) == 50 and len(external) == 60
        folder = MODULES / row['generation'] / row['id']
        code = (folder/'durations.py').read_bytes()
        assert digest(code) == receipt['module_sha256']
        visible = (folder/'REPORT.md').read_text().splitlines()
        ordered = official + external
        actual, fuel, _ = execute(guest, code.decode(), [(n,arg) for n,arg,_ in ordered])
        matches = [type(v) is type(case[2]) and v == case[2] for v,case in zip(actual,ordered,strict=True)]
        scored.append({'id':row['id'], 'module_sha256':digest(code), 'visible_lines':visible,
                       'visible_exact':visible == [str(v) for v in details['want']],
                       'official_matches':sum(matches[:50]),'official_total':50,
                       'external_matches':sum(matches[50:]),'external_total':60,
                       'output_sha256':digest(json.dumps(actual,separators=(',',':')).encode()),
                       'grader_only_guest_batches':1,'grader_only_fuel':fuel})
    assert len(scored) == 2
    args.output.write_text(json.dumps(scored,indent=2)+'\n')
    print(json.dumps(scored))


if __name__ == '__main__':
    main()
