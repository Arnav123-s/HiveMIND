from . import intake, lossless, multiplicity
from .test_lossless import BASE


def test_explicit_repeats_with_defined_roles():
    for tail in (" Then print the value of turn(2).", " Print the values of snap(9) and snap(9)."):
        assert multiplicity.contract(BASE+tail) == intake.contract(BASE+tail)
        assert multiplicity.contract(BASE+tail) is not None
        assert lossless.contract(BASE+tail) is None


def test_unaccounted_repetitions_still_withhold():
    for q in ("For the customer: turn(2). "+BASE, BASE+" snap(3) gives 12.",
              BASE+" For the customer: turn(7)."):
        assert intake.contract(q) is not None
        assert multiplicity.contract(q) is None
