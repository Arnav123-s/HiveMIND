"""Choose from immutable specialist outputs with delayed feedback, and replay the frozen studies."""
import os
for setting in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[setting] = "1"

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "training/experiments/atlas/retention"))
import study as previous

HEAD = previous.HEAD
POLICIES = ("incumbent", "newest", "best_previous", "random", "typed", "feedback", "nearest_candidate",
            "nearest_direct", "allowed_base")


def word_digest(value):
    return sha256(value.encode()).hexdigest()


def unit(array):
    norm = np.linalg.norm(array)
    return array / max(float(norm), 1e-12)


@dataclass(frozen=True)
class Request:
    key: str
    domain: str
    question: str
    feature: np.ndarray
    words: tuple
    allowed: tuple
    allowed_base: str


class Members:
    def __init__(self):
        self.study = s = previous.Study()
        old, new, panels = previous.indexes(s)
        starting_head = s.fit(s.empty, old, list(range(len(s.tokens))))
        specialists, _, _, _ = previous.arm(s, starting_head, old, new, True, False, True)
        self.names = ["incumbent", *s.domains]
        self.heads = [starting_head, *(specialists[d] for d in s.domains)]
        self.head_hashes = {}
        for name, head in zip(self.names, self.heads, strict=True):
            payload = b"".join(np.ascontiguousarray(a).tobytes() for a in head[HEAD])
            self.head_hashes[name] = sha256(payload).hexdigest()
        self.training = old + new
        self.historical = sum(panels.values(), [])
        self.means = {domain: np.mean([unit(s.x[i]) for i in self.training if s.rows[i].domain == domain], axis=0)
                      for domain in s.domains}
        self.allowed = {domain: tuple(s.words[int(s.tokens[int(j)])] for j in s.cols[domain]) for domain in s.domains}

    def feature(self, x, domain):
        return unit(unit(x) - self.means[domain])

    def request(self, key, domain, question, x, logits, other_score, other_id, other_word):
        s = self.study
        words = []
        for head in self.heads:
            a, b = head[HEAD]
            scores = logits + (x @ a.T) @ b.T
            col = int(np.argmax(scores))
            top = int(s.tokens[col])
            outside = other_score > scores[col] or (other_score == scores[col] and other_id < top)
            words.append(other_word if outside else s.words[top])
        allowed_cols = s.cols[domain]
        best_col = allowed_cols[int(np.argmax(logits[allowed_cols]))]
        return Request(key, domain, question, self.feature(x, domain), tuple(words), self.allowed[domain],
                       s.words[int(s.tokens[best_col])])

    def archived(self, i):
        s = self.study
        row = s.rows[i]
        return self.request(row.key, row.domain, row.question, s.x[i], s.base[i],
                            s.other[i], s.outside_id[i], str(s.outside_word[i]))


class Chooser:
    def __init__(self, members):
        s = members.study
        self.names = members.names
        self.memory = defaultdict(list)
        self.support = defaultdict(Counter)
        self.quality = [0] * len(members.names)
        for i in members.training:
            row = s.rows[i]
            key = word_digest(row.question)
            self.memory[row.domain].append((key, members.feature(s.x[i], row.domain), row.label.casefold()))

    def choose(self, req):
        known = [(key, feat, label) for key, feat, label in self.memory[req.domain]
                 if key != word_digest(req.question)]
        label = min(known, key=lambda entry: (-float(entry[1] @ req.feature), entry[0]))[2]
        base = req.words[0]
        intended = self.names.index(req.domain)
        order = [0, intended, *(k for k in range(1, len(req.words)) if k != intended)]
        allowed_ids = [k for k in order if req.words[k] in req.allowed]
        matching = next((k for k in order if req.words[k] == label), None)
        first_valid = allowed_ids[0] if allowed_ids else 0
        nearest = matching if matching is not None else first_valid
        valid_incumbent = base in req.allowed
        typed = 0 if valid_incumbent else nearest
        ledger = self.support[(req.domain, base)]
        unlocked = ledger["win"] >= 2 and ledger["loss"] == 0
        feedback = nearest if not valid_incumbent or unlocked else 0
        strongest = max(range(len(self.quality)), key=lambda k: (self.quality[k], -k))
        random_head = int(word_digest("router-control-v1:" + req.question), 16) % len(req.words)
        indices = dict(incumbent=0, newest=intended, best_previous=strongest, random=random_head,
                       typed=typed, feedback=feedback, nearest_candidate=nearest)
        predictions = {name: req.words[k] for name, k in indices.items()}
        predictions.update(nearest_direct=label, allowed_base=req.allowed_base)
        return dict(predictions=predictions, heads={name: self.names[k] for name, k in indices.items()},
                    support=dict(ledger), nearest_label=label)

    def disclose(self, req, decision, answer):
        for idx, word in enumerate(req.words):
            self.quality[idx] += int(word == answer)
        base, proposed = req.words[0], decision["predictions"]["nearest_candidate"]
        if base != proposed and base in req.allowed:
            result = "win" if proposed == answer else "loss" if base == answer else "tie"
            self.support[(req.domain, base)][result] += 1
        self.memory[req.domain].append((word_digest(req.question), req.feature, answer))


def pair(before, after):
    assert len(before) == len(after)
    return dict(n=len(before), correct=sum(after), gains=sum(b and not a for a, b in zip(before, after)),
                losses=sum(a and not b for a, b in zip(before, after)))


def summarize(rows):
    previous_ok = [r["outputs"][0] == r["answer"] for r in rows]
    data = {name: pair(previous_ok, [r["predictions"][name] == r["answer"] for r in rows])
            for name in POLICIES}
    data["hindsight"] = pair(previous_ok, [r["answer"] in r["outputs"] for r in rows])
    return data


def run(members, confirmation=None):
    s = members.study
    router = Chooser(members)
    archive = sorted(members.historical, key=lambda i: word_digest("router-waves-1:" + s.rows[i].question))
    waves = [[(members.archived(i), s.rows[i].label.casefold()) for i in archive[j:j+12]]
             for j in range(0, len(archive), 12)]
    if confirmation:
        waves.append(confirmation)
    output = dict(heads=members.head_hashes, rounds=[])
    all_rows = []
    seen = []
    for number, wave in enumerate(waves, 1):
        # Current labels become visible only after *all* choices for this wave have been made.
        decisions = [router.choose(req) for req, answer in wave]
        prediction_hash = word_digest(json.dumps(decisions, sort_keys=True))
        rows = [dict(key=req.key, domain=req.domain, question=req.question, outputs=list(req.words),
                     answer=answer, **choice) for (req, answer), choice in zip(wave, decisions, strict=True)]
        retention = []
        for req, answer, first_good in seen:
            replay = router.choose(req)
            retention.append((first_good, replay["predictions"]["feedback"] == answer))
        metrics = pair([row[0] for row in retention], [row[1] for row in retention])
        output["rounds"].append(dict(number=number, predictions_sha256=prediction_hash, scores=summarize(rows),
                                     prior_feedback_holds=metrics, rows=rows))
        for (req, answer), choice in zip(wave, decisions, strict=True):
            router.disclose(req, choice, answer)
            seen.append((req, answer, choice["predictions"]["feedback"] == answer))
        all_rows.extend(rows)
    output["archived"] = summarize(all_rows[:len(archive)])
    return output


def read_confirmation(members, filename, cache):
    tasks = json.loads(filename.read_text())
    with np.load(cache, allow_pickle=False) as data:
        if data["cohort"].item() != sha256(filename.read_bytes()).hexdigest():
            raise ValueError("Native cache belongs to a different panel")
        if not np.array_equal(members.study.tokens, data["tokens"]):
            raise ValueError("Incompatible archived vocabulary")
        mixed = []
        for j, row in enumerate(tasks):
            req = members.request(f"fresh-{j}", row["domain"], row["question"], data["x"][j].astype(np.float64),
                                  data["logits"][j].astype(np.float64), data["outside_logit"][j],
                                  data["outside_id"][j], str(data["outside_word"][j]))
            mixed.append((req, row["label"].casefold()))
        return mixed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.cache) != bool(args.panel):
        parser.error("pass --panel and --cache together")
    members = Members()
    fresh = read_confirmation(members, args.panel, args.cache) if args.panel else None
    report = run(members, fresh)
    report["source_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    report["protocol_sha256"] = sha256((HERE / "protocol.md").read_bytes()).hexdigest()
    args.out.write_text(json.dumps(report, indent=1) + "\n")
    print("archived", {k: v["correct"] for k, v in report["archived"].items()})
    if fresh:
        print("fresh", {k: v["correct"] for k, v in report["rounds"][-1]["scores"].items()})


if __name__ == "__main__":
    main()
