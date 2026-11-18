"""The talk exam: 40 messages, made by code and checked by code, sat through the hive's one door (team/talk.py).

    python training/talk_exam.py show --seed N              the messages of a sitting and what each must get right
    python training/talk_exam.py sit --seed N [--who t17|body] [--out FILE.json] [--only route,fact,...] [--port P]
                                     [--minutes M] [--per S]
                                                            sit it: every message goes to team.talk.reply

A sitting can be held to time (the grow line sits it every generation, and it must never slow or break the line):
--minutes is the whole sitting's budget and --per the most seconds one message may take. With either, each message is
sat in a process of its own, ended (its programs with it) at its cap or at the end of the budget; such a message, and
every one the budget does not reach, counts as failed for "time", and the sitting ends cleanly with its json written.

Four kinds, ten messages each, every one drawn from a template with new values (the same seed, the same exam). The
messages sit on the edges where a weak talker slips, and each check names the near miss that is wrong:

  route    talk or work, on the border: a sum done in the head (7 times 8) against one that is not (4817 times 362);
           "look up" what was said in this very chat, or a capital, against a price that changes today; explain a
           concept against write a program and run it. The check is the way team/talk.py took (talk.route, the very
           decision reply() makes); nothing is answered for these.
  fact     a fact given in the message (or the turns just before) must come back right, beside a similar value that
           is not the answer (two rooms, two times, two gates), or after a correction ("actually it moved to room
           412"), or out of a long message full of other numbers and codes.
  earlier  a conversation of 4 to 8 earlier turns (the hive's own turns written out here): the item asked for is one
           of several, or the hive's own earlier answer, or was changed later on (a new name, another book).
  time     the hive is told the date and time (reply's `now`), on the edges: across the end of a month or a year,
           February in leap and common years, hours back across midnight, time zones given in the message, the
           weekday many days back.

Every check is code (numbers, dates, weekdays and times read out of the reply; words matched after lower-casing and
dropping punctuation); no model judges. Where a check names near misses ("not"), the first of the answer and the near
misses that the reply names must be the answer ("412, it moved from 318" is right, "318... or 412" is wrong); a value
under "never" must not be named at all; a reply that says it does not know is wrong. The score is out of 40, and out
of 10 for the goal's table (bar: 8 of 10).
"""
import datetime
import json
import os
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KINDS = ("route", "fact", "earlier", "time")
EACH = 10
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
OUT = ROOT / "training" / "reports" / "talk"

# ---- values -----------------------------------------------------------------------------------------------------------
NAMES = ["Priya", "Tomasz", "Aiko", "Mateo", "Fatima", "Lars", "Noor", "Kofi", "Elena", "Ravi", "Ines", "Jonas", "Mei", "Omar", "Sofia", "Dmitri"]
CITIES = ["Lyon", "Porto", "Krakow", "Valencia", "Leeds", "Ghent", "Bergen", "Turin", "Graz", "Malmo", "Cork", "Bilbao", "Utrecht", "Tampere"]
CAPITALS = {"Peru": "Lima", "Kenya": "Nairobi", "Norway": "Oslo", "Chile": "Santiago", "Vietnam": "Hanoi", "Portugal": "Lisbon",
            "Egypt": "Cairo", "Canada": "Ottawa", "Poland": "Warsaw", "Ghana": "Accra"}
PETS = ["Biscuit", "Pepper", "Juniper", "Mochi", "Rufus", "Clover", "Ziggy", "Hazel", "Otis", "Pickle"]
BOOKS = ["The Silent Orchard", "A River of Glass", "Northern Lanterns", "The Clockmaker's Garden", "Paper Comets", "Salt and Cedar"]
JOBS = ["nurse", "carpenter", "librarian", "pilot", "baker", "geologist", "translator", "plumber"]
THINGS = ["bread", "batteries", "lemons", "stamps", "rice", "candles", "soap", "tea", "glue", "onions", "envelopes", "honey"]
CONCEPTS = ["recursion", "a hash table", "binary search", "an API", "a race condition", "object-oriented programming", "a database index"]
ZONES = [("Lisbon", 0), ("Berlin", 1), ("Athens", 2), ("Dubai", 4), ("Singapore", 8), ("Tokyo", 9), ("New York", -5), ("Chicago", -6), ("Sao Paulo", -3)]
# small talk between the turns that matter: no digits, names, cities, weekdays or shopping things in them
FILLERS = [("What's a good way to stay focused when I work?", "Short breaks help: work for a while, then rest a little, and keep your phone in another room."),
           ("Tell me a fun fact.", "Octopuses have three hearts."),
           ("How do I keep basil alive on a windowsill?", "Give it plenty of light, water it when the soil feels dry, and pinch off the flowers."),
           ("Any tips for sleeping better?", "Keep the same bedtime, avoid screens late in the evening and keep the room cool and dark."),
           ("Why is the sea salty?", "Rivers carry minerals from rocks into the sea, and when the water evaporates the salt stays behind."),
           ("Do you have a tip for remembering things?", "Write them down, or tie each one to a picture in your head."),
           ("What's a nice thing to cook on a rainy evening?", "A thick vegetable soup with a crusty loaf is hard to beat."),
           ("Why do cats purr?", "Mostly when they are content, but sometimes also to calm themselves."),
           ("How do I get better at drawing?", "Draw a little every day, and draw what you see rather than what you remember."),
           ("Should I stretch before or after running?", "A short warm-up before, and gentle stretching after.")]


def _code(r, letters=2, digits=4):
    return "".join(r.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(letters)) + "".join(r.choice("0123456789") for _ in range(digits))


def _turns(pairs):
    return [m for u, a in pairs for m in ({"role": "user", "content": u}, {"role": "assistant", "content": a})]


def _hm(h, m):
    return f"{h % 24:02d}:{m:02d}"


def _utc(k):
    return f"UTC{'+' if k >= 0 else '-'}{abs(k)}"


# ---- the four kinds -----------------------------------------------------------------------------------------------
def m_route(r, i):
    """Five templates of talk and five of work, each on the border with one of the other side: (message, history, check)."""
    a, b = r.randint(3, 9), r.randint(3, 9)
    n1, c1, country = r.choice(NAMES), r.choice(CITIES), r.choice(sorted(CAPITALS))
    day, hh, mm = r.choice(WEEKDAYS).title(), r.randint(8, 17), r.choice([0, 15, 30, 45])
    concept = r.choice(CONCEPTS)
    talk = [  # done in the head, or said already in this chat, or a thing that does not change
        (r.choice([f"quick one: what is {a} times {b}?", f"what's {a} plus {b}?", f"what is {10 * a} minus {b}?", f"what is half of {2 * a}?"]), []),
        (r.choice([f"can you look up when my appointment with {n1} is?", f"please look up what I told you about the appointment with {n1}",
                   f"look up the time of my appointment with {n1} for me"]),
         _turns([(f"My appointment with {n1} is on {day} at {hh}:{mm:02d}.", "Noted, I'll remember that."), r.choice(FILLERS)])),
        (r.choice([f"can you explain what {concept} is, in simple words?", f"how does {concept} work? no code please, just the idea",
                   f"what is {concept}, and why do programmers use it?"]), []),
        (r.choice([f"look up the capital of {country} for me", f"how many {r.choice(['legs does a spider have', 'sides does a hexagon have', 'players are on a football team', 'minutes are in an hour'])}?",
                   f"do you know the capital of {country}?"]), []),
        (r.choice(["make this sound more polite: 'send me the report by friday or else'", "fix the grammar: 'me and him goes to the shop yesterday'",
                   f"summarise in one sentence: '{n1} missed the bus, walked to work in the rain, and still got there before everyone else.'"]), []),
    ]
    big = [r.randint(120, 9800) for _ in range(8)]
    people = r.sample(NAMES, 6)
    work = [  # worked out with programs, or read from a source that changes
        (r.choice([f"what is {r.randint(1200, 9800)} times {r.randint(130, 980)}?", f"what's {r.randint(10000, 99999)} divided by {r.choice([7, 13, 17, 23])}, to three decimals?",
                   f"add these up for me: {', '.join(map(str, big))}"]), []),
        (r.choice([f"write a python program that prints the first {r.randint(15, 40)} prime numbers and show me what it prints",
                   f"write code that checks whether '{r.choice(['racecar', 'level', 'rotator', 'banana'])}' is a palindrome and run it",
                   f"can you write a function that counts the vowels in a text, and test it on '{c1} in the rain'?"]), []),
        (r.choice(["look up the price of bitcoin right now", f"look up today's weather in {c1}", "what's the exchange rate from euro to yen today?",
                   "who won the football match last night?"]), []),
        (r.choice([f"which day of the week was {r.randint(1, 28)} {r.choice(MONTHS).title()} {r.randint(1950, 2010)}?",
                   f"how old is someone born on {r.randint(1, 28)} {r.choice(MONTHS).title()} {r.randint(1950, 2010)}, today?"]), []),
        (r.choice(["here are the test scores: " + ", ".join(f"{p} {r.randint(41, 99)}" for p in people) + ". who came second, and what is the average?",
                   f"in this list, which number appears most often: {', '.join(str(r.randint(1, 9)) for _ in range(25))}?"]), []),
    ]
    msg, history = (talk + work)[i]
    return msg, history, {"type": "route", "want": "talk" if i < len(talk) else "work"}


def m_fact(r, i):
    """A fact in the message or the turns just before, beside a near miss or after a correction: (message, history, check)."""
    n1, n2, n3 = r.sample(NAMES, 3)
    a1, a2 = r.sample(range(19, 78), 2)
    r1, r2 = r.sample(range(101, 999), 2)
    g1, g2 = f"{r.choice('ABCDEFG')}{r.randint(2, 48)}", f"{r.choice('ABCDEFG')}{r.randint(2, 48)}"
    while g2 == g1:
        g2 = f"{r.choice('ABCDEFG')}{r.randint(2, 48)}"
    f1, f2 = _code(r, 2, 4), _code(r, 2, 4)
    w1, w2 = (f"{r.choice(['maple', 'otter', 'violet', 'harbor', 'comet', 'pebble'])}{r.randint(1000, 9999)}" for _ in range(2))
    c1, c2 = r.sample(CITIES, 2)
    t1, t2 = (_hm(h, m) for h, m in zip(r.sample(range(9, 18), 2), (r.choice([0, 15, 30, 45]), r.choice([0, 15, 30, 45]))))
    p1, p2, p3 = r.sample(range(45, 140), 3)
    h1, h2 = r.sample(range(2, 99), 2)
    group, hotel = _code(r, 2, 4), _code(r, 2, 4)
    t3, t4 = _hm(r.randint(18, 19), r.choice([0, 30])), _hm(r.randint(20, 21), r.choice([0, 15, 30]))
    made = [
        (f"The design review is in room {r1} and the budget meeting is in room {r2}. Which room is the budget meeting in?", [],
         {"type": "number", "want": r2, "not": [r1]}),
        (f"The workshop with {n1} is in room {r1}. Oh wait, I just got an email: actually it moved to room {r2}. Where is the workshop now?", [],
         {"type": "number", "want": r2, "not": [r1]}),
        (f"Lunch with {n1} is at {t1} and the call with {n2} is at {t2}. When is the call with {n2}?", [], {"type": "clock", "want": t2, "not": [t1]}),
        (f"My flight {f1} leaves from gate {g1}; my brother's flight {f2} leaves from gate {g2}. Which gate does my brother's flight leave from?", [],
         {"type": "text", "want": [[g2]], "not": [g1]}),
        (f"{n1} is {a1} and {n2} is {a2}. Sorry, I mixed them up: {n1} is {a2} and {n2} is {a1}. How old is {n2}?", [],
         {"type": "number", "want": a1, "not": [a2]}),
        (f"The wifi password is {w1}. Hmm, that one doesn't work... the sign by the door says it was changed to {w2}. What's the wifi password?", [],
         {"type": "text", "want": [[w2]], "not": [w1]}),
        (f"In the shop window: the blue jacket costs {p1} euros, the grey one {p2} euros and the green one {p3} euros. How much is the grey jacket?", [],
         {"type": "number", "want": p2, "not": [p1, p3]}),
        (f"Here's the plan for Saturday. We meet at the station at 08:15, bus {r.randint(10, 99)} leaves at 08:40 and gets to {c1} around 11:00. "
         f"The hotel booking reference is {hotel}, check-in from 15:00, room on floor {r.randint(2, 9)}. Lunch is at a place called Salt and Cedar, "
         f"table for {r.randint(3, 9)}. The museum tickets cost {r.randint(12, 30)} euros each, and the group code for them is {group}. My sister's train "
         f"from {c2} gets in at 13:20 on platform {r.randint(2, 14)}. What is the group code for the museum tickets?", [],
         {"type": "text", "want": [[group]], "not": [hotel]}),
        ("What time does the team dinner start?",
         _turns([(f"The team dinner is at the Bilbao Grill at {t3}, table for {r.randint(5, 7)}.", "Lovely, enjoy the evening!"),
                 (f"Change of plan: two more people are coming, so it starts later, at {t4}.", "Noted, thanks for the update.")]),
         {"type": "clock", "want": t4, "not": [t3]}),
        ("Which house number is my parents'?",
         _turns([(f"I live at number {h1} on Mill Street, and my parents live at number {h2} on the same street.", "How handy to live so close!")]),
         {"type": "number", "want": h2, "not": [h1]}),
    ]
    return made[i % len(made)]


def m_earlier(r, i):
    """A conversation of 4 to 8 turns: the turns that matter among small talk (some said by the hive, some changed later),
    then the question."""
    n1, n2, n3 = r.sample(NAMES, 3)
    c1, c2, c3 = r.sample(CITIES, 3)
    p1, p2, p3 = r.sample(PETS, 3)
    b1, b2 = r.sample(BOOKS, 2)
    j1, j2, j3 = r.sample(JOBS, 3)
    s = r.sample(THINGS, 4)
    lucky, house, age = r.sample(range(11, 98), 3)
    soft, hard = r.choice([(5, 9), (6, 10), (6, 11), (7, 12)])
    t1, t2 = (_hm(h, m) for h, m in zip(r.sample(range(9, 18), 2), (r.choice([0, 15, 30, 45]), r.choice([0, 15, 30, 45]))))
    made = [
        ([(f"Hi, I'm {n1}.", f"Hello {n1}, nice to meet you! How can I help?"),
          (f"Oh, one thing: please call me {n2} from now on. It's the name I go by.", "Of course, noted.")],
         "What name should you call me?", {"type": "text", "want": [[n2]], "not": [n1]}),
        ([("Give me three names for a new kitten.", f"How about {p1}, {p2} or {p3}?")],
         "What was the second name you suggested?", {"type": "text", "want": [[p2]], "not": [p1, p3]}),
        ([(f"I need to buy {s[0]}, {s[1]} and {s[2]}.", "Got it, that's your shopping list."), (f"Add {s[3]} to the list, please.", "Added."),
          (f"Actually, I still have {s[1]} at home, take it off.", "Done, it's off the list.")],
         "What's on my shopping list now?", {"type": "text", "want": [[s[0]], [s[2]], [s[3]]], "never": [s[1]]}),
        ([(f"My trip in June: first {c1}, then {c2}, and last {c3}.", "That sounds like a wonderful trip!")],
         f"Which city do I visit right after {c2}?", {"type": "text", "want": [[c3]], "not": [c1]}),
        ([("How long should I boil an egg?", f"About {soft} minutes for a soft yolk, and about {hard} minutes for a hard one.")],
         "How many minutes did you say for a soft yolk?", {"type": "number", "want": soft, "not": [hard]}),
        ([(f"My sister {n1} is a {j1}, my brother {n2} is a {j2} and my cousin {n3} is a {j3}.", "What a mix of jobs in one family!")],
         "What does my brother do?", {"type": "text", "want": [[j2]], "not": [j1, j3]}),
        ([("Which city should I visit in spring?", f"{c1} is lovely in spring."),
          (f"I've been to {c1} already. Another one?", f"Then try {c2}: mild weather and few crowds.")],
         "Which city did you recommend the second time?", {"type": "text", "want": [[c2]], "not": [c1]}),
        ([(f"My lucky number is {lucky}. My house is number {house}, and I'm {age} years old.", "Thanks for telling me a bit about yourself!")],
         "What did I say my lucky number is?", {"type": "number", "want": lucky, "not": [house, age]}),
        ([(f"I'm reading '{b1}' at the moment.", "Enjoy it!"),
          (f"I gave up on '{b1}', it was too slow. I've started '{b2}' instead.", "Fair enough, I hope you like it more.")],
         "Which book am I reading now?", {"type": "text", "want": [[b2]], "not": [b1]}),
        ([(f"Put my two meetings in order: the review with {n2} at {max(t1, t2)} and the call with {n1} at {min(t1, t2)}.",
           f"In order: first the call with {n1} at {min(t1, t2)}, then the review with {n2} at {max(t1, t2)}.")],
         f"What time did you say the review with {n2} is?", {"type": "clock", "want": max(t1, t2), "not": [min(t1, t2)]}),
    ]
    said, ask, check = made[i % len(made)]
    total = r.randint(4, 8)  # turns before the question; the ones that matter keep their order, small talk fills the rest
    at = set(r.sample(range(total), len(said)))
    fill, said = iter(r.sample(FILLERS, total - len(said))), iter(said)
    return ask, _turns([next(said) if k in at else next(fill) for k in range(total)]), check


def _date(d):
    return d.strftime("%Y-%m-%d")


def m_time(r, i):
    """(message, check, now): the hive is told the date and time, and the question sits on an edge of the calendar or the clock."""
    td = datetime.timedelta
    minute = r.choice(range(0, 60, 5))

    def at(y, mo, d, h=None, mi=None):
        return datetime.datetime(y, mo, d, r.randint(8, 18) if h is None else h, minute if mi is None else mi)
    year, mo, d = r.choice([2026, 2027]), r.randint(1, 12), r.randint(1, 28)
    feb = r.choice([2027, 2028])  # 2028 is a leap year, 2027 is not
    if i == 0:  # across the end of a year
        now = at(year, 12, r.randint(22, 31))
        n = (31 - now.day) + r.randint(1, 9)
        later = now + td(days=n)
        return f"What will the date be {n} days from now?", {"type": "date", "want": _date(later), "not": [_date(later.replace(year=now.year))]}, now
    if i == 1:  # February, leap or not
        now = at(feb, 2, r.randint(25, 28))
        n = max(2, (28 - now.day) + r.randint(1, 3))
        later = now + td(days=n)
        other = datetime.date(2028 if feb == 2027 else 2027, 2, now.day) + td(days=n)  # the same days counted in the other kind of year
        return f"What is the date {n} days from today?", {"type": "date", "want": _date(later), "not": [f"{feb}-{other:%m-%d}"]}, now
    if i == 2:  # hours back across midnight
        now = at(year, mo, d, r.randint(0, 2))
        hrs = now.hour + r.randint(1, 5)
        then = now - td(hours=hrs)
        return (f"What was the date and time {hrs} hours ago?",
                {"type": "all", "of": [{"type": "clock", "want": then.strftime("%H:%M")}, {"type": "date", "want": _date(then)}]}, now)
    if i == 3:  # minutes on across midnight, sometimes into a new month
        now = at(year, mo, r.choice([d, (datetime.date(year + mo // 12, mo % 12 + 1, 1) - td(days=1)).day]), 23, r.choice(range(5, 60, 5)))
        mins = r.choice([70, 95, 130, 150])
        then = now + td(minutes=mins)
        return (f"What will the date and time be in {mins} minutes?",
                {"type": "all", "of": [{"type": "clock", "want": then.strftime("%H:%M")}, {"type": "date", "want": _date(then)}]}, now)
    if i == 4:  # the time now in another zone
        now = at(year, mo, d)
        (c1, z1), (c2, z2) = r.sample(ZONES, 2)
        there = now + td(hours=z2 - z1)
        return (f"The time you were given is my local time: I'm in {c1} ({_utc(z1)}). What time is it right now in {c2} ({_utc(z2)})?",
                {"type": "clock", "want": there.strftime("%H:%M"), "not": [now.strftime("%H:%M")]}, now)
    if i == 5:  # a meeting set in another zone
        now = at(year, mo, d)
        (c1, z1), (c2, z2) = r.sample(ZONES, 2)
        h = r.randint(8, 18)
        return (f"My call is at {h}:00 {c1} time ({_utc(z1)}), and I'm in {c2} ({_utc(z2)}). What time is the call for me?",
                {"type": "clock", "want": _hm(h + z2 - z1, 0), "not": [_hm(h, 0)]}, now)
    if i == 6:  # the weekday many days back
        now = at(year, mo, d)
        n = r.choice([k for k in range(10, 60) if k % 7])
        return (f"What day of the week was it {n} days ago?",
                {"type": "weekday", "want": WEEKDAYS[(now - td(days=n)).weekday()], "allow": [WEEKDAYS[now.weekday()]]}, now)
    if i == 7:  # the first of next month
        now = at(year, mo, r.randint(20, 28))
        first = datetime.date(year + mo // 12, mo % 12 + 1, 1)
        return ("What day of the week is the first day of next month?",
                {"type": "weekday", "want": WEEKDAYS[first.weekday()], "allow": [WEEKDAYS[now.weekday()]]}, now)
    if i == 8:  # the last day of February
        now = at(feb, 2, r.randint(1, 20))
        last = 29 if feb % 4 == 0 else 28
        return ("What is the date of the last day of this month?",
                {"type": "date", "want": f"{feb}-02-{last}", "not": [f"{feb}-02-{57 - last}"]}, now)
    # days back across the start of a year
    now = at(year + 1, 1, r.randint(1, 6))
    n = now.day + r.randint(2, 20)
    then = now - td(days=n)
    return f"What was the date {n} days ago?", {"type": "date", "want": _date(then), "not": [_date(then.replace(year=now.year))]}, now


def _now(r):
    """A date and time for a message of the other kinds: a day in 2026 or 2027, between 08:00 and 18:55."""
    day = datetime.date(2026, 1, 1) + datetime.timedelta(days=r.randint(0, 729))
    return datetime.datetime(day.year, day.month, day.day, r.randint(8, 18), r.choice(range(0, 60, 5)))


def make(seed):
    """The 40 messages of one sitting: [{id, kind, message, history, now, check}], in a mixed order."""
    out = []
    for kind in KINDS:
        order = list(range(EACH))
        random.Random(f"{seed}:{kind}:order").shuffle(order)  # which template each of the ten gets
        for j in range(EACH):
            r = random.Random(f"{seed}:{kind}:{j}")
            now = _now(r)
            if kind == "time":
                message, check, now = m_time(r, order[j])
                history = []
            else:
                message, history, check = {"route": m_route, "fact": m_fact, "earlier": m_earlier}[kind](r, order[j])
            out.append({"kind": kind, "message": message, "history": history, "now": now.strftime("%Y-%m-%d %H:%M"), "check": check})
    random.Random(f"{seed}:mix").shuffle(out)
    for k, it in enumerate(out):
        it["id"] = f"t{seed}_{k:02d}"
    return [{"id": it.pop("id"), **it} for it in out]


# ---- checks ---------------------------------------------------------------------------------------------------------
def norm(text):
    """Lower case, every run of what is not a letter or a digit one space ('Maple-4417!' -> 'maple 4417')."""
    return " " + re.sub(r"[^0-9a-z]+", " ", str(text).lower()).strip() + " "


def _at(reply, want):
    """Where the words `want` are first named in the reply (after norm), or None."""
    w = norm(want).strip()
    k = norm(reply).find(f" {w} ") if w else -1
    return None if k < 0 else k


def _has(reply, want):
    return _at(reply, want) is not None


def _numbers_at(text):
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(text))
    return [(m.start(), float(m.group())) for m in re.finditer(r"-?\d+(?:\.\d+)?", t)]


def numbers(text):
    return [v for _, v in _numbers_at(text)]


def _dates_at(text):
    """Every date the text names, where: [(position, 'YYYY-MM-DD' or 'MM-DD' (a day and month with no year by it))]."""
    t, out = str(text).lower(), []
    for m in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        y, mo, d = m.groups()
        out.append((m.start(), f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"))
    mon = r"(" + "|".join(m[:3] + r"[a-z]*\.?" for m in MONTHS) + r")"
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + mon + r",?\s*(\d{4})?", t):
        d, mo, y = m.groups()
        out.append((m.start(), _dm(mo, d, y)))
    for m in re.finditer(mon + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b,?\s*(\d{4})?", t):
        mo, d, y = m.groups()
        out.append((m.start(), _dm(mo, d, y)))
    return sorted((k, x) for k, x in out if x)


def dates(text):
    """Every date the text names, as 'YYYY-MM-DD' or 'MM-DD' (a day and month with no year by it)."""
    return {x for _, x in _dates_at(text)}


def _dm(m, d, y):
    mo = next((k + 1 for k, name in enumerate(MONTHS) if m.startswith(name[:3])), 0)
    if not mo or not 1 <= int(d) <= 31:
        return ""
    return f"{int(y):04d}-{mo:02d}-{int(d):02d}" if y else f"{mo:02d}-{int(d):02d}"


def _clocks_at(text):
    """Every time of day the text names, where: [(position, 'HH:MM')] (3:55 pm, 15:55, 15.55 and 3 pm are all read)."""
    t, out = str(text).lower(), []
    for m in re.finditer(r"\b(\d{1,2})[:.](\d{2})\s*((?:a\.?m\.?|p\.?m\.?)(?![a-z]))?", t):
        out.append((m.start(), _clock(int(m.group(1)), int(m.group(2)), m.group(3))))
    for m in re.finditer(r"\b(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)(?![a-z])", t):
        out.append((m.start(), _clock(int(m.group(1)), 0, m.group(2))))
    return sorted((k, x) for k, x in out if x)


def clocks(text):
    """Every time of day the text names, as 'HH:MM'."""
    return {x for _, x in _clocks_at(text)}


def _clock(h, m, ap):
    if ap:
        if not 1 <= h <= 12:
            return ""
        h = h % 12 + (12 if ap.startswith("p") else 0)
    return f"{h:02d}:{m:02d}" if h < 24 and m < 60 else ""


UNSURE = re.compile(r"\b(?:i|we)\s+(?:do\s*n[o']t|don't|cannot|can't|can not)\s+(?:know|remember|recall|tell)\b|\bi(?:'m| am) not sure\b", re.I)


def _first(spec, text):
    """Where the reply first names the answer and where it first names a near miss (spec 'not'), and the near misses
    it names at all; positions are None when not named."""
    t, want, near = spec["type"], spec["want"], spec.get("not", [])
    if t == "text":
        found = [_at(text, w) for g in want for w in g]
        named = [d for d in near if _has(text, d)]
        return min((k for k in found if k is not None), default=None), min((_at(text, d) for d in named), default=None), named
    if t == "number":
        at, same = _numbers_at(text), lambda v, w: abs(v - w) < 1e-6
    elif t == "date":
        at, same = _dates_at(text), lambda v, w: v == w or v == w[5:]
    elif t == "clock":
        at, same = _clocks_at(text), lambda v, w: v == w
    else:
        raise ValueError(f"no near misses for a check of type {t!r}")
    first = lambda w: next((k for k, v in at if same(v, w)), None)  # noqa: E731
    named = [d for d in near if first(d) is not None]
    return first(want), min((first(d) for d in named), default=None), named


def check(spec, text, way=None):
    """(right, why) for one reply (text) and the route talk.py took (way) against a check spec."""
    t = spec["type"]
    if t == "route":
        return way == spec["want"], f"wants {spec['want']}; took {way}"
    if UNSURE.search(str(text)):  # 'I don't remember your name. I'm Priya' (t17, seed 1) names the name and is still wrong
        return False, "the reply says it does not know or remember"
    if t == "all":
        got = [check(s, text) for s in spec["of"]]
        return all(ok for ok, _ in got), "; ".join(why for _, why in got)
    ok, why = _plain(spec, text)
    if ok and spec.get("never"):
        said = [w for w in spec["never"] if _has(text, w)]
        if said:
            ok, why = False, why + f"; names {said}, which it must not"
    if ok and spec.get("not"):
        at, miss, named = _first(spec, text)
        if miss is not None and (at is None or miss < at):
            ok, why = False, why + f"; names the near miss {named} first"
    return ok, why


def _plain(spec, text):
    """(right, why) for the answer itself, near misses aside."""
    t = spec["type"]
    if t == "text":
        missing = [g for g in spec["want"] if not any(_has(text, w) for w in g)]
        return not missing, f"wants {' and '.join(' or '.join(g) for g in spec['want'])}" + (f"; missing {missing}" if missing else "")
    if t == "number":
        got = numbers(text)
        return any(abs(g - spec["want"]) < 1e-6 for g in got), f"wants {spec['want']}; the reply's numbers: {got[:8]}"
    if t == "date":
        got = dates(text)
        return spec["want"] in got or spec["want"][5:] in got, f"wants {spec['want']}; the reply's dates: {sorted(got)[:6]}"
    if t == "weekday":
        said = {d for d in WEEKDAYS if _has(text, d)}
        ok = spec["want"] in said and said <= {spec["want"], *spec.get("allow", [])}
        return ok, f"wants {spec['want']}; the reply names {sorted(said)}"
    if t == "clock":
        got = clocks(text)
        return spec["want"] in got, f"wants {spec['want']}; the reply's times: {sorted(got)[:6]}"
    raise ValueError(f"no check of type {t!r}")


# ---- a sitting ------------------------------------------------------------------------------------------------------
class Broke(Exception):
    """A message that raised in the process it was sat in: its error, as "Type: what it said"."""


def _within(fn, seconds):
    """fn()'s value; with `seconds`, fn runs in a forked process of its own group, ended with everything it started
    (the programs the hive runs) when the time is up: TimeoutError then, Broke when it raised."""
    if seconds is None:
        return fn()
    import multiprocessing
    import signal
    ctx = multiprocessing.get_context("fork")
    rx, tx = ctx.Pipe(duplex=False)

    def child():
        os.setpgrp()
        try:
            tx.send(("ok", fn()))
        except BaseException as e:  # noqa: BLE001 - whatever broke is told to the sitting
            tx.send(("err", f"{type(e).__name__}: {e}"))
    p = ctx.Process(target=child, daemon=True)
    p.start()
    tx.close()
    got = None
    try:
        if rx.poll(max(0.0, seconds)):
            got = rx.recv()
    except (EOFError, OSError):
        got = ("err", f"the message's process ended with code {p.exitcode}")
    finally:
        if got is None or p.is_alive():
            for kill in (lambda: os.killpg(p.pid, signal.SIGKILL), p.kill):
                try:
                    kill()
                except OSError:
                    pass
        p.join(10)
        rx.close()
    if got is None:
        raise TimeoutError(f"over {seconds:.0f} s")
    if got[0] == "err":
        raise Broke(got[1])
    return got[1]


def sit(seed, who="body", only=(), log=print, run_dir=None, minutes=None, per=None):
    """Every message through team/talk.py: route items through talk.route (the decision reply makes, nothing
    answered), the rest through talk.reply with the conversation and the exam's date and time.
    who: 'body' (the body on this machine) or a member name ('t17'). minutes: the whole sitting's budget; per: the
    most seconds one message may take (see the top of this file). Returns the result (see score())."""
    from team import talk
    base = (None if who == "body" else who) or talk.speaker()
    if not base:
        raise RuntimeError("the hive's body is not on this machine")
    home = Path(run_dir or ROOT / "runs" / "talk_exam" / f"{seed}_{time.strftime('%Y%m%d-%H%M%S')}")
    rows, t00 = [], time.time()
    end = t00 + 60 * float(minutes) if minutes is not None else None
    for it in make(seed):
        if only and it["kind"] not in only:
            continue
        t0 = time.time()
        caps = [c for c in (per, end - t0 if end is not None else None) if c is not None]
        cap = min(caps) if caps else None

        def one(it=it):
            if it["kind"] == "route":
                return talk.route(base, it["message"], it["history"])[0], ""
            out = talk.reply(it["message"], it["history"], run_dir=home / it["id"], base=base,
                             now=datetime.datetime.strptime(it["now"], "%Y-%m-%d %H:%M"))
            return ("work" if out["worked"] else "talk"), out["text"]
        try:
            if cap is not None and cap <= 0:
                raise TimeoutError("the sitting's time was up before this message")
            way, text = _within(one, cap)
            ok, why = check(it["check"], text, way)
        except TimeoutError as e:  # over its cap, or past the budget: failed for time, the sitting goes on (or ends)
            way, text, ok, why = None, "", False, f"time: {e}"
        except Broke as e:
            way, text, ok, why = None, "", False, f"broke: {e}"
        except Exception as e:  # noqa: BLE001 - a message that broke is a message failed, the sitting goes on
            way, text, ok, why = None, "", False, f"broke: {type(e).__name__}: {e}"
        rows.append({"id": it["id"], "kind": it["kind"], "message": it["message"], "turns": len(it["history"]) // 2,
                     "now": it["now"], "route": way, "reply": text, "ok": bool(ok), "why": why, "seconds": round(time.time() - t0, 1)})
        log(f"{it['id']} {it['kind']:<7} {'RIGHT' if ok else 'wrong'} [{way}] {it['message'][:60]!r} -> {text[:80]!r} ({why})")
    res = score(seed, who, base, rows, round((time.time() - t00) / 60, 1))
    if minutes is not None or per is not None:
        res.update(budget_minutes=minutes, per_seconds=per)
    return res


def score(seed, who, base, rows, minutes=0.0):
    right = sum(r["ok"] for r in rows)
    kinds = {k: [sum(r["ok"] for r in rows if r["kind"] == k), sum(r["kind"] == k for r in rows)] for k in KINDS}
    return {"seed": seed, "who": who, "member": base, "when": time.strftime("%Y-%m-%d %H:%M"), "minutes": minutes,
            "right": right, "of": len(rows), "score": right, "out_of_10": round(10 * right / len(rows), 1) if rows else 0.0,
            "kinds": kinds, "timed_out": sum(str(r.get("why", "")).startswith("time") for r in rows), "items": rows}


def main(argv):
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    cmd = argv[0] if argv else ""
    seed = int(opt("--seed", (datetime.date.today() - datetime.date(2026, 1, 1)).days))
    if cmd == "show":
        for it in make(seed):
            turns = f" (after {len(it['history']) // 2} turns)" if it["history"] else ""
            print(f"{it['id']} {it['kind']:<7} [{it['now']}]{turns} {it['message']}\n    check: {json.dumps(it['check'])}")
        return 0
    if cmd == "sit":
        if opt("--port"):  # a server of this exam's own, beside one another process is using
            from team import ternary
            p = int(opt("--port"))
            ternary.port = lambda member: p
        only = tuple(k for k in (opt("--only", "") or "").split(",") if k)
        if opt("--who", "body") != "body":  # what goes to work is worked by the same model that talks
            os.environ.setdefault("HIVE_MEMBERS", opt("--who"))
        num = lambda k: float(opt(k)) if opt(k) is not None else None  # noqa: E731
        path = Path(opt("--out") or OUT / f"{seed}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            res = sit(seed, opt("--who", "body"), only, minutes=num("--minutes"), per=num("--per"))
        except Exception as e:  # noqa: BLE001 - a sitting that could not start still says so in its json
            res = {"seed": seed, "who": opt("--who", "body"), "when": time.strftime("%Y-%m-%d %H:%M"), "minutes": 0.0,
                   "right": 0, "of": 0, "out_of_10": None, "kinds": {}, "error": f"{type(e).__name__}: {e}", "items": []}
        path.write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({k: res[k] for k in ("seed", "who", "right", "of", "out_of_10", "kinds", "minutes", "timed_out", "error") if k in res}))
        return 1 if res.get("error") else 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
