"""Capture the genuine first member turn, training-history resemblance and frozen scaffold per task."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from team import memory, solo

HERE = Path(__file__).resolve().parent
DATE = '2026-11-21 (Saturday)'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(task, short):
    class Captured(Exception):
        pass
    def intercept(who, messages, **kwargs):
        raise Captured(messages)
    correct_env = {'HIVE_SHORT_ORDERS': str(int(short)), 'HIVE_FULL_ORDERS': str(int(not short)),
                   'HIVE_LIBRARY': '0', 'HIVE_NOTES': '0'}
    orders = solo.orders
    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, correct_env), \
         patch.object(solo, 'orders', lambda who: orders(who, DATE)), patch.object(solo.ternary, 'chat', intercept):
        try:
            solo.member(task, 1, None, None, Path(temp), 0., who='t80+g55trunk', also=())
        except Captured as found:
            return found.args[0]
        raise RuntimeError('member ended before first native request')


def prepare(training_rows, scaffold, dest):
    spec = importlib.util.spec_from_file_location('frozen_scaffolds', scaffold)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert sha(scaffold.read_bytes()) == 'b150c0e0095a5f0548fb411f90fd04b2804c1c5729869bcd7a77c0c72b5dfa82'
    assert sha(scaffold.with_name('bank.json').read_bytes()) == '2bf73f572fb764b5b2091928a8ec9a3bd94970ee177430d4485b8dc6dace1075'
    rows = [json.loads(line) for line in training_rows.read_text().splitlines()]
    history = {r['task'] for r in rows if r.get('type') == 'first' and r.get('task')}
    previous = [(t, memory.words(t)) for t in sorted(history)]
    panel = json.loads((HERE/'panel.json').read_bytes())
    assert sha((HERE/'panel.json').read_bytes()) == '6de40e99d162efe5897c6486d897cebf1f694038755d9f14cf772d4b713c8350'
    data = {'orders': {}, 'rows': [], 'history_count': len(history), 'training_rows_sha256': sha(training_rows.read_bytes())}
    for r in panel:
        task = r['task']
        short, full = capture(task, True), capture(task, False)
        assert short[1] == full[1] and len(short) == len(full) == 2
        assert short[0]['content'] == solo.SHORT.format(today=DATE) and full[0]['content'] == solo.MEMBER.format(today=DATE)
        for name, messages in [('short', short), ('full', full)]:
            data['orders'][name] = messages[0]['content']
        assert task not in history
        words = memory.words(task)
        score, near = max((len(words & old)/max(1, len(words | old)), t) for t,old in previous)
        data['rows'].append({'id':r['id'], 'group':r['group'], 'user':short[1]['content'], 'scaffold':module.render(task),
                             'gate':'short' if score >= .30 else 'full', 'nearest':near, 'jaccard':round(score,6)})
    dest.write_text(json.dumps(data, sort_keys=True,indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('training_rows', type=Path)
    p.add_argument('scaffold', type=Path)
    p.add_argument('dest', type=Path)
    a = p.parse_args()
    prepare(a.training_rows,a.scaffold,a.dest)
