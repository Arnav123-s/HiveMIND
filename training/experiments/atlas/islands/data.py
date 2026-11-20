"""The immutable exercise split and compact, unrestricted-vocabulary scorer inputs."""
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256
import json

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REPORT = ROOT / "training/reports/domain-engrams"
EXTRA = {"physics": "water-v2", "engineering": "timing-v2"}


@dataclass(frozen=True)
class Row:
    key: str
    domain: str
    split: str
    question: str
    label: str
    token: int


def corpus():
    original = json.loads((REPORT / "exercises.json").read_text())
    states = np.load(REPORT / "training-states.npz")
    rows, known = [], {}
    for domain in sorted(original):
        task = original[domain]
        token = dict(zip([label for _, label in task["train"]], states[domain + "_tokens"].astype(int)))
        for source in ("train", "check"):
            for i, (question, label) in enumerate(task[source]):
                key = f"{domain}-{source}-{i}"
                rows.append(Row(key, domain, "train" if source == "train" else "anchor", question, label, int(token[label])))
                if source == "train":
                    known[key] = states[domain][i]
        if domain in EXTRA:
            folder = REPORT / EXTRA[domain]
            extra = json.loads((folder / "exercises.json").read_text())
            vectors = np.load(folder / "training-states.npz")["features"][9:]
            held = set()
            for label in token:
                group = [i for i, (_, name) in enumerate(extra) if name == label]
                assert len(group) == 6
                held.update(sorted(group, key=lambda i: sha256(extra[i][0].encode()).digest())[:2])
            for i, ((question, label), vector) in enumerate(zip(extra, vectors, strict=True)):
                key = f"{domain}-extra-{i}"
                known[key] = vector
                rows.append(Row(key, domain, "held" if i in held else "train", question, label, int(token[label])))
    assert len({r.question for r in rows}) == len(rows) == 90
    return rows, known


def load():
    rows, known = corpus()
    with np.load(HERE / "cached-endpoints.npz") as stored:
        assert [r.key for r in rows] == stored["ids"].tolist()
        known.update(zip(stored["anchor_ids"].tolist(), stored["anchor_features"]))
        features = np.stack([known[r.key] for r in rows]).astype(np.float64)
        return (rows, features, stored["tokens"], stored["canonical_logits"], stored["other_logits"],
                stored["other_ids"], stored["other_words"])
