"""Inject sealed conflicting phase answers at the chat boundary; never start a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
PANEL_SHA = '4f8aef836c93711fee45db311213372d5f18f0d66ab15e7e2332d125364c6de8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=HERE.parents[4])
    parser.add_argument('--cases', type=Path, default=HERE/'cases.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.checkout.resolve()
    sys.path.insert(0, str(root))
    os.environ.update(HIVE_BANK='off', HIVE_ENGRAMS='1', HIVE_SIGNALS='1',
                      HIVE_ENGRAMS_HOME=str(root/'cells/engrams'))
    from team import domain_advice, solo, talk, ternary, water_phase
    if sha(args.cases) != PANEL_SHA:
        raise ValueError('the independent prompts have changed')
    evidence = {'cases_sha256':PANEL_SHA, 'model_generations': 0, 'implementation_sha256':{}, 'cases':[]}
    for mod in (talk, solo, water_phase, domain_advice):
        evidence['implementation_sha256'][mod.__name__] = sha(Path(mod.__file__))
    detector = getattr(water_phase, 'standalone_phase', None)
    validator = getattr(water_phase, 'confirms', None)
    with tempfile.TemporaryDirectory(prefix='hive-water-injection-') as d:
        for row in json.loads(args.cases.read_bytes()):
            prompt, wrong = row['text'], row['worker']
            phase = detector(prompt, ()) if detector else None
            result = {'id':row['id'],'eligible_phase':phase,'outcomes':{}}
            if row['expected_phase'] is not None and validator:
                # Probe the constituent decision and recovery separately, even when the outer gate declines.
                physical = water_phase.equilibrium_phase(prompt)
                probe = {'physical_phase': physical}
                if physical is not None:
                    explicit = water_phase.checked_reply(prompt, physical, source='equilibrium_rule', proposed=wrong)
                    probe.update(validator_accepts_injected=validator(physical, wrong),
                                 validator_accepts_computed=validator(physical, physical),
                                 explicit_recovery_text=explicit['text'])
                result['component_probe_bypasses_standalone_eligibility'] = probe
            for route in ('talk','work'):
                convo = [{'role':'user', 'content':prompt}]
                report = {'agreed':True, 'report':wrong+'\n## How it was checked\nControlled worker agreement.',
                          'files':[]}
                with (patch.object(talk, 'route', return_value=(route,convo)),
                      patch.object(solo, 'first', return_value=report) as worker,
                      patch.object(ternary, 'chat', return_value=wrong) as native):
                    out = talk.reply(prompt, base='t80', run_dir=Path(d)/row['id']/route)
                result['outcomes'][route] = {k:v for k,v in out.items() if k not in
                                              ('dir','task','seconds','domain_signal','engram_advice')}
                result['outcomes'][route].update(synthetic_worker_calls=worker.call_count,
                                                 synthetic_chat_calls=native.call_count)
            evidence['cases'].append(result)
    args.output.write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
