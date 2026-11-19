"""Run the sealed eight-case delivery test with simulated model and worker outputs."""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
CASES_SHA256 = '369e0fa7156199f6ac879cc8774bbcf1c6be7dcc29376638be9e91bbe4e3f628'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delivered_phase(text):
    # Score the displayed answer independently of the production verifier.
    match = re.fullmatch(r'(?:(?:the water|it) is )?(solid|liquid|gas)[.!]?', text.strip(), re.I)
    return match.group(1).lower() if match else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=HERE.parents[5])
    parser.add_argument('--cases', type=Path, default=HERE/'cases.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if digest(args.cases) != CASES_SHA256:
        raise ValueError('Sealed case bytes differ')
    root = args.checkout.resolve()
    sys.path.insert(0, str(root))
    os.environ.update(HIVE_BANK='off', HIVE_SIGNALS='1', HIVE_ENGRAMS='1',
                      HIVE_ENGRAMS_HOME=str(root/'cells/engrams'))
    from team import domain_advice, solo, talk, ternary, water_phase

    result = {'cases_sha256': CASES_SHA256, 'actual_model_generations': 0,
              'source_sha256': {m.__name__: digest(Path(m.__file__)) for m in (domain_advice, solo, talk, water_phase)},
              'cases': []}
    with tempfile.TemporaryDirectory(prefix='hive-water-delivery-') as tempdir:
        for row in json.loads(args.cases.read_bytes()):
            prompt = row['text']
            expected = row['expected_phase']
            case = {'id': row['id'], 'expected_phase': expected, 'arms': {}}
            for arm, proposed in [('conflict', row['worker']), ('ordinary', row['ordinary_answer'])]:
                cases_by_route = case['arms'][arm] = {}
                for route in ('talk', 'work'):
                    messages = [{'role': 'user', 'content': prompt}]
                    worked = {'agreed': True, 'report': proposed + '\n## How it was checked\nControlled worker agreement.', 'files': []}
                    with (patch.object(talk, 'route', return_value=(route, messages)),
                          patch.object(solo, 'first', return_value=worked) as worker,
                          patch.object(ternary, 'chat', return_value=proposed) as chat):
                        reply = talk.reply(prompt, base='t80', run_dir=Path(tempdir)/row['id']/arm/route)
                    text = reply['text']
                    check = reply.get('water_phase_check')
                    if expected is not None:
                        passed = delivered_phase(text) == expected
                    else:
                        passed = text == proposed and check is None
                    cases_by_route[route] = {'injected': proposed, 'text': text, 'phase_check': check,
                                             'agreed': reply.get('agreed'), 'worked': reply['worked'],
                                             'synthetic_worker_calls': worker.call_count,
                                             'synthetic_chat_calls': chat.call_count, 'passed': passed}
            result['cases'].append(case)

    result['passing_cases_both_routes'] = {
        group: {
            arm: sum(all(v['passed'] for v in row['arms'][arm].values()) for row in result['cases']
                     if (row['expected_phase'] is not None) == eligible)
            for arm in ('conflict', 'ordinary')}
        for group, eligible in [('eligible', True), ('excluded', False)]}
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
