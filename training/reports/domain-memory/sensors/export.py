"""Make the small standard-library serving asset from the original trained four-bit archive."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = ROOT / 'training/reports/rule_lab/engrams/four-bit-pair.npz'
EXPECTED = '328370f1e213e347b538337345150d202a4bd308f7e7f2a093ebeea6163f08ef'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('unexpected original trained sensor archive')
    sys.path.insert(0, str(ROOT))
    from training.experiments.hive_signals import FRAME, interpret, load_reader, load_sender
    senders = [load_sender(ARCHIVE, role) for role in (0, 1)]
    reader = load_reader(ARCHIVE)
    table = []
    for left in range(16):
        for right in range(16):
            frames = [FRAME.pack(1, 6, 1, 0, left), FRAME.pack(1, 7, 1, 1, right)]
            opposite, positive = interpret(reader, 1, frames)
            table.append(str(2*opposite + positive))
    data = {'source_sha256': EXPECTED,
            'senders': [{'weights': s.weight[0].tolist(), 'bias': s.bias.item()} for s in senders],
            'reader': ''.join(table)}
    args.output.write_text(json.dumps(data, indent=2)+'\n')
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
