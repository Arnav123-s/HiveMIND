"""Fixed-budget rehearsal, repair and routing on the island study's cached native model endpoints."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "islands"))
from run import Study, HEAD, RANK, merge, np
from hashlib import sha256
from itertools import product
from statistics import median
from time import process_time
import argparse
import json


def key(row):
    return sha256(row.question.encode()).digest()


def predict(study, heads, indices, *, routed=False):
    previous = study.test
    try:
        study.test = indices
        return study.score(heads, by_domain=routed, detail=True)["cases"]
    finally:
        study.test = previous


def indexes(study):
    original = [i for i in study.train if "-train-" in study.rows[i].key]
    reserve = []
    for d in study.domains:
        for col in study.cols[d]:
            pair = [i for i in original if study.rows[i].domain == d and study.gold[i] == col]
            assert len(pair) == 2
            reserve.append(min(pair, key=lambda i: key(study.rows[i])))
    old = sorted(set(original) - set(reserve))
    new = sorted(set(study.train) - set(original))
    panels = dict(reserved=reserve, earlier=[i for i in study.test if study.rows[i].split == "anchor"],
                  supplementary=[i for i in study.test if study.rows[i].split == "held"])
    assert len(old) == 18 and len(new) == 24 and len({*old, *new, *sum(panels.values(), [])}) == 90
    return old, new, panels


def inspect(study, incumbent, pool):
    a, b = incumbent[HEAD]
    pred = predict(study, incumbent, pool)
    margins = {}
    for p, i in zip(pred, pool, strict=True):
        scores = study.base[i] + (study.x[i] @ a.T) @ b.T
        gold = study.gold[i]
        current = scores[gold]
        scores[gold] = -np.inf
        margins[i] = (bool(p["ok"]), float(max(scores.max(), study.other[i]) - current))
    return margins


def select(study, old, new, observations, priority, anchors):
    selected = []
    for d in sorted({study.rows[i].domain for i in new}):
        for col in study.cols[d]:
            group = [i for i in new if study.rows[i].domain == d and study.gold[i] == col]
            def order(i):
                ok, margin = observations[i]
                return (ok, -margin, key(study.rows[i])) if priority else key(study.rows[i])
            selected.extend(sorted(group, key=order)[:1 if anchors else 2])
    rehearsed = []
    if anchors:
        queues = [[i for i in sorted(old, key=lambda i: key(study.rows[i]))
                   if study.rows[i].domain == d and observations[i][0]] for d in study.domains]
        while len(rehearsed) < 6:
            eligible = [q for q in queues if q]
            if not eligible:
                raise ValueError("fewer than six verified rehearsal rows")
            for q in eligible[:6 - len(rehearsed)]:
                rehearsed.append(q.pop(0))
    assert len(set(selected + rehearsed)) == 12
    return selected, rehearsed


def adjust(study, incumbent, ids, cols, observations, rehearsal):
    if not ids:
        return incumbent
    x = study.x[ids]
    norms = np.linalg.norm(x, axis=1)
    unit = x / norms[:, None]
    target = np.zeros((len(ids), len(cols)))
    for j, i in enumerate(ids):
        ok, margin = observations[i]
        if not ok and i not in rehearsal:
            target[j, np.searchsorted(cols, study.gold[i])] = max(0, margin + 6)
    dual = np.linalg.solve(unit @ unit.T + 0.1 * np.eye(len(ids)), target)
    b = np.zeros((len(study.tokens), len(ids)))
    b[cols] = dual.T
    return merge.merge([incumbent, {HEAD: (unit / np.median(norms), b)}], [1, 1], rank=RANK, normalize=False)[0]


def arm(study, incumbent, old, new, priority, anchors, routed):
    start = process_time()
    obs = inspect(study, incumbent, old + new)
    chosen, rehearsed = select(study, old, new, obs, priority, anchors)
    selected = chosen + rehearsed
    prepared = process_time()
    if routed:
        weights = {d: adjust(study, incumbent, [i for i in selected if study.rows[i].domain == d],
                             study.cols[d], obs, rehearsed) for d in study.domains}
    else:
        weights = adjust(study, incumbent, selected, list(range(len(study.tokens))), obs, rehearsed)
    return weights, chosen, rehearsed, dict(total=process_time() - start, inspect_select=prepared - start)


def paired(before, after):
    return dict(n=len(before), score=sum(row["ok"] for row in after), before=sum(row["ok"] for row in before),
                gains=sum(not a["ok"] and b["ok"] for a, b in zip(before, after, strict=True)),
                losses=sum(a["ok"] and not b["ok"] for a, b in zip(before, after, strict=True)))


def route(study, broad, specialists, test):
    by_key = {study.rows[i].key: i for i in test}
    broad = {p["key"]: p for p in broad}
    specialists = {p["key"]: p for p in specialists}
    outcome = []
    for stream in ("interleaved", "blocks"):
        sequence = sorted(test, key=lambda i: (study.rows[i].domain if stream == "blocks" else "", key(study.rows[i])))
        for policy in ("fixed", "lru", "success"):
            cache = list(study.domains[:2]) if policy == "fixed" else []
            credit = {d: 0.0 for d in study.domains}
            rows, hits, evictions = [], 0, 0
            for i in sequence:
                case = study.rows[i].key
                domain = study.rows[i].domain
                had = domain in cache
                hits += had
                before = list(cache)
                wide, expert = broad[case], specialists[case]
                delivered = expert if had else wide
                if policy == "lru":
                    cache = ([d for d in cache if d != domain] + [domain])[-2:]
                if policy == "success":
                    credit = {d: value * 0.9 for d, value in credit.items()}
                    credit[domain] += int(expert["ok"]) - int(wide["ok"])
                    cache = sorted((d for d in credit if credit[d] > 0), key=lambda d: (-credit[d], d))[:2]
                evictions += len(set(before) - set(cache))
                rows.append(dict(key=case, domain=domain, before=before, hit=had, token=delivered["token"],
                                 ok=delivered["ok"], broad_ok=wide["ok"], specialist_ok=expert["ok"]))
            assert len({row["key"] for row in rows}) == len(by_key)
            outcome.append(dict(stream=stream, policy=policy, checks=2 * len(test), hits=hits, evictions=evictions,
                                compared_to_broad=paired([broad[study.rows[i].key] for i in sequence], rows),
                                oracle_ceiling=sum(row["broad_ok"] or row["specialist_ok"] for row in rows), rows=rows))
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    study = Study()
    old, new, panels = indexes(study)
    test = sum(panels.values(), [])
    incumbent = study.fit(study.empty, old, list(range(len(study.tokens))))
    arms = list(product((False, True), repeat=3))
    costs = {a: [] for a in arms}
    for a in arms:
        arm(study, incumbent, old, new, *a)
    for j in range(7):
        for a in arms[j:] + arms[:j]:
            *_, cpu = arm(study, incumbent, old, new, *a)
            costs[a].append(cpu)
    wide_and_local = {}
    before = predict(study, incumbent, test)
    panels_for = {study.rows[i].key: name for name, ix in panels.items() for i in ix}
    results = []
    for a in arms:
        priority, anchors, routed = a
        weights, current, rehearsed, _ = arm(study, incumbent, old, new, *a)
        after = predict(study, weights, test, routed=routed)
        if not priority and anchors:
            wide_and_local[routed] = after
        def summary(indices):
            return paired(predict(study, incumbent, indices), predict(study, weights, indices, routed=routed))
        scores = {name: paired([p for p in before if panels_for[p["key"]] == name],
                               [p for p in after if panels_for[p["key"]] == name]) for name in panels}
        heads = list(weights.values()) if routed else [weights]
        results.append(dict(priority=priority, anchors=anchors, routed=routed, inspected=42,
                            current_ids=[study.rows[i].key for i in current], rehearsal_ids=[study.rows[i].key for i in rehearsed],
                            current_selected=summary(current), rehearsal_selected=summary(rehearsed),
                            all_new=summary(new), panels=scores, all_excluded=paired(before, after), cases=after,
                            coefficient_count=sum(a.size + b.size for h in heads for a, b in [h[HEAD]]),
                            median_cpu_s={k: median(t[k] for t in costs[a]) for k in costs[a][0]}, cpu_runs=costs[a]))
    artifacts = [HERE / "study.py", HERE / "protocol.md", HERE.parent / "islands" / "results.json"]
    output = dict(source_sha256={f.name: sha256(f.read_bytes()).hexdigest() for f in artifacts},
                  panels={k: [study.rows[i].key for i in ix] for k, ix in panels.items()},
                  older_training=[study.rows[i].key for i in old], new_feedback=[study.rows[i].key for i in new],
                  bare=predict(study, study.empty, test), incumbent=before, arms=results,
                  edges=route(study, wide_and_local[False], wide_and_local[True], test))
    args.out.write_text(json.dumps(output, separators=(",", ":"), allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
