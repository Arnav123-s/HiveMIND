"""Generate fresh prompts and keys without calling any project calculator."""
import calendar
import json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent


def weekday(y, m, d):
    return calendar.day_name[date(y, m, d).weekday()].lower()


def days(start, end):
    return (date(*end) - date(*start)).days


def weekdays_inclusive(start, end):
    lo, hi = date(*start), date(*end)
    return sum((lo + timedelta(days=i)).weekday() < 5 for i in range((hi-lo).days+1))


# Honest user-goal coverage includes answerable questions outside a narrow converter.
ROWS = [
    ("poster", "What day of the week is 2029-09-16?", "direct", weekday(2029,9,16)),
    ("appointment", "Which weekday is 17 September 2034?", "wording", weekday(2034,9,17)),
    ("delivery", "What weekday does 2032-03-08 fall on?", "wording", weekday(2032,3,8)),
    ("ticket", "My bus ticket says 3 August 2036. Which weekday is that?", "wording", weekday(2036,8,3)),
    ("diary", "Tell me the weekday for 2035-04-12.", "wording", weekday(2035,4,12)),
    ("new-year", "How many days are there from 2040-12-31 to 2041-01-01?", "direct", days((2040,12,31),(2041,1,1))),
    ("gap", "What is the gap in days from 2033-07-08 to 2033-07-29?", "wording", days((2033,7,8),(2033,7,29))),
    ("leap", "How many days elapsed between 2028-02-28 and 2028-03-02?", "wording", days((2028,2,28),(2028,3,2))),
    ("hostel", "I checked into a hostel on 11 May 2032 and left on 14 May 2032. How many calendar days elapsed?", "wording", days((2032,5,11),(2032,5,14))),
    ("milestones", "Both milestones take place on 2038-06-19. How many calendar days separate those dates?", "wording", 0),
    ("endpoints", "Counting both endpoints, how many calendar dates run from 2044-04-11 through 2044-04-13?", "neighbor", 1+days((2044,4,11),(2044,4,13))),
    ("workweek", "Counting Monday to Friday only and including both endpoints, how many weekdays fall from June 6, 2031 to June 10, 2031?", "neighbor", weekdays_inclusive((2031,6,6),(2031,6,10))),
    ("following", "What weekday is the day after 2030-10-09?", "neighbor", weekday(2030,10,10)),
    ("holiday", "What weekday is my next holiday?", "underspecified", None),
    ("invalid", "Which day of the week is 2035-02-29?", "invalid", None),
    ("locale", "What weekday is 04/07/2036?", "underspecified", None),
    ("midnight", "At 00:15 UTC on 2043-12-16, what weekday is it in my local time zone?", "underspecified", None),
    ("tentative", "Our trip will start on either 8 June or 10 June 2037 and end on 19 June. How many days will actually elapse?", "underspecified", None),
]

if __name__ == "__main__":
    assert weekday(2036,4,7) != weekday(2036,7,4)
    assert len(ROWS) == len({r[0] for r in ROWS}) == 18
    for name, obj in {
        "panel.json": [dict(id=i, question=q, group=g) for i, q, g, _ in ROWS],
        "keys.json": {i:dict(value=v, group=g) for i, _, g, v in ROWS},
    }.items():
        (HERE / name).write_text(json.dumps(obj, indent=2) + "\n")
