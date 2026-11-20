"""Pack the frozen independent TF-IDF reference using only the public training rows."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys


HERE = Path(__file__).resolve().parent
REF = HERE.parent / 'reports/domain-memory/signals'
sys.path.insert(0, str(REF))
import centroid


def public_rows():
    data = []
    for name, limit in [('requests.txt', 32), ('topics.txt', None)]:
        for line in (HERE/name).read_text().splitlines():
            if line.startswith('['):
                label = line[1:-1]
                count = 0
            elif line:
                if limit is None or count < limit:
                    data.append((line, None if label in ('follow','other') else label))
                count += 1
    return data


def fit(rows):
    reference, calibration = centroid.build(rows)
    grouped = {}
    for text,label in rows:
        grouped.setdefault(label or 'abstain',set()).add(text)
    train, calibrate = [], []
    for label, texts in sorted(grouped.items()):
        ordered = sorted(texts, key=lambda s: hashlib.sha256(s.encode()).hexdigest())
        for i,text in enumerate(ordered):
            (calibrate if i%5==0 else train).append((text,label))
    model = centroid.Centroid(train+calibrate)
    names, words = sorted(model.centers), sorted(model.idf)
    row = struct.Struct('>'+'d'*(len(names)+1))
    data = b''.join(row.pack(model.idf[f], *(model.centers[d].get(f,0.) for d in names)) for f in words)
    return {'domains':names,'features':words,'weights':base64.b64encode(data).decode('ascii'),
            'cut':calibration['cut'],'margin':calibration['margin']}, calibration, reference


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    asset, info, _ = fit(public_rows())
    packed=gzip.compress(json.dumps(asset,sort_keys=True,separators=(',',':')).encode(),mtime=0)
    args.out.write_bytes(packed)
    print(json.dumps({**info,'sha256':hashlib.sha256(packed).hexdigest(),'bytes':len(packed)},indent=2))
