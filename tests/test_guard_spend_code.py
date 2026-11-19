"""team/guard.py CODE_RULES "spend": real spending in code stays blocked; the word in the task's own data is no spending.
g48's c10004810_01 (h_tab_jsonl) was refused three times for a JSON string "needs Arnav's approval; not run"."""
import pytest

from team import guard

DATA = ('import json\nrows = json.loads("""[{"id": 1, "kind": "purchase", "note": "needs Arnav\'s approval; not run"},\n'
        '{"id": 2, "kind": "payment", "note": "checkout page, not run"}]""")\n'
        'bought = [r for r in rows if r["kind"] == "purchase"]\nprint("purchases:", len(bought))\n'
        'def purchases(rows):\n    return [r for r in rows if "purchase" in r["kind"]]\nprint(purchases(rows), "purchase (done)")\n')

SPENDING = ["import stripe\nstripe.Charge.create(amount=5)", "from paypalrestsdk import Payment", "cart.checkout()",
            "purchase(item)", "shop.buy(item, qty=2)", "pay(card, 40)", "requests.get('https://shop.example.com/checkout?id=3')",
            "urlopen('https://api.razorpay.com/v1/orders')", "make_payment(card)", "driver.add_to_cart(x)"]


def _check(code):
    g = guard.Guard.__new__(guard.Guard)
    asked = []
    g.ask = lambda agent, kind, what: asked.append((kind, what)) and False
    return guard.Guard.check_code(g, "coder", code), asked


def test_the_word_in_the_tasks_own_data_is_not_spending():
    ok, asked = _check(DATA)
    assert ok and not asked


@pytest.mark.parametrize("code", SPENDING)
def test_real_spending_in_code_is_still_blocked(code):
    ok, asked = _check(code)
    assert not ok and asked[0][0] == "spend"
