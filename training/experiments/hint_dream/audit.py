"""Cross-check admitted programs on fresh inputs with an independent streaming reference."""
import argparse
import json
from pathlib import Path
import random

from training import hint_dream
from training.experiments.fieldwork.guest import Guest
from training.experiments.hint_dream.independent import streaming
from training.experiments.hint_dream.pilot import PANELS


def audit(folder, sdk):
    rec = json.loads((folder / 'results.json').read_text())
    seed, indexes = PANELS[rec.get('panel', 'initial')]
    if not rec['complete'] or len(rec['calls']) != 2 * len(indexes) or len(rec['pairs']) != len(indexes):
        raise ValueError('A completed paired panel is required')
    specs = list(hint_dream.draw(seed, max(indexes) + 1))
    guest = Guest(sdk)
    report = []
    for i, (idx, pair) in enumerate(zip(indexes, rec['pairs'], strict=True)):
        if not pair['admitted']:
            continue
        spec = specs[idx]
        rng = random.Random(f'fresh-program-audit-v1/{spec.seed}')
        samples = []
        for n in range(64):
            labels = rng.sample(('birch', 'cedar', 'oak', 'pine', 'ash', 'spruce', 'maple'), rng.randint(1, 6))
            values = [(rng.choice(labels), rng.randrange(spec.modulus)) for _ in range(n)]
            samples.append(hint_dream.encode(spec.form, values))
        wanted = [streaming(spec, x) for x in samples]
        grades = {"spec": spec.seed, "cases": len(samples)}
        for arm, call in zip(('blind','hinted'), rec['calls'][2*i:2*i+2], strict=True):
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
