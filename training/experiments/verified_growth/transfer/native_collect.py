"""Capture one native selector decision per English request before exposing any answer or result."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
from urllib.error import URLError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from training.experiments.verified_growth.composer import native

EXPECTED = '6a71ae4d4806e855854e33c8d2e5397673893fec6c799287963e02fff265130d'


def collect(args):
    assert sha256(Path(native.__file__).read_bytes()).hexdigest() == EXPECTED
    requests = json.loads((args.fixtures / 'requests.json').read_bytes())
    tables = json.loads((args.fixtures / 'tables.json').read_bytes())
    existing = {}
    if args.out.exists():
        existing = {r['id']:r for r in map(json.loads,args.out.read_text().splitlines())}
    for case in requests:
        if case['id'] in existing:
            continue
        first, second = case['tables']
        columns = sorted(tables[first]['rows'][0])
        assert columns == sorted(tables[second]['rows'][0])
        start = time.monotonic()
        try:
            answer = native.select(args.url, case['request'], columns)
        except (OSError, ValueError) as exc:
            # Log transport failures separately. A completed model response is never replaced.
            with args.out.with_suffix('.errors.jsonl').open('a') as log:
                log.write(json.dumps({'id':case['id'], 'error':str(exc), 'seconds':round(time.monotonic()-start,3)})+'\n')
            raise
        row = dict(id=case['id'], input_sha256=sha256(json.dumps([case['request'],columns],ensure_ascii=False).encode()).hexdigest(),selector_sha256=EXPECTED,**answer)
        with args.out.open('a') as log:
            log.write(json.dumps(row,ensure_ascii=False)+'\n')
        print(len(existing)+1,flush=True)
        existing[case['id']] = row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=HERE/'panel')
    parser.add_argument('--url', required=True)
    parser.add_argument('--out', type=Path, required=True)
    collect(parser.parse_args())
