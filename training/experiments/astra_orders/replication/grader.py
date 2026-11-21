"""Independent reference grades for scoring after seat selection. Never imported by inference or routing."""
import json


def grade(row, answer, folder):
    raw = row["payload"]
    if row["family"] == "delayed-release":
        end = total_wait = 0
        for _, arrival, duration in raw["bookings"]:
            wait = max(0, end - arrival)
            total_wait += wait
            end = arrival + wait + duration
        return answer.strip() == f"{total_wait}\n{end}"
    if row["family"] == "careful-meter":
        readings = raw["readings"]
        top = 2 ** raw["bits"]
        expected = [b - a if b >= a else top - a + b for a,b in zip(readings, readings[1:])]
        filename, printed = "pulses.json", sum(expected)
    else:
        sorted_rises = sorted(((a-b, code) for code, a, b in raw["data"] if b - a >= raw["threshold"]))
        expected = [code for _,code in sorted_rises]
        filename, printed = "drift.json", len(expected)
    try:
        actual = json.loads((folder / filename).read_bytes())
    except (OSError, ValueError, UnicodeError):
        return False
    return json.dumps(actual) == json.dumps(expected) and answer.strip() == str(printed)
