"""Repeat native donor collection with a compatible CPU model. Writes a new trace archive."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import tempfile

from replay import HERE, ORDER_SHA, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary', 'weights', 'adapter', 'sdk', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--checkout', type=Path, default=HERE.parents[3])
    args = parser.parse_args()
    sys.path.insert(0, str(args.checkout.resolve()))
    from training.experiments.fieldwork import native, work
    from training.experiments.fieldwork.guest import Guest

    guest = Guest(args.sdk.resolve())
    orders = read('orders', ORDER_SHA)
    traces = {}
    with tempfile.TemporaryDirectory(prefix='hive-native-donors-') as tmp:
        root = Path(tmp)
        with native.server(args.binary, args.weights, root/'server.log', args.adapter, threads=2) as url:
            for name, order in orders.items():
                if order['phase'] != 'donor':
                    continue
                turns = []
                def ask(task, prefix, prior):
                    if not turns:
                        response = {'writer': 'authored_failed_draft', 'source': order['source'],
                                    'usage': {'completion_tokens': 0}, 'seconds': 0, 'stop': 'frozen_source'}
                    else:
                        if not prior or len(turns) > 2:
                            raise ValueError('unexpected correction call')
                        response = native.generate(url, task, prefix, prior, budget=240, seed=3141,
                                                   focused=True, concise=True)
                        response['writer'] = 'g47code2'
                    turns.append({'task': task.text, 'examples': task.example, 'prefix': prefix,
                                  'earlier': prior, 'response': response})
                    return response
                receipt = work.work(order['spec'], guest, ask, root/name/'work', root/name/'bank',
                                    rounds=3, repair_budget=2)
                traces[name] = turns
                print(name, len(turns)-1, 'native calls;', receipt['validated'], 'qualification checks passed')
    data = json.dumps(traces, indent=2).encode() + b'\n'
    args.output.write_bytes(gzip.compress(data, mtime=0))


if __name__ == '__main__':
    main()
