import json

import pytest

from training.experiments import rule_lab as lab
from training.experiments import rule_lab_recipe as recipes
from training.experiments.rule_lab_solver import fit
from training.experiments.rule_lab_train import teaching_rows


def test_rules_and_heldout_settings_are_disjoint_from_training_and_probing():
    for family in lab.TERMS:
        train = {lab.secret(i, family) for i in range(10, 16)}
        exam = {lab.secret(i, family) for i in range(101, 107)}
        assert len(train) == len(exam) == 6 and train.isdisjoint(exam)
    assert all(x not in range(3) or y not in range(3) for x, y in lab.POINTS)


def test_tools_accept_formatting_but_enforce_budget_and_measurements():
    assert lab.checked_action('```json\n{"measure":[[[0,1]]]}\n```', [], 3)["measure"] == [[0, 1]]
    for text in ('{"measure":[[3,0]]}', '{"measure":[[0,0],[0,0]]}', '{"submit":[1,true,2]}',
                 '{"submit":[1,2,3],"measure":[]}', '{"measure":[[2,2]]}'):
        with pytest.raises(ValueError):
            lab.checked_action(text, [[0, 0, 1], [0, 1, 2], [1, 0, 3], [1, 1, 4]], 3)

    obs = [[0, 0, 4], [1, 0, -1], [0, 1, 2]]
    assert lab.checked_action('{"submit":["r0","r1-r0","-(r0-r2)"]}', obs, 3)["submit"] == [4, -5, -2]
    for expr in ("True", "r3", "r1**2", "f()", "9999*9999", "r1+"):
        with pytest.raises(ValueError):
            lab.coefficient(expr, obs)


def test_public_feedback_and_blind_grader(tmp_path):
    class Guesser:
        def reply(self, cell, messages):
            msg = messages[-1]["content"]
            if "notebook:\nempty" in msg:
                return {"text": '{"measure":[[0,0]],"next":"peer"}'}
            if "Tool error" not in msg:
                return {"text": '{"submit":[99,0,0]}'}
            assert "at x=0, y=0" in msg and "x=-3" not in msg
            return {"text": '{"submit":["r0",0,0]}'}

    state = lab.episode(Guesser(), tmp_path / "blind.json", 10, "affine", "open", ["a", "b"])
    assert state["turns"][1]["error"] and state["turns"][2]["accepted"]
    assert not state["score"]["correct"]


@pytest.mark.parametrize("family", lab.TERMS)
def test_exact_worker_requires_identifiable_consistent_public_evidence(family):
    truth = lab.secret(25, family)
    points = [(0, 0), (2, 1), (1, 2), (2, 2)]
    table = [(x, y, lab.instrument(truth, x, y)) for x, y in points]
    assert fit(family, table[:2]) is None
    assert fit(family, table) == list(truth)
    assert fit(family, table + [(0, 0, 100)]) is None


def test_induced_procedure_and_teaching_split(tmp_path):
    points = [(0, 0), (0, 1), (1, 0), (1, 1)]
    worlds = [[(x, y, lab.instrument(lab.secret(seed, "affine"), x, y)) for x, y in points]
              for seed in range(10, 16)]
    recipe = recipes.synthesize(worlds)
    truth = lab.secret(103, "affine")
    assert recipes.execute(recipe, lambda x, y: lab.instrument(truth, x, y)) == list(truth)
    changed = recipes.calibrate(recipe, lambda x, y: 2 + 3*x - y + 4*x*y)
    assert changed["coefficients"] == [2, 3, -1, 4] and len(changed["observations"]) == 5
    assert recipes.calibrate(recipe, lambda x, y: x*x)["worker"] == "abstain"
    assert recipes.public_error({"points": [[0, 0]], "expressions": ["r0", "r0", "r0"]}, worlds)
    path = tmp_path / "exam.json"
    path.write_text(json.dumps({"family": "affine", "seed": 101}))
    with pytest.raises(ValueError, match="teaching"):
        teaching_rows([path])


def test_restarted_peer_reads_only_measured_evidence(tmp_path):
    path = tmp_path / "episode.json"

    class First:
        def reply(self, cell, messages):
            if cell == "analyst":
                raise ConnectionError("simulated process loss")
            assert "notebook:\nempty" in messages[-1]["content"]
            return {"text": '{"measure":[[0,0],[1,0],[0,1]],"next":"peer"}'}

    class Peer:
        def reply(self, cell, messages):
            assert cell == "analyst"
            assert "predictions" not in messages[-1]["content"] and "x=0, y=0 -> z=" in messages[-1]["content"]
            c, x, y = [r[2] for r in json.loads(path.read_text())["observations"]]
            return {"text": json.dumps({"submit": [c, x-c, y-c]})}

    args = path, 11, "affine", "open", ["designer", "analyst"]
    with pytest.raises(ConnectionError):
        lab.episode(First(), *args)
    before = json.loads(path.read_text())
    assert "score" not in before and len(before["turns"]) == 1
    result = lab.episode(Peer(), *args)
    assert result["score"]["hits"] == 8 and result["score"]["probes"] == 3
    assert lab.episode(None, *args) == json.loads(path.read_text())
    with pytest.raises(ValueError):
        lab.episode(None, path, 12, "affine", "open", ["designer", "analyst"])
