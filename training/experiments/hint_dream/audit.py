"""Cross-check admitted programs on fresh inputs with an independent streaming reference."""
import argparse
import json
from pathlib import Path
import random

from training import hint_dream
from training.experiments.fieldwork.guest import Guest
from training.experiments.hint_dream.independent import streaming
from training.experiments.hint_dream.pilot import scheduled


def audit(folder, sdk):
    rec = json.loads((folder / 'results.json').read_text())
    panel = rec.get('panel', 'initial')
    if panel not in ('initial', 'confirmation', 'trained'):
        raise ValueError('This audit applies to original teaching pairs and unhinted seen-task retests')
    specs = scheduled(panel)
    if 'retest_index' in rec:
        specs = [specs[rec['retest_index']]]
    arms = ('after_training',) if panel == 'trained' else ('blind', 'hinted')
    if not rec['complete'] or len(rec['calls']) != len(arms) * len(specs) or len(rec['pairs']) != len(specs):
        raise ValueError('A complete panel is required')
    guest = Guest(sdk)
    report = []
    for i, (spec, pair) in enumerate(zip(specs, rec['pairs'], strict=True)):
        if pair['spec'] != spec.seed:
            raise ValueError('Recorded exercise differs from registration')
        if panel != 'trained' and not pair['admitted']:
            continue
        rng = random.Random(f'fresh-program-audit-v1/{spec.seed}')
        samples = []
        for n in range(64):
            labels = rng.sample(('birch', 'cedar', 'oak', 'pine', 'ash', 'spruce', 'maple'), rng.randint(1, 6))
            values = [(rng.choice(labels), rng.randrange(spec.modulus)) for _ in range(n)]
            samples.append(hint_dream.encode(spec.form, values))
        wanted = [streaming(spec, x) for x in samples]
        grades = {"spec": spec.seed, "cases": len(samples)}
        calls = rec['calls'][len(arms) * i:len(arms) * (i + 1)]
        for arm, call in zip(arms, calls, strict=True):
            source = hint_dream.extract_code(call['raw'])
            results, _, _ = guest.run(source, samples)
            grades[arm] = sum('value' in r and json.dumps(r['value'], sort_keys=True) == json.dumps(y, sort_keys=True)
                              for r, y in zip(results, wanted, strict=True))
        report.append(grades)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.panel, args.sdk), indent=2))
