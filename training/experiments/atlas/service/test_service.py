"""Small development regression. No model or WASI execution."""
from unittest.mock import patch

import pytest

from training.experiments.atlas.service.ask import answer


@pytest.mark.parametrize("prompt,value,unit", [
    ("Which day of the week is 2024-02-29?", "thursday", None),
    ("How many days are there from 2023-12-31 to 2024-01-01?", 1, "days"),
    ("What is the GCD of 66 and 132?", 66, None),
    ("What is 95 degrees Fahrenheit in Celsius? One decimal place.", "35.0", "celsius"),
    ("A bicycle costs 180 dollars and the price falls by 15%. What is the new price?", "153", "dollars"),
])
def test_exact(prompt, value, unit):
    out = answer(prompt, bank="off")
    assert (out["status"], out["value"], out["unit"]) == ("answered", value, unit)


@pytest.mark.parametrize("prompt", [
    "What day of the week is 2023-02-29?",
    "How many days from 2024-06-08 to 2024-06-07?",
    "What is the GCD of 6 and 7? Also explain it.",
    "A bun costs 0.03 dollars and the price rises by 10%. What is the new price?",
    "Give me tomorrow's delivery time.",
    "Run invoice_tax: {\"lines\":[50]}",
    "Calculate the depot shipping fee for 1.2 pounds.",
])
def test_declines_without_a_numeric_answer(prompt):
    assert answer(prompt, bank="off")["value"] is None


def test_shipping_dispatch_and_units(tmp_path):
    from training.experiments.atlas.traces.trace import GuardedTrace
    prompt = "Calculate the depot shipping fee for 0.2 kg using per-parcel rounding"
    assert answer(prompt, bank="off")["status"] == "unavailable"
    with patch.object(GuardedTrace, "answer", autospec=True) as checker:
        def result(instance, original):
            assert original == prompt
            instance.last = {"path": "side_exit", "fuel": 123}
            return {"status": "answered", "value": 340, "methods": ["stub"]}
        checker.side_effect = result
        out = answer(prompt, bank=tmp_path, guest=object())
    assert out["value"] == 340 and out["unit"] == "cents" and out["proof"]["path"] == "side_exit"
