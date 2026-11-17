import random
from pathlib import Path

from training.kinds import h_web as H  # the kind's own file (training/exam_hard keeps its old names)


def test_a_fact_from_the_open_web_is_checked_against_every_value_wikidata_records(monkeypatch):
    monkeypatch.setattr(H, "WEB", [H.WEB[0]])
    monkeypatch.setattr(H, "_web_pick", lambda cls, prop, links, seed: ("Q1", "Testville", "Nowhere"))
    monkeypatch.setattr(H, "_web_values", lambda qid, prop, units: [120000.0, 125500.0])
    field, kind, task, check = H.h_web(random.Random(1))
    assert field == "hard: open web" and "Testville (Nowhere)" in task and "Q1" in task
    assert check(Path("/x"), "The population is 125,500.")[0]       # any value recorded, with thousands separators
    assert check(Path("/x"), "About 120200 people.")[0]               # within half a percent
    assert not check(Path("/x"), "It is 99000.")[0]
