import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from training.experiments.engram_lora_surgery import compose, energy
from training.experiments.engram_fusion_exam import AFFINE_SEEDS
from training.experiments.rule_lab import secret
from training.experiments.engram_output_repair import features, inject, sparse_value
from training.experiments.engram_vector_surgery import surgery_diagnostics
from training.experiments.hive_interchange import bit_budget, decode, prefix_center
from training.experiments.hive_persona import checked_style, markers, one_sentence
from training.experiments.hive_reward_audits import BLOCK, METHODS, play


def test_compose_is_invariant_to_donor_rank_coordinates():
    rng = np.random.default_rng(11)
    a, b = rng.normal(size=(3, 13)), rng.normal(size=(9, 3))
    c, d = rng.normal(size=(3, 13)), rng.normal(size=(9, 3))
    target = (b @ a + d @ c) / 2
    u, s, vh = np.linalg.svd(target, full_matrices=False)
    optimal = (u[:, :3] * s[:3]) @ vh[:3]
    for ca, db in ((c, d), (-c, -d)):
        x, y = compose(a, b, ca, db, 3)
        np.testing.assert_allclose(y @ x, optimal, atol=1e-10)
        full_a, full_b = compose(a, b, ca, db, 6)
        np.testing.assert_allclose(full_b @ full_a, target, atol=1e-10)
    assert energy(b, a) == pytest.approx(np.linalg.norm(b @ a) ** 2)


def test_native_fusion_exam_uses_four_distinct_available_worlds():
    assert len({tuple(secret(seed, "affine")) for seed in AFFINE_SEEDS}) == 4


def test_sparse_terms_and_single_live_synapse_reproduce_the_same_scalar():
    torch.manual_seed(11)
    x = torch.randn(19, 12)
    idx = torch.tensor([0, 1, 12, 43, 90], dtype=torch.uint8)
    coef = torch.randn(len(idx)).half()
    z = features(x, 2)[:, idx.long()] @ coef.float()
    torch.testing.assert_close(sparse_value(x, idx, coef), z)
    head = torch.nn.Linear(7, 1)
    torch.testing.assert_close(inject(head, z), z)
    with torch.no_grad():
        head.weight.zero_()
    with pytest.raises(ValueError, match="active synapse"):
        inject(head, z)


def test_steering_has_same_full_readout_as_folded_weights():
    torch.manual_seed(13)
    dictionary = torch.randn(23, 8)
    ids = [2, 4, 6, 7]
    row = surgery_diagnostics(torch.randn(11, 8), dictionary[ids], dictionary, ids, torch.randn(4, 8))
    assert row["max_full_vocab_fold_error"] < 2e-5
    assert row["candidate_logits_max_difference"] < 2e-5


def test_early_exit_checks_the_entire_prefix_including_rare_codes():
    grid = torch.zeros((256, 256), dtype=torch.uint8)
    grid[1, 2] = 3
    budget = bit_budget(grid)
    codes = torch.tensor([[0, 0], [1, 1], [1, 2], [54, 54], [255, 255]])
    bits = budget[codes[:, 0], codes[:, 1]].long()
    assert bits.tolist() == [8, 8, 8, 4, 2]
    assert torch.equal(decode(grid, codes), decode(grid, prefix_center(codes, bits[:, None])))


def test_style_and_factual_content_receive_separate_scores():
    facts = ("Friday", "Cedar")
    assert markers("Hey, you're set for Friday at Cedar!", facts) == {
        "both_facts": True, "formal_marker": False, "casual_marker": True, "one_sentence": True}
    assert not markers("I confirm Friday at Cedar is canceled.", facts)["both_facts"]
    assert not markers("I confirm Thursday at Cedar.", facts)["both_facts"]
    assert not one_sentence("Hi Jo,\n\nFriday at Cedar. Let me know what works!")
    line, repaired = checked_style("Dear Jo, the code is", "formal", "Jo", "the cobalt badge code is 731", ("cobalt", "731"))
    assert repaired and "731" in line
    assert checked_style(line, "formal", "Jo", "the cobalt badge code is 731", ("cobalt", "731")) == (line, False)
    with pytest.raises(ValueError):
        checked_style("Hey Jo!", "casual", "Jo", "a badge is ready", ("cobalt", "731"))
    reversed_role = "Hey Jo, you're assigned to K427 and Rowan heard about it!"
    statement = "ticket K427 has been assigned to Rowan"
    assert markers(reversed_role, ("K427", "Rowan"))["both_facts"]
    assert checked_style(reversed_role, "casual", "Jo", statement, ("K427", "Rowan")) == (
        "Hey Jo, ticket K427 has been assigned to Rowan.", True)


def test_audited_policies_cannot_buy_extra_truth_or_quarantine_a_clean_sender():
    station = np.arange(1024) % 4
    pred = np.ones((len(station), 2), dtype=bool)
    data = (station, None, pred, pred[:, 0])
    for method in METHODS:
        exact = play(data, 19, method, False, False)
        assert exact["audits"] == len(station) // BLOCK
        assert exact["true_pass"] == 1 and exact["flagged_healthy_stations"] == 0
