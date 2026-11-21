from training import grow


def test_short_trial_precheck_reserves_time_for_learning_and_remeasurement():
    begin = 1000
    ready = begin + 45 * 60
    # Of the 40 minutes left, at most 10 each are reserved for the two measurements.
    assert grow.precheck_deadline(begin, ready, 85, "85") == ready + 10 * 60
    assert grow.precheck_deadline(begin, ready, 110, "110") == ready + 65 * 60 / 4
    late = begin + 90 * 60
    assert grow.precheck_deadline(begin, late, 85, "85") == late
    for profile in ("auto", "170"):
        assert grow.precheck_deadline(begin, ready, 170, profile) == 0


def test_cut_short_comparison_uses_the_same_rows():
    report = grow.paired_kept_losses(
        {"task1": "x", "task2": "y", "task3": "z"},
        {"x": [2.0, 90.0], "y": [1.0, 5.0], "z": [3.0]},
        {"x": [1.0], "y": [1.0, 3.0]},
    )
    assert report == {
        "x": {"lessons": 1, "rows": 1, "before": 2.0, "after": 1.0},
        "y": {"lessons": 1, "rows": 2, "before": 3.0, "after": 2.0},
        "z": {"lessons": 1, "rows": 0, "before": None, "after": None},
    }


def test_expired_slice_does_not_export_an_untrained_adapter(tmp_path, monkeypatch):
    import pytest
    from test_held_out import _rows, _train

    with pytest.raises(RuntimeError, match="zero optimizer updates"):
        _train(tmp_path, monkeypatch, _rows(), "", checkpoint=False, minutes=1e-12)
    assert not list((tmp_path / "out").glob("*.gguf"))
    assert not list((tmp_path / "grow").rglob("adapter_model.safetensors"))
