"""Evaluate the predeclared balanced random, hard, constant-price and LMSR half-budget selections."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run import Study, np
from hashlib import sha256
from statistics import median
import argparse
import json

SEEDS = (23, 29, 31, 37, 41)
PULLS = (0.5, 0.1)
POLICIES = ["hard", "static", "lmsr", *(f"random-{s}" for s in SEEDS)]
B = 0.5


def cost(q):
    m = q.max()
    return float(m + B * np.log(np.exp((q - m) / B).sum()))


def prices(q):
    weights = np.exp((q - q.max()) / B)
    return weights / weights.sum()


class Subsets(Study):
    def __init__(self):
        super().__init__()
        self.names = [self.rows[i].key for i in self.train]
        self.cells = [(self.rows[i].domain, int(self.gold[i])) for i in self.train]
        self.groups = {s: [j for j, v in enumerate(self.cells) if v == s] for s in sorted(set(self.cells))}
        self.policy = "hard"

    def neighbors(self):
        x = self.x[self.train]
        unit = x / np.linalg.norm(x, axis=1, keepdims=True)
        unit -= unit.mean(axis=0)
        unit /= np.linalg.norm(unit, axis=1, keepdims=True)
        sim = unit @ unit.T
        np.fill_diagonal(sim, -np.inf)
        neighbors = [sorted(range(len(self.train)), key=lambda j: (-row[j], self.names[j]))[:2] for row in sim]
        return sim, neighbors

    def market(self):
        n = len(self.train)
        _, near = self.neighbors()
        incoming = np.bincount(np.ravel(near), minlength=n)
        margin = self.margins(self.train)
        utility = np.zeros(n)
        for group in self.groups.values():
            scoped = margin[group]
            for j in group:
                percentile = (sum(scoped < margin[j]) + 0.5 * sum(scoped == margin[j])) / len(group)
                utility[j] = 1 + percentile + 1 / (1 + incoming[j])
        bundles = np.eye(n) / 2
        for j, neighbors in enumerate(near):
            bundles[j, neighbors] = 0.25
        q = np.zeros(n)
        remaining = {s: len(group) // 2 for s, group in self.groups.items()}
        eligible = set(range(n))
        start, cash = cost(q), 15.0
        selected, trades = [], []
        for _ in range(sum(remaining.values())):
            p = prices(q) if self.policy == "lmsr" else np.full(n, 1 / n)
            quotes = bundles @ p
            assert (p > 0).all() and abs(p.sum() - 1.0) < 1e-10
            offers = [j for j in eligible if remaining[self.cells[j]] > 0]
            j = min(offers, key=lambda j: (-utility[j] / quotes[j], self.names[j]))
            indifferent = min(offers, key=lambda j: (-utility[j], self.names[j]))
            updated = q + bundles[j]
            charge = cost(updated) - cost(q) if self.policy == "lmsr" else float(quotes[j])
            cash -= charge
            assert 0 < charge <= 0.5000001 and cash >= -1e-8
            trades.append(dict(item=self.names[j], neighbors=[self.names[k] for k in near[j]], value=utility[j],
                               marginal=quotes[j], debit=charge, cash=cash, winner_at_uniform=self.names[indifferent]))
            q = updated
            eligible.remove(j)
            remaining[self.cells[j]] -= 1
            selected.append(self.train[j])
        if self.policy == "lmsr":
            assert abs((15 - cash) - (cost(q) - start)) < 1e-9
        self.ledger = dict(liquidity=B if self.policy == "lmsr" else None, start_cash=15, closing_cash=cash,
                           final_prices=dict(zip(self.names, prices(q) if self.policy == "lmsr" else np.full(n, 1/n))),
                           closing_shares=dict(zip(self.names, q)), trades=trades)
        return selected

    def schedule(self, keep):
        self.ledger = None
        if self.policy == "hard":
            return super().schedule(0.5)
        if self.policy.startswith("random-"):
            seed = self.policy.split("-")[-1]
            selected = []
            for group in self.groups.values():
                order = sorted(group, key=lambda j: sha256((seed + ":" + self.names[j]).encode()).digest())
                selected.extend(self.train[j] for j in order[:len(group) // 2])
        else:
            selected = self.market()
        chosen = set(selected)
        assert len(chosen) == 30 and chosen <= set(self.train)
        jobs = super().schedule(1.0)
        return [{d: [i for i in seq if i in chosen] for d, seq in row.items()} for row in jobs]

    def describe_subset(self, jobs):
        selected = [i for rnd in jobs for seq in rnd.values() for i in seq]
        assert len(set(selected)) == 30 and all(self.rows[i].split == "train" for i in selected)
        local_ids = [self.train.index(i) for i in selected]
        assert all(sum(j in group for j in local_ids) * 2 == len(group) for group in self.groups.values())
        sim, near = self.neighbors()
        return dict(ids=[self.rows[i].key for i in selected],
                    coverage=len({k for j in local_ids for k in [j, *near[j]]}),
                    mean_nearest_selected_cosine=float(np.max(sim[np.ix_(local_ids, local_ids)], axis=1).mean()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    study = Subsets()
    arms = [(policy, pull) for pull in PULLS for policy in POLICIES]
    timing = {arm: [] for arm in arms}
    for k in range(-1, 5):
        order = arms[k:] + arms[:k]
        for name, pull in order:
            study.policy = name
            _, cpu = study.train_arm(0.5, pull)
            if k >= 0:
                timing[name, pull].append(cpu)
    legacy = json.loads((HERE.parent / "results.json").read_text())
    results, subsets = [], {}
    for name, pull in arms:
        study.policy = name
        history, _ = study.train_arm(0.5, pull)
        subset = study.describe_subset(study.schedule(0.5))
        if name not in subsets:
            subsets[name] = dict(**subset, ledger=study.ledger)
        assert subsets[name]["ids"] == subset["ids"]
        scores = [dict(local=study.score(local, by_domain=True, detail=i == 3), trunk=study.score(trunk, detail=i == 3))
                  for i, (local, trunk) in enumerate(history)]
        if name == "hard":
            expect = next(a for a in legacy["arms"] if a["keep"] == 0.5 and a["pull"] == pull)
            assert subset["ids"] == [s for rnd in expect["training_ids"] for seq in rnd.values() for s in seq]
            assert scores[-1]["local"] == expect["rounds"][-1]["local"]
            assert scores[-1]["trunk"] == expect["rounds"][2]["trunk"]
        times = timing[name, pull]
        results.append(dict(policy=name, pull=pull, rounds=scores, cpu_s=times,
                            median_cpu_s={k: median(t[k] for t in times) for k in times[0]}))
    def effect(candidate, other, pull):
        a, b = [next(arm["rounds"][-1] for arm in results if arm["policy"] == name and arm["pull"] == pull)
                for name in (candidate, other)]
        contrast = {}
        for body in ("local", "trunk"):
            pairs = list(zip(a[body]["cases"], b[body]["cases"], strict=True))
            contrast[body] = dict(delta=a[body]["total"] - b[body]["total"],
                                  gains=[x["key"] for x, y in pairs if x["ok"] and not y["ok"]],
                                  losses=[x["key"] for x, y in pairs if not x["ok"] and y["ok"]])
        return dict(candidate=candidate, control=other, pull=pull, **contrast)
    contrasts = [effect(candidate, control, pull) for pull in PULLS for candidate in ("lmsr", "hard")
                 for control in POLICIES if control.startswith("random-") or (candidate == "lmsr" and control == "static")]
    sources = {str(p.relative_to(HERE.parents[4])): sha256(p.read_bytes()).hexdigest()
               for p in [HERE / "protocol.md", HERE / "compare.py", HERE.parent / "run.py", HERE.parent / "results.json"]}
    output = dict(freeze_sha256=sources, subsets=subsets, arms=results, contrasts=contrasts)
    args.out.write_text(json.dumps(output, separators=(",", ":"), allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
