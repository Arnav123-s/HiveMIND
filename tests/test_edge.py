import json
from collections import Counter

from training import exam, exam_hard, grow


def _line(kinds, dna="t17"):
    return json.dumps({"dna": dna, "arms": {"after": {"kinds": kinds}}})


def test_kinds_near_half_passed_weigh_most(tmp_path):
    rec = tmp_path / "g.jsonl"
    rec.write_text("\n".join([_line({"easy": [8, 8], "edge": [4, 8], "hopeless": [0, 8]}), _line({"easy": [99, 99]}, dna="t40")]))
    w = grow.edge_weights(record=rec)
    assert w["edge"] > w["easy"] and w["edge"] > w["hopeless"]
    assert abs(w["edge"] - 0.25) < 1e-9          # (4+1)/(8+2) = 0.5 -> 0.25
    assert abs(w["easy"] - w["hopeless"]) < 1e-9  # learned and not-yet-learnable weigh the same, and little


def test_edge_practice_draws_by_weight(monkeypatch):
    def maker(kind):
        def make(r):
            return "f", kind, f"{kind} task {r.random()}", lambda ans: True
        make.__name__ = "m_" + kind
        return make
    monkeypatch.setattr(exam, "MAKERS", [maker("easy"), maker("edge")])
    monkeypatch.setattr(exam_hard, "MAKERS", [maker("hopeless")])
    tasks = exam.exam(7, 30, level="edge", weights={"easy": 0.01, "edge": 0.25, "hopeless": 0.01})
    count = Counter(t[2] for t in tasks)
    assert len(tasks) == 30 and count["edge"] > 20
    assert len({t[3] for t in tasks}) == 30   # no task twice
    again = exam.exam(7, 30, level="edge", weights={"easy": 0.01, "edge": 0.25, "hopeless": 0.01})
    assert [t[:4] for t in tasks] == [t[:4] for t in again]  # same seed, same tasks
