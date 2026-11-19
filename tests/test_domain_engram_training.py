import numpy as np
import pytest

from training import domain_engram


def test_low_rank_residual_learns_two_independent_labels():
    x = np.array([[1.0, 2.0], [1.1, 1.9], [2.0, -1.0], [1.8, -1.1]])
    ids, a, b, result = domain_engram.fit(x, [5, 5, 2, 2])
    predicted = ids[np.argmax(x @ a.T @ b.T, axis=1)]
    assert list(predicted) == [5, 5, 2, 2]
    assert result["target_mse_after"] < result["target_mse_before"]
    assert a.shape == (domain_engram.RANK, 2) and b.shape == (2, domain_engram.RANK)


def test_insufficient_support_and_nonfinite_states_are_rejected():
    with pytest.raises(ValueError):
        domain_engram.fit(np.eye(3), [4, 4, 6])
    with pytest.raises(ValueError):
        domain_engram.fit(np.array([[np.nan], [1], [2], [3]]), [3, 3, 5, 5])


def test_non_disjoint_and_conflicting_prompts_are_rejected_before_loading(tmp_path):
    a = {"prompt": "Label this record.", "answer": "A"}
    args = {"model": None, "runtime": None, "threads": 1}
    with pytest.raises(ValueError, match="disjoint"):
        domain_engram.train([a], tmp_path / "x", validation=[a], **args)
    with pytest.raises(ValueError, match="conflicting"):
        domain_engram.train([a, dict(a, answer="B")], tmp_path / "x", **args)



def test_another_base_cannot_publish_a_t80_adapter(tmp_path):
    foreign = tmp_path / "unrelated.gguf"
    foreign.write_bytes(b"another model")
    with pytest.raises(ValueError, match="Ternary-Bonsai-8B"):
        domain_engram.train([{"prompt": "A?", "answer": "X"}], tmp_path / "candidate.gguf",
                            model=foreign, runtime=None)
