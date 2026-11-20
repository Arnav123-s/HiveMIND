"""Post-study controls for the service calculator; keep the original experiment immutable."""
from datetime import date
from decimal import Decimal, Inexact, ROUND_HALF_DOWN, ROUND_HALF_UP, localcontext

from training.experiments.atlas.pulse.one_checked import certificate as historical, current


def test_supported_dates_match_original_and_gregorian_calendar():
    for year in (1, 4, 1582, 1900, 1999, 2000, 2024, 2100, 2400, 9999):
        for month, name in enumerate(current.MONTHS, 1):
            for day in (0, 1, 15, 28, 29, 30, 31, 32):
                try:
                    target = date(year, month, day)
                except ValueError:
                    target = None
                for text in (f'{day} {name.title()} {year:04}', f'{year:04}-{month:02}-{day:02}'):
                    weekday = f'What day of the week is {text}?'
                    elapsed = f'How many days are there from {year:04}-01-01 to {text}?'
                    want_day = ('weekday', current.WEEKDAYS[target.weekday()]) if target else None
                    want_days = ('days', (target-date(year,1,1)).days) if target else None
                    assert current.expected(weekday) == historical.expected(weekday) == want_day
                    assert current.expected(elapsed) == historical.expected(elapsed) == want_days
    for text in ('01/02/2024', '1 jan 2024', '2024-01-01 12:00', '30 Foober 2024', '0000-01-01'):
        assert current.expected(f'Which day of the week is {text}?') is None


def test_cents_and_rounding_are_independent_of_callers_decimal_context():
    house = 'A house costs 99999999 dollars and the price rises by 10%. What is the new price?'
    assert not historical.certify(house, '109999998.90 dollars')
    for rounding in (ROUND_HALF_UP, ROUND_HALF_DOWN):
        with localcontext() as cfg:
            cfg.prec = 3
            cfg.rounding = rounding
            cfg.traps[Inexact] = True
            assert current.expected(house) == ('dollars', Decimal('109999998.90'))
            assert current.certify(house,'109999998.90 dollars')
            assert not current.certify(house,'109999998.90 euros')
            assert current.expected('A part costs 0.05 dollars and the price rises by 10%. What is the new price?') is None
            for num, src, dest in [('0.25','Celsius','Fahrenheit'),('-0.25','Celsius','Fahrenheit'),
                                   ('32.09','Fahrenheit','Celsius'),('31.91','Fahrenheit','Celsius')]:
                assert current.expected(f'What is {num} degrees {src} in {dest}? One decimal place.') is None
            for num, want in [('32.089','0.0'),('32.091','0.1')]:
                prompt = f'What is {num} degrees Fahrenheit in Celsius? One decimal place.'
                assert current.certify(prompt, want+' °C')
                assert not current.certify(prompt, want+' °F')
