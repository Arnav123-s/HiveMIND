"""The ordinary CSV command uses the frozen rule and reports missing coverage."""
from pathlib import Path

import pytest

from team import cli


def test_tidal_observations_via_cli(capsys):
    data = Path(__file__).resolve().parents[1] / "training/reports/checked-repair/san-francisco-tide.csv"
    assert cli.main(["exposure", str(data), "--threshold", "1.5", "--max-gap", "6"]) == 0
    text = capsys.readouterr().out
    assert "268.9090909 minutes" in text and "Upward crossings: 1" in text and "239 of 239" in text


def test_numeric_units_custom_columns_and_discontinuities(tmp_path, capsys):
    data = tmp_path / "log.csv"
    data.write_text("elapsed,temperature\n0,10\n2,0\n3,NA\n4,8\n9,8\n10,8\n")
    cli.main(["exposure", str(data), "--threshold", "5", "--max-gap", "2", "--unit", "hours",
              "--time-column", "elapsed", "--value-column", "temperature"])
    text = capsys.readouterr().out
    assert "2 hours" in text and "Upward crossings: 0" in text and "2 of 5" in text


def test_timezone_offsets_compare_as_instants(tmp_path, capsys):
    data = tmp_path / "log.csv"
    data.write_text("timestamp,value\n2025-06-01T02:00:00+02:00,5\n2025-06-01T00:00:10Z,9\n")
    cli.main(["exposure", str(data), "--threshold", "5", "--max-gap", "10", "--unit", "seconds"])
    assert "10 seconds" in capsys.readouterr().out


@pytest.mark.parametrize(("rows", "error"), [
    ("2,1\n1,2", "strictly increasing"),
    ("1,1\n1,2", "strictly increasing"),
    ("1,1\n2,NaN", "finite number"),
    ("1,1\ninf,2", "finite number"),
    ("1,1\n,2", "timestamp"),
    ("2025-01-01T00:00Z,1\n2025-01-01T00:01,2", "time format"),
    ("0,1\n2", "row width"),
])
def test_bad_data_reports_line(tmp_path, capsys, rows, error):
    data = tmp_path / "bad.csv"
    data.write_text("timestamp,value\n" + rows + "\n")
    with pytest.raises(SystemExit) as exc:
        cli.main(["exposure", str(data), "--threshold", "1", "--max-gap", "1"])
    message = capsys.readouterr().err
    assert exc.value.code == 2 and "line 3" in message and error in message


def test_no_intervals_are_measurable(tmp_path, capsys):
    data = tmp_path / "log.csv"
    data.write_text("timestamp,value\n0,5\n1,\n2,8\n")
    cli.main(["exposure", str(data), "--threshold", "5", "--max-gap", "1"])
    text = capsys.readouterr().out
    assert "could not be measured" in text and "0 of 2" in text


def test_decimal_intervals_at_gap_limit_and_large_finite_readings(tmp_path, capsys):
    data = tmp_path / "log.csv"
    data.write_text("timestamp,value\n0.2,-1e308\n0.3,1e308\n0.4,-1e308\n")
    cli.main(["exposure", str(data), "--threshold", "0", "--max-gap", "0.1"])
    text = capsys.readouterr().out
    assert "0.1 minutes" in text and "Upward crossings: 1" in text and "2 of 2" in text
