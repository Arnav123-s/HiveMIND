"""Run from any directory with Python 3. No model or third-party packages needed."""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from team import cache_lines


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric_panel():
    rng = random.Random(481903)
    totals = dict(inputs=0, matched=0, wrong=0, declined=0)
    sizes = (1, 2, 3, 4, 7, 8, 16, 24, 32, 48, 63, 64, 96, 128, 256, 512)
    for i in range(2048):
        size = sizes[i % len(sizes)]
        base = rng.randrange(2**44) * size
        start = base + rng.choice((0, 1, size - 1, rng.randrange(size)))
        width = rng.choice((1, size, size + 1, 2 * size, 3 * size - 1, rng.randrange(1, 8 * size + 1)))
        address = hex(start) if i % 2 else str(start)
        prompt = (f'With aligned {size}-byte cache lines, a {width}-byte read starts at address {address}. '
                  'How many distinct lines does the access touch? Reply with just the integer.')
        actual = cache_lines.answer(prompt)
        # Enumerate every touched byte. This never uses the implementation's interval-count formula.
        lines = {address // size for address in range(start, start + width)}
        totals['inputs'] += 1
        if actual is None:
            totals['declined'] += 1
        elif (actual['text'], actual['cache_lines']['first_line'], actual['cache_lines']['last_line']) == (
                str(len(lines)), min(lines), max(lines)):
            totals['matched'] += 1
        else:
            totals['wrong'] += 1
    return totals


def ordinary(prompt):
    result = subprocess.run([str(ROOT/'hive'), '--once', prompt], cwd=ROOT,
                            env=dict(os.environ, HIVE_PYTHON=sys.executable, HIVE_BANK='off'),
                            text=True, capture_output=True, check=True)
    return result.stdout.strip()


def main():
    cases = json.loads((HERE/'cases.json').read_text())
    keys = json.loads((HERE/'keys.json').read_text())
    results = []
    for case in cases:
        output = cache_lines.answer(case['prompt'])
        key = keys[case['id']]
        # Use the ordinary CLI only when the formula claims the task. Calling a model on a declined case is outside this audit.
        cli = ordinary(case['prompt']) if output else None
        correct = cli == str(key['expected']) if key['eligible'] else output is None
        results.append(dict(id=case['id'], eligible=key['eligible'], expected=key['expected'],
                            output=cli, correct=correct, calculation=output and output['cache_lines']))
    old = ('A processor uses 64-byte cache lines aligned at addresses divisible by 64. A four-byte load begins '
           'at byte address 62. How many distinct cache lines contain these four bytes? Reply with a single integer.')
    retrospective = cache_lines.answer(old)
    report = dict(method='handwritten model-free aligned byte interval; no fitted parameters',
                  retrospective=dict(expected=2, observed_old_worker_outputs=['1','1'],
                                     local_answer=retrospective['text'], ordinary_cli=ordinary(old), check=retrospective['cache_lines']),
                  independent_prose=dict(results=results, eligible_solved=sum(x['eligible'] and x['correct'] for x in results),
                                         eligible=sum(x['eligible'] for x in results),
                                         ineligible_declined=sum(not x['eligible'] and x['correct'] for x in results),
                                         ineligible=sum(not x['eligible'] for x in results),
                                         all_wrong_numeric_answers=sum(x['output'] is not None and not x['correct'] for x in results)),
                  fixed_grammar_numeric_sweep=numeric_panel(),
                  sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'team/cache_lines.py', HERE/'cases.json', HERE/'keys.json',
                                                                     HERE/'protocol.md')})
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
