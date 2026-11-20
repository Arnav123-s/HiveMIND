"""First-token merge comparison on the previously archived native T80 endpoint data."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import process_time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "islands"))
from run import HEAD, Study, matrix


def factors(weights, rank):
    u, s, vh = np.linalg.svd(weights, full_matrices=False)
    r = min(rank, len(s))
    return {HEAD: (vh[:r].astype(np.float32), (u[:, :r]*s[:r]).astype(np.float32))}


def trimmed_vote(deltas):
    flattened = deltas.reshape(len(deltas), -1)
    k = max(1, int(np.ceil(flattened.shape[1]*0.2)))
    cutoffs = np.partition(abs(flattened), -k, axis=1)[:, -k]
    trimmed = np.where(abs(deltas) >= cutoffs[:, None, None], deltas, 0)
    sign = np.sign(trimmed.sum(axis=0))
    same = (np.sign(trimmed) == sign) & (trimmed != 0)
    return np.where(same,trimmed,0).sum(axis=0) / np.maximum(1,same.sum(axis=0))


def polar(mat):
    u, _, vh = np.linalg.svd(mat, full_matrices=False)
    return u @ vh


def orthogonal_merge(deltas):
    left, scale, right = [], [], []
    for delta in deltas:
        u, s, vh = np.linalg.svd(delta, full_matrices=False)
        left.append(u[:,:2])
        scale.extend(s[:2])
        right.append(vh[:2].T)
    return (polar(np.column_stack(left))*np.array(scale)) @ polar(np.column_stack(right)).T


def evaluate(path):
    st = Study()
    dev = []
    for domain in st.domains:
        for col in st.cols[domain]:
            options = [i for i in st.train if st.rows[i].domain == domain and st.gold[i] == col]
            dev.append(min(options,key=lambda i:sha256(st.rows[i].question.encode()).digest()))
    fit = sorted(set(st.train) - set(dev))
    assert (len(fit), len(dev), len(st.test)) == (42,18,30)
    pooled = st.fit(st.empty, fit, np.arange(len(st.tokens)))
    common = matrix(pooled)
    heads = {d:st.fit(pooled,[i for i in fit if st.rows[i].domain==d],st.cols[d]) for d in st.domains}
    deltas = np.stack([matrix(heads[d])-common for d in st.domains])
    result = dict(fitting=[st.rows[i].key for i in fit], development=[st.rows[i].key for i in dev],
                  test=[st.rows[i].key for i in st.test],
                  pooled=st.score(pooled, detail=True),
                  oracle_domain=st.score(heads,by_domain=True,detail=True), arms={}, scales={})
    # Ignore magnitudes below numerical precision for this descriptive sign statistic.
    active = abs(deltas) > abs(deltas).max()*1e-6
    shared = active.sum(axis=0) >= 2
    opposed = ((deltas>0)&active).any(axis=0) & ((deltas<0)&active).any(axis=0)
    result['signs'] = dict(shared=int(shared.sum()), opposing=int((shared & opposed).sum()))
    total = deltas.sum(axis=0)
    ties = trimmed_vote(deltas)
    approaches = [('mean16', deltas.mean(axis=0), 16), ('sum4',total,4), ('sum12',total,12),
                  ('sum16',total,16), ('ties16',ties,16), ('polar2_each',orthogonal_merge(deltas),16)]
    for seed in (11,29,53):
        rng = np.random.default_rng(seed)
        dropped = np.where(rng.random(deltas.shape)<0.5, 0, 2*deltas).mean(axis=0)
        approaches.append((f'dare_mean16_{seed}', dropped, 16))
    def head(delta, alpha, rank):
        return factors(common+alpha*delta,rank)
    def loss(edit):
        logits = st.base[dev] + st.x[dev] @ matrix(edit).T
        indices = np.arange(len(dev))
        y = logits[indices,st.gold[dev]].copy()
        logits[indices,st.gold[dev]] = -np.inf
        strongest = np.maximum(logits.max(axis=1),st.other[dev])
        return float(np.logaddexp(0,strongest-y).mean())
    for name, delta, rank in approaches:
        initial = head(delta, 1, rank)
        result['arms'][name] = st.score(initial, detail=True)
        if name not in ('sum16','ties16'):
            continue
        before = process_time()
        options = [(loss(head(delta, alpha, rank)), float(alpha)) for alpha in np.linspace(0,2,11)]
        _, best = min(options,key=lambda pair:(pair[0],abs(pair[1]-1)))
        grid_cpu = process_time() - before
        alpha = 1.0
        before = process_time()
        steps = []
        for _ in range(5):
            left,right=max(0,alpha-0.05),min(2,alpha+0.05)
            l,r=loss(head(delta,left,rank)),loss(head(delta,right,rank))
            grad=(r-l)/(right-left)
            steps.append(dict(alpha=alpha,left=left,right=right,left_loss=l,right_loss=r))
            alpha=float(np.clip(alpha-0.25*grad,0,2))
        final_loss = loss(head(delta,alpha,rank))
        difference_cpu = process_time()-before
        result['scales'][name]=dict(grid=options, grid_choice=best, grid_cpu_s=grid_cpu,
                                    grid_test=st.score(head(delta,best,rank),detail=True),steps=steps,
                                    final=alpha,final_dev_loss=final_loss,finite_difference_cpu_s=difference_cpu,
                                    finite_difference_test=st.score(head(delta,alpha,rank),detail=True))
    path.write_text(json.dumps(result,indent=2)+'\n')
    print({k:v['total'] for k,v in result['arms'].items()})
    print({k:(v['grid_test']['total'],v['finite_difference_test']['total']) for k,v in result['scales'].items()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,type=Path)
    evaluate(p.parse_args().out)
