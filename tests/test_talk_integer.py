"""Formatting checked program output on requests for one integer."""
import pytest

from team import domain_route, solo, talk


@pytest.mark.parametrize(("printed", "expected"), [
    ("+00017", "+00017"), ("-000", "-000"), ("0009", "0009"),
    ("+00017.0000", "17"), ("-100.000", "-100"), ("-.0000", "0"), ("2.", "2"),
    ("+.018e+3", "18"), ("-1200E-2", "-12"), ("09e0002", "900"),
    ("123456789012345678901234567890.000", "123456789012345678901234567890"),
])
def test_preserve_exact_literal(printed, expected):
    assert talk._exact_integer(printed) == expected


@pytest.mark.parametrize('printed', [
    '0.0000000000001', '-0.99', '1.000000000000000000000000000001', '1E-9999',
    '1e9999', '1e1000000000000000000000000000000', '4.0 / 2', '2.0 kg', '01/02/2027',
    '2027-01-02','NaN','-Infinity','18.0\n## Discounts\n5.0','1_000.0','1,000.0','0xA',
])
def test_does_not_expand_or_coerce_other_answers(printed):
    assert talk._exact_integer(printed) is None


def test_expansion_length_includes_minus_sign():
    assert len(talk._exact_integer('1e2999')) == 3000
    assert talk._exact_integer('-1e2999') is None
    assert talk._exact_integer('1e3000') is None


@pytest.mark.parametrize(('printed','requested','expected','rephrased'), [
    ('0032.000', 'Reply with JUST THE INTEGER.', '32', False),
    ('24.0', 'Just the integer.', '24', False),
    ('-12.2', 'Just the integer, please.', '-12.2', True),
    ('1e9999999', 'Give me only one integer.', '1e9999999', True),
    ('6.0\n## Breakdown\nThere were two groups.', 'Print as a single integer.', '6.0\n## Breakdown\nThere were two groups.', True),
    ('0.0', 'Explain the total.', '0.0', True),
])
def test_uses_only_verified_program_output(monkeypatch, tmp_path, printed, requested, expected, rephrased):
    rewrites=[]
    monkeypatch.setattr(talk, 'local_reply', lambda *a, **kw: None)
    monkeypatch.setattr(talk, 'route', lambda *a: ('work', []))
    monkeypatch.setattr(domain_route, 'prepare_advice', lambda *a, **kw: None)
    from team import engram
    monkeypatch.setattr(engram, 'for_request', lambda *a, **kw: [])
    monkeypatch.setattr(solo, 'first', lambda *a, **kw: {'report':printed+'\n\n## How it was checked\nTwo agreed.\n',
                                                         'agreed':True,'files':[]})
    def rewrite(*a, **kw):
        rewrites.append(True)
        return ''
    monkeypatch.setattr(talk.ternary, 'chat', rewrite)
    result=talk.reply('I guessed 99. '+requested, base='t80',run_dir=tmp_path/'run')
    assert result['text'] == expected
    assert bool(rewrites) == rephrased


def test_preserve_extreme_or_precise_printed_values_when_checking_a_rewrite():
    assert talk._values('1e9999999') != talk._values('1e9999998')
    assert talk._values('1.000000000000000000000000000001') != talk._values('1')
