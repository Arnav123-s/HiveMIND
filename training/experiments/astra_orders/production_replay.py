"""Post-audit replay of the 14 reviewed, immutable local-only programs through the normal CPython runner."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from team.deliverables import wanted
from team.specialists.coder import extract_code
from team.tools import sandbox
from training.experiments.astra_orders import panel

HERE = Path(__file__).resolve().parent
SHA = '0d152f2baf1318f6d781d03742c1414bcb8f1f60ea637e2a8b169c1ace808cb9'


def replay():
    source = (HERE / 'native.json').read_bytes()
    # Native CPython is not a sandbox. These exact programs were inspected for
    # process/network operations, file paths, imports and other side effects.
    if hashlib.sha256(source).hexdigest() != SHA:
        raise ValueError('only the reviewed immutable outputs are eligible for host replay')
    requests = {r['id']:r for r in json.loads((HERE / 'panel.json').read_bytes())}
    out = []
    for call in json.loads(source)['calls']:
        row = requests[call['id']]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work = root / 'work'
            work.mkdir()
            names = wanted(row['task'])
            sandbox.give(row['task'], work, skip=names)
            with patch.object(sandbox, 'HOOK', root / 'hooks'):
                run = sandbox.run_python(extract_code(call['raw']), work, timeout=15)
            ok, reason = panel.grade(row, run['stdout'], work)
            files = {n: (work/n).read_text() for n in ('pulses.json','drift.json') if (work/n).is_file()}
            emitted = {'stdout':run['stdout'], 'stderr_last':run['stderr'].strip().splitlines()[-1] if run['stderr'].strip() else '',
                       'exit':run['returncode'], 'files':files}
        out.append({'id':call['id'], 'arm':call['arm'], 'ok':bool(ok and not run['returncode']),
                    'reason':reason, **emitted})
    return {'native_sha256':SHA, 'runtime':'normal team.tools.sandbox.run_python from repository venv', 'calls':out}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    args = p.parse_args()
    args.out.write_text(json.dumps(replay(),indent=2,sort_keys=True)+'\n')
