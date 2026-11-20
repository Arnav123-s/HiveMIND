"""Prepare a development-only MAP-Elites archive and separately grade its frozen routes."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "islands"))
from run import HEAD, ROOT, REPORT, Study, np
from training import domain_engram
from hashlib import sha256
from itertools import product
from time import process_time
import argparse
import json

SEEDS = (11, 23, 37)
RAND = (101, 103, 107, 109, 113)
GROUPS = (("coding", "math"), ("conversation", "ml"), ("engineering", "physics"))


def digest(text):
    return sha256(text.encode()).digest()


def rng(seed, step, role):
    return np.random.default_rng(int.from_bytes(digest(f"{seed}/{step}/{role}")[:8], "big"))


def fingerprint(head):
    return sha256(b"".join(np.ascontiguousarray(a).tobytes() for a in head[HEAD])).hexdigest()


def split(study):
    dev, terminal = [], []
    for j, domain in enumerate(study.domains):
        for panel in ("anchor", "held"):
            rows = [i for i in study.test if study.rows[i].domain == domain and study.rows[i].split == panel]
            rows.sort(key=lambda i: digest("archive-v1:" + study.rows[i].question))
            for k, i in enumerate(rows):
                (dev if (k + j) % 2 == 0 else terminal).append(i)
    assert len(dev) == len(terminal) == 15 and len(set(dev + terminal + study.train)) == 90
    return dev, terminal


def historical(study):
    heads = [study.empty, study.fit(study.empty, study.train, list(range(len(study.tokens))))]
    states = np.load(REPORT / "training-states.npz")
    for d in study.domains:
        ids, a, short, _ = domain_engram.fit(states[d], states[d + "_tokens"])
        b = np.zeros((len(study.tokens), short.shape[1]), np.float32)
        b[np.searchsorted(study.tokens, ids)] = short
        heads.append({HEAD: (a.astype(np.float32), b)})
    return heads


def infer(study, indices):
    x = study.x[study.train]
    x = x / np.linalg.norm(x, axis=1, keepdims=True)
    center = x.mean(axis=0)
    def unit(a):
        return a / np.linalg.norm(a, axis=-1, keepdims=True)
    training = unit(x - center)
    centroids = unit(np.stack([training[[study.rows[i].domain == d for i in study.train]].mean(axis=0) for d in study.domains]))
    test = unit(unit(study.x[indices]) - center)
    return [study.domains[k] for k in np.argmax(test @ centroids.T, axis=1)]


def predict(study, head, indices):
    previous = study.test
    try:
        study.test = indices
        return study.score(head, detail=True)["cases"]
    finally:
        study.test = previous


def repertoire_route(selected, guesses, records, dev_cases):
    return {d: max(selected, key=lambda n: (sum(p["ok"] for p, domain in zip(dev_cases[n], guesses) if domain == d),
                                             records[n]["correct"], -n))
            for d in sorted({*guesses, *(d for pair in GROUPS for d in pair)})}


def search(study, initial, dev, seed, lanes, noise):
    heads, dev_cases, records, elites = [], [], [], {}
    guesses = infer(study, dev)

    def insert(head, info):
        ident = len(heads)
        predictions = predict(study, head, dev)
        bare = dev_cases[0] if dev_cases else predictions
        bits = []
        for group in GROUPS:
            pairs = [(a, b) for a, b in zip(predictions, bare) if a["domain"] in group]
            bits.append("1" if 3 * sum(a["token"] != b["token"] for a, b in pairs) >= len(pairs) else "0")
        cell = "".join(bits)
        total = sum(p["ok"] for p in predictions)
        incumbent = elites.get(cell)
        wins = incumbent is None or total > records[incumbent]["correct"]
        records.append(dict(id=ident, cell=cell, correct=total, entered=wins, previous=incumbent,
                            weights=fingerprint(head), tokens=[p["token"] for p in predictions], **info))
        if wins:
            elites[cell] = ident
        heads.append(head)
        dev_cases.append(predictions)

    for head, name in zip(initial, ["bare", "pooled", *study.domains], strict=True):
        insert(head, dict(origin=name, lane=None, parent=None, rows=[]))
    cells = [[i for i in study.train if study.rows[i].domain == d and study.gold[i] == col]
             for d in study.domains for col in study.cols[d]]
    for step in range(24):
        lane = step % lanes
        parents = sorted(i for i in elites.values() if records[i]["lane"] == lane)
        if not parents:
            parents = sorted(elites.values())
        parent = 0 if step < lanes else int(rng(seed, step, "parent").choice(parents))
        row_rng = rng(seed, step, "rows")
        chosen = [int(row_rng.choice(group)) for group in cells]
        head = study.fit(heads[parent], chosen, list(range(len(study.tokens))))
        if noise:
            a, b = head[HEAD]
            z = rng(seed, step, "noise").normal(size=a.shape)
            perturbed = a + z * (noise * np.linalg.norm(a) / np.linalg.norm(z))
            head = {HEAD: (perturbed.astype(np.float32), b)}
        insert(head, dict(origin="proposal", lane=lane, parent=parent, rows=[study.rows[i].key for i in chosen]))

    best = max(range(len(heads)), key=lambda n: (records[n]["correct"], -n))
    options = {"last": [len(heads) - 1], "single": [best], "archive": sorted(elites.values())}
    for s in RAND:
        ids = rng(s, 0, "random-control").choice(len(heads), size=len(elites), replace=False)
        options[f"random-{s}"] = sorted(map(int, ids))
    assert 1 <= len(elites) <= 8 and len(set(options["archive"])) == len(elites)
    routes = {p: repertoire_route(ids, guesses, records, dev_cases) for p, ids in options.items()}
    return dict(seed=seed, lanes=lanes, noise=noise, records=records, cells=elites, selected=options, routes=routes), heads


def summarize(study, ix, raw, oracle, bare):
    def group(indices):
        return dict(count=len(indices), score=sum(raw[j]["ok"] for j in indices), oracle=sum(oracle[j] for j in indices),
                    gains=sum(raw[j]["ok"] and not bare[j]["ok"] for j in indices),
                    losses=sum(not raw[j]["ok"] and bare[j]["ok"] for j in indices))
    return dict(total=group(range(len(ix))), earlier=group([j for j,i in enumerate(ix) if study.rows[i].split == "anchor"]),
                supplementary=group([j for j,i in enumerate(ix) if study.rows[i].split == "held"]))


def grade(study, plan, heads, terminal):
    guesses = infer(study, terminal)
    submitted = sorted({0, *(k for group in plan["selected"].values() for k in group)})
    outputs = {k: predict(study, heads[k], terminal) for k in submitted}
    results = {}
    for name, ids in plan["selected"].items():
        used = [plan["routes"][name][guess] for guess in guesses]
        answers = [outputs[k][j] for j, k in enumerate(used)]
        oracle = [any(outputs[k][j]["ok"] for k in ids) for j in range(len(terminal))]
        summary = summarize(study, terminal, answers, oracle, outputs[0])
        results[name] = dict(**summary, deployed_heads=len(ids), used=used, predictions=[p["token"] for p in answers],
                             correct=[p["key"] for p in answers if p["ok"]],
                             recoverable=[study.rows[terminal[j]].key for j, ok in enumerate(oracle) if ok])
    return dict(seed=plan["seed"], lanes=plan["lanes"], noise=plan["noise"], occupants=len(plan["cells"]), policies=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "score"])
    parser.add_argument("--plan", type=Path, default=HERE / "frozen-plan.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    study = Study()
    dev, terminal = split(study)
    boot = historical(study)
    plans, head_sets = [], []
    start = process_time()
    for seed, lanes, noise in product(SEEDS, (1, 2), (0, 0.05)):
        p, weights = search(study, boot, dev, seed, lanes, noise)
        plans.append(p)
        if args.phase == "score":
            head_sets.append(weights)
    files = [HERE / "experiment.py", HERE / "protocol.md", HERE.parent / "islands" / "results.json",
             HERE.parent / "islands" / "calibration.json"]
    manifest = dict(freeze={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in files},
                    fit=[study.rows[i].key for i in study.train], development=[study.rows[i].key for i in dev],
                    terminal=[study.rows[i].key for i in terminal], plans=plans)
    if args.phase == "prepare":
        args.plan.write_text(json.dumps(manifest, separators=(",", ":")) + "\n")
        print("Development plan", sha256(args.plan.read_bytes()).hexdigest(), "CPU seconds", round(process_time()-start, 3))
        return
    # All candidate weights, archive parentage, retained bodies and deployable decisions must match byte-for-byte
    # before reading even one terminal correctness result.
    if json.loads(args.plan.read_text()) != manifest:
        raise ValueError("development plan changed; refusing to score")
    results = [grade(study, p, w, terminal) for p, w in zip(plans, head_sets, strict=True)]
    bare = predict(study, study.empty, terminal)
    output = dict(plans_sha256=sha256(args.plan.read_bytes()).hexdigest(), terminal=[p["key"] for p in bare],
                  true_domains=[p["domain"] for p in bare], inferred_domains=infer(study, terminal), bare=bare, arms=results)
    args.out.write_text(json.dumps(output, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
