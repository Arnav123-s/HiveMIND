"""Fit two distinct sparse text senders and a logistic reader on their quantized messages."""
import argparse
import base64
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from team import signals

CLASSES = signals.DOMAINS + ('follow', 'other')
CORPUS_HASHES = {'requests.txt': '1dad7324c5d62f09fdfdac527664b67b39e8f13267b772419c2bbf3ff8d13a5a',
                 'topics.txt': '88504d6b1c1ebba349ad705bfbf591b7446f35629e4eb5503b1a6d53b594b2b1'}


def sections(name):
    data = (HERE/name).read_bytes()
    if hashlib.sha256(data).hexdigest() != CORPUS_HASHES[name]:
        raise ValueError(f'changed corpus: {name}')
    rows = {}
    for line in data.decode().splitlines():
        if line.startswith('['):
            group = line.strip('[]')
            rows[group] = []
        elif line:
            rows[group].append(line)
    return rows


def examples(requests, topics):
    samples, weights = [], []
    for idx, group in enumerate(CLASSES):
        for utterance in requests[group][:32]:
            samples.append((utterance, idx))
            weights.append(1.)
        for phrase in topics.get(group, []):
            samples.append((phrase, idx))
            weights.append(.75)
            for term in phrase.split():
                samples.append((term, idx))
                weights.append(.35)
    return samples, weights


def fit_sender(vectors, labels, weights, strength):
    model = LogisticRegression(C=strength, max_iter=600, solver='lbfgs', tol=1e-6)
    model.fit(vectors, labels, sample_weight=weights)
    scale = float(np.max(np.abs(model.coef_))) / 127
    rows = np.rint(model.coef_.T/scale).clip(-127,127).astype('int8')
    return {'weights': base64.b64encode(rows.tobytes()).decode('ascii'), 'scale': scale,
            'bias': model.intercept_.tolist()}


def quantized_model(asset):
    m = {**asset, 'id': 'development', 'vocab': {v:i for i,v in enumerate(asset['vocab'])}}
    for role in signals.ROLES:
        sender = asset[role]
        m[role] = {**sender,'rows': memoryview(base64.b64decode(sender['weights'])).cast('b')}
    return m


def pairs(requests, start, stop):
    """Independent contexts, contradicting contexts and an explicit prior for the referential turns."""
    rows = []
    for c, group in enumerate(CLASSES):
        for i, text in enumerate(requests[group][start:stop]):
            j = start + (i+3) % (stop-start)
            if c == 6:
                rows.append((text, '', 6))
                for h in range(7):
                    before = requests[CLASSES[h] if h<6 else 'other'][j]
                    rows.append((text, before, min(h, 6)))
            else:
                actual = c if c < 6 else 6
                rows.extend([(text,'',actual),(text,requests[CLASSES[(c+i+1)%6]][j],actual)])
    return rows


def train():
    requests, topics = sections('requests.txt'), sections('topics.txt')
    samples, weights = examples(requests,topics)
    ft = [signals.features(text) for text,_ in samples]
    counts = Counter(key for row in ft for key in row)
    names = sorted(counts)
    vocab = {k:i for i,k in enumerate(names)}
    idf = [max(.25, np.log((1 + len(ft))/(1 + counts[k]))) for k in names]
    indices, values, indptr = [],[],[0]
    for row in ft:
        a = [(vocab[k], v*idf[vocab[k]]) for k,v in row.items()]
        norm = np.sqrt(sum(v*v for _,v in a))
        indices.extend(i for i,_ in a)
        values.extend(v/norm for _,v in a)
        indptr.append(len(indices))
    matrix = csr_matrix((values,indices,indptr),shape=(len(samples),len(vocab)))
    y = [c for _,c in samples]
    # The lexical guard requires a training term actually associated with a domain.
    # Exclude generic task framing that can surround equally well an unfamiliar topic.
    framing = set(('i a an the this that it how can do my why what is are on in for from '
                   'of to as with these those your does give find get need want would like '
                   'helps help explain use show work make me we can could tell if ask '
                   'first only same two one something someone more difference between '
                   'please or try change choose should which start means best short and you').split())
    occurrences = {}
    for (text, c), row in zip(samples, ft):
        for key in row:
            if (key.startswith('w:') and key[2:] not in framing) or key.startswith('s:'):
                counts_by_class = occurrences.setdefault(key, [0]*8)
                counts_by_class[c] += 1
    anchor_masks = {}
    for key, ns in occurrences.items():
        mask = sum(1 << c for c in range(6) if ns[c] and ns[c]/sum(ns) >= .38)
        if mask:
            anchor_masks[key] = mask
    asset = {'task': signals.TASK, 'version': signals.VERSION, 'levels': signals.LEVELS,
             'domains': signals.DOMAINS, 'anchor_masks': anchor_masks, 'vocab': names, 'idf': [round(x,6) for x in idf],
             'request': fit_sender(matrix, y, weights, 65),
             'context': fit_sender(matrix, [min(c,6) for c in y], weights, 52)}
    model = quantized_model(asset)
    cache = {}
    def code(role, text):
        if (role,text) not in cache:
            cache[role,text] = signals._send(model,role,'train',text).payload
        return cache[role,text]

    rng = random.Random(75161)
    observed, targets = [], []
    for text, prior, label in pairs(requests,0,32):
        req, ctx = code('request',text),code('context',prior)
        for t in (False, True, True):
            def soften(v):
                if not t: return v
                strength = rng.uniform(.38,.98)
                return tuple(round(strength*n + (1-strength)*signals.LEVELS/len(v)) for n in v)
            observed.append(signals.reader_features(soften(req),soften(ctx)))
            targets.append(label)
    reader = LogisticRegression(C=12, max_iter=600, tol=1e-6)
    reader.fit(observed, targets)
    asset['reader'] = {'bias': reader.intercept_.tolist(), 'w': reader.coef_.tolist()}
    model['reader'] = asset['reader']
    mfunc = signals._model
    signals._model = lambda: model
    decisions = []
    checks = [(code('request',s),code('context',p),label) for s,p,label in pairs(requests,32,38)]
    def frames(q,c):
        return [signals.Frame('dev', role, signals.VERSION, signals.TASK+'/'+role, 'development', v)
                for role,v in zip(signals.ROLES,(q,c))]
    dev = [(frames(q,c),l) for q,c,l in checks]
    try:
        for d in (.29,.36,.42,.48,.55,.62):
            for m in (.13,.19,.25,.32):
                for r in (.5,.65,.75):
                    gates = {'intent':d,'domain':d,'margin':m,'reader':r}
                    model['gates'] = gates
                    cor = bad = null_calls = 0
                    for codes,label in dev:
                        got = signals.read_frames('dev',codes)
                        if got is not None:
                            good = label<6 and got['domain']==CLASSES[label]
                            cor += int(good)
                            bad += int(not good)
                            null_calls += int(label==6)
                    # Correct coverage is preferred after penalizing mistaken referrals and null violations.
                    decisions.append((cor-6*bad-4*null_calls, -bad, cor, d,m,r, null_calls))
    finally:
        signals._model = mfunc
    eligible = [entry for entry in decisions if entry[-1] == 0]
    if not eligible:
        fewest = min(entry[-1] for entry in decisions)
        eligible = [entry for entry in decisions if entry[-1] == fewest]
    _, neg_bad, correct, d,m,r, null_calls = max(eligible)
    asset['gates'] = {'intent':d,'domain':d,'margin':m,'reader':r}
    return asset, {'source_sha256': CORPUS_HASHES, 'sender_training_rows_with_lexical_anchors': len(samples),
                   'reader_training_pairs_before_softening':len(pairs(requests,0,32)),
                   'reader_training_rows': len(targets), 'heldout_authored_turns': 48,
                   'heldout_combinations':len(checks),'nonnull_target_combinations':sum(c<6 for _,_,c in checks),
                   'development_correct_advice':correct,'development_wrong_advice':-neg_bad,
                   'development_false_on_null':null_calls,'thresholds':asset['gates']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    asset, report=train()
    data=gzip.compress(json.dumps(asset,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode(),mtime=0)
    report['bundle_id']=hashlib.sha256(data).hexdigest()
    report['bundle_bytes']=len(data)
    args.out.write_bytes(data)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
