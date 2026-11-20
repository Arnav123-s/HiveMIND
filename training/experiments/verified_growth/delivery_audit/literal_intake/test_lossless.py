from . import intake, lossless


BASE = "Create wheel.py. turn(2) gives 6. snap(3) gives 12."


def test_every_call_counted():
    complete = BASE + " Print the values of turn(7) and snap(9)."
    assert lossless.contract(complete) == intake.contract(complete)
    for missing in ("For the customer: turn(7). ", "For the customer: snap ( [ 'a) b' ] ). "):
        assert intake.contract(missing+BASE) is not None
        assert lossless.contract(missing+BASE) is None


def test_duplicate_roles_withhold():
    for tail in (" Then print the value of turn(2).", " Print the values of snap(9) and snap(9).",
                 " turn(2) is 6."):
        assert intake.contract(BASE+tail) is not None
        assert lossless.contract(BASE+tail) is None
