"""Benign development controls. All fixtures use made-up names and literal arithmetic."""
from .intake import contract, normalized
from training.experiments.verified_growth.file_relay import relay


BODY = "Write and save toy.py with two functions. 1) bloom(x) adds one (bloom(2) is 3). 2) shade(x) doubles (shade(4) should return 8)."
CASES = [(("bloom", [2]), 3), (("shade", [4]), 8)]
QUERIES = [("bloom",[6]), ("shade",[9])]


def test_varied_order_and_layout():
    endings = ["Then tell me, each on its own line, the values of bloom(6) and of shade(9).",
               "Print the outputs of bloom(6), followed by shade(9), in that order.",
               "Give me the results for `bloom(6)` and `shade(9)`, one per line."]
    for q in endings:
        for request in (BODY+" "+q, q+" "+BODY):
            spec = contract(request)
            assert spec == ("toy.py", {"bloom","shade"}, CASES, QUERIES)
            assert relay.contract(normalized(spec))==spec
    assert contract(BODY)[3]==[]


def test_inputs_and_checks_are_literals():
    for text in [
        BODY.replace(" is 3", " is not 3"), BODY.replace(" is 3", " is 3 or 5"),
        BODY.replace(" is 3"," is 3+1"), BODY.replace("should return 8","might return 8"),
        BODY.replace("shade(4)","shade(x)"), BODY+" bloom(2) returns 7.",
        BODY+" Also tell me the values of bloom(6) and mystery(3).",
        BODY+" Then print bloom(6) and explain why.", BODY+" Print the source files.",
        BODY.replace("two functions", "three functions"), BODY.replace("toy.py","/tmp/toy.py"),
        BODY+" Also implement functions bloom and absent.", BODY+" Also save data.csv.", BODY.replace("toy.py","a file"), BODY+" Print bloom(variable).",
        "Read toy.py. bloom(2) = 3; bloom(5) = 6.",
    ]:
        assert contract(text) is None, text
