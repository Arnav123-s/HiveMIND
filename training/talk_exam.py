"""The talk exam: 40 messages, made by code and checked by code, sat through the hive's one door (team/talk.py).

    python training/talk_exam.py show --seed N              the messages of a sitting and what each must get right
    python training/talk_exam.py sit --seed N [--who t17|body] [--out FILE.json] [--only route,fact,...] [--port P]
                                                            sit it: every message goes to team.talk.reply

Four kinds, ten messages each, every one drawn from a template with new values (the same seed, the same exam):

  route    talk or work: a greeting, an explanation, a poem must be answered at once; a sum, data to go through, a
           version or a web page must go to the programs. The check is the way team/talk.py took (talk.route, the
           very decision reply() makes); nothing is answered for these.
  fact     a fact given in the message (or the turn just before) must come back right in the reply: a gate, a code,
           an age, a room.
  earlier  a conversation of 1 to 3 earlier turns (the hive's own turns written out here): the last message asks
           for something said 1 to 3 turns back, by the user or by the hive.
  time     the hive is told the date and time (reply's `now`), and the reply must use it right: the weekday today,
           the date in 9 days, the time in 95 minutes.

Every check is code (numbers, dates, weekdays and times read out of the reply; words matched after lower-casing and
dropping punctuation); no model judges. The score is out of 40, and out of 10 for the goal's table (bar: 8 of 10).
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
COLOURS = ["teal", "maroon", "amber", "lilac", "olive", "turquoise", "crimson", "indigo"]
BOOKS = ["The Silent Orchard", "A River of Glass", "Northern Lanterns", "The Clockmaker's Garden", "Paper Comets", "Salt and Cedar"]
JOBS = ["nurse", "carpenter", "librarian", "pilot", "baker", "geologist", "translator", "plumber"]
THINGS = ["bread", "batteries", "lemons", "stamps", "rice", "candles", "soap", "tea", "glue", "onions", "envelopes", "honey"]
FILLERS = [("What's a good way to stay focused when I work?", "Short breaks help: work for a while, then rest a little, and keep your phone in another room."),
           ("Tell me a fun fact.", "Octopuses have three hearts."),
           ("How do I keep basil alive on a windowsill?", "Give it plenty of light, water it when the soil feels dry, and pinch off the flowers."),
           ("Any tips for sleeping better?", "Keep the same bedtime, avoid screens late in the evening and keep the room cool and dark."),
           ("Why is the sea salty?", "Rivers carry minerals from rocks into the sea, and when the water evaporates the salt stays behind.")]


def _code(r, letters=2, digits=4):
    return "".join(r.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(letters)) + "".join(r.choice("0123456789") for _ in range(digits))


def _turns(pairs):
    return [m for u, a in pairs for m in ({"role": "user", "content": u}, {"role": "assistant", "content": a})]


# ---- the four kinds -----------------------------------------------------------------------------------------------
def m_route(r, i):
    """Half talk, half work: (message, history, check)."""
    if i % 2 == 0:
        country = r.choice(sorted(CAPITALS))
        msg = r.choice([f"what is the capital of {country}?",
                        f"why does {r.choice(['ice float on water', 'the moon have phases', 'bread rise', 'a rainbow form after rain', 'the sky turn red at sunset'])}?",
                        f"write a short poem about {r.choice(['autumn leaves', 'a lighthouse', 'morning coffee', 'a sleepy cat', 'the first snow'])}",
                        f"can you explain what {r.choice(['photosynthesis', 'inflation', 'a prime number', 'democracy', 'gravity'])} means?",
                        f"how do I say '{r.choice(['good night', 'thank you very much', 'where is the station'])}' in {r.choice(['Spanish', 'French', 'German', 'Italian'])}?",
                        f"any advice for {r.choice(['a first job interview', 'learning to cook', 'running my first 5k', 'moving to a new city'])}?",
                        f"good morning {r.choice(NAMES)}-bot! how are you today?",
                        f"what's the difference between a {r.choice(['frog and a toad', 'cyclone and a tornado', 'virus and a bacterium', 'lake and a pond'])}?"])
        return msg, [], {"type": "route", "want": "talk"}
    a, b, c, d = (r.randint(40, 1400) for _ in range(4))
    msg = r.choice([f"what is {r.choice([7.5, 12, 15, 17.5, 22, 35])}% of {r.randint(120, 9800)}?",
                    f"here are my monthly costs: rent {a}, food {b}, travel {c}, phone {d}. which costs the most, and what is the total?",
                    f"which is the newest version of {r.choice(['numpy', 'pandas', 'requests', 'flask', 'scipy'])} on PyPI?",
                    f"write a python function that {r.choice(['reverses the words in a sentence', 'checks if a number is prime', 'counts the vowels in a text'])} and run it on an example to show it works",
                    f"read https://{r.choice(['example.com', 'www.python.org', 'en.wikipedia.org/wiki/Ternary_numeral_system'])} and tell me the title of the page",
                    f"sort these numbers and tell me the median: {', '.join(str(r.randint(1, 500)) for _ in range(r.randint(7, 11)))}",
                    f"how many days are there from {r.randint(1, 28)} {r.choice(MONTHS).title()} 2027 to {r.randint(1, 28)} {r.choice(MONTHS).title()} 2028?",
                    f"multiply {r.randint(1000, 9999)} by {r.randint(100, 999)} for me"])
    return msg, [], {"type": "route", "want": "work"}


def m_fact(r, i):
    n1, n2, n3 = r.sample(NAMES, 3)
    a1, a2, a3 = r.sample(range(19, 78), 3)
    gate, flight = f"{r.choice('ABCDEFG')}{r.randint(2, 48)}", _code(r, 2, 4)
    pw = f"{r.choice(['maple', 'otter', 'violet', 'harbor', 'comet', 'pebble'])}{r.randint(1000, 9999)}"
    room, order, spot, level = r.randint(101, 999), _code(r, 3, 5), r.randint(10, 380), r.choice(["2", "3", "4", "5", "B1", "B2"])
    c1, c2 = r.sample(CITIES, 2)
    day, hh, mm = r.choice(WEEKDAYS).title(), r.randint(8, 17), r.choice([0, 15, 30, 45])
    made = [
        (f"My flight {flight} leaves from gate {gate}. Which gate does my flight leave from?", [], {"type": "text", "want": [[gate]]}),
        (f"The wifi password here is {pw}. Can you remind me what the wifi password is?", [], {"type": "text", "want": [[pw]]}),
        (f"{n1} is {a1} years old, {n2} is {a2} and {n3} is {a3}. How old is {n2}?", [], {"type": "number", "want": a2}),
        (f"My order number is {order}. What is my order number?", [], {"type": "text", "want": [[order]]}),
        (f"I parked on level {level}, spot {spot}. Which spot did I park in?", [], {"type": "number", "want": spot}),
        (f"The meeting with {n1} is in room {room}, the one with {n2} is online. Which room is the meeting with {n1} in?", [], {"type": "number", "want": room}),
        (f"My friend {n1} lives in {c1} and my colleague {n2} lives in {c2}. Where does my colleague live?", [], {"type": "text", "want": [[c2]]}),
        (f"Here is my note: 'Dentist on {day} at {hh}:{mm:02d}.' When is my dentist appointment?", [],
         {"type": "text", "want": [[day], [f"{hh}:{mm:02d}", f"{(hh - 1) % 12 + 1}:{mm:02d}" if mm else f"{(hh - 1) % 12 + 1} {'am' if hh < 12 else 'pm'}"]]}),
        (f"What is my locker number?", _turns([(f"Please keep this for me: my locker number is {room}.", f"Noted: your locker number is {room}.")]),
         {"type": "number", "want": room}),
        (f"Which train platform did I say?", _turns([(f"My train to {c1} leaves from platform {spot % 19 + 1}.", "Thanks, I'll keep that in mind. Have a good trip!")]),
         {"type": "number", "want": spot % 19 + 1}),
    ]
    return made[i % len(made)]


def m_earlier(r, i):
    """A fact said 1 to 3 turns back (by the user or by the hive), then filler turns, then the question."""
    name, city, pet, colour = r.choice(NAMES), r.choice(CITIES), r.choice(PETS), r.choice(COLOURS)
    book, job, lucky = r.choice(BOOKS), r.choice(JOBS), r.randint(11, 97)
    shop = r.sample(THINGS, 3)
    made = [
        ((f"Hi, I'm {name}.", f"Hello {name}, nice to meet you! How can I help?"), "Do you remember my name?", {"type": "text", "want": [[name]]}),
        ((f"I'm moving to {city} next month.", "How exciting! A new city is a big step."), "Which city did I say I'm moving to?", {"type": "text", "want": [[city]]}),
        ((f"My dog is called {pet}.", f"{pet} is a lovely name for a dog!"), "What is my dog's name?", {"type": "text", "want": [[pet]]}),
        (("Suggest a name for my new cat.", f"How about {pet}?"), "What name did you suggest for my cat?", {"type": "text", "want": [[pet]]}),
        ((f"My favourite colour is {colour}.", "Good choice, it is a lovely colour."), "What's my favourite colour?", {"type": "text", "want": [[colour]]}),
        ((f"I'm reading '{book}' at the moment.", "Enjoy it! Reading every day is a good habit."), "Which book did I say I'm reading?", {"type": "text", "want": [[book]]}),
        ((f"I work as a {job}.", "That sounds like interesting work."), "What did I tell you my job is?", {"type": "text", "want": [[job]]}),
        ((f"My lucky number is {lucky}.", "A fine lucky number!"), "What is my lucky number?", {"type": "number", "want": lucky}),
        ((f"I need to buy {shop[0]}, {shop[1]} and {shop[2]}.", "Got it, that's your shopping list."), "What was the second thing on my shopping list?", {"type": "text", "want": [[shop[1]]]}),
        (("Which city should I visit in spring?", f"{city} is lovely in spring: mild weather and few crowds."), "Which city did you recommend?", {"type": "text", "want": [[city]]}),
    ]
    said, ask, check = made[i % len(made)]
    back = r.randint(1, 3)  # the fact is this many turns before the question
    return ask, _turns([said] + r.sample(FILLERS, back - 1)), check


def _date(d):
    return d.strftime("%Y-%m-%d")


def m_time(r, i, now):
    n, mins, hrs, k = r.randint(2, 12), r.choice([20, 35, 45, 50, 95, 110, 140]), r.randint(2, 5), r.randint(2, 9)
    today = WEEKDAYS[now.weekday()]
    later, ago = now + datetime.timedelta(days=n), now - datetime.timedelta(days=n)
    month = MONTHS[(now.month - 1 + k) % 12]
    made = [
        ("What day of the week is it today?", {"type": "weekday", "want": today, "allow": []}),
        ("What is today's date?", {"type": "date", "want": _date(now)}),
        (f"What day of the week will it be in {n} days?", {"type": "weekday", "want": WEEKDAYS[later.weekday()], "allow": [today]}),
        (f"What will the date be {n} days from now?", {"type": "date", "want": _date(later)}),
        (f"What was the date {n} days ago?", {"type": "date", "want": _date(ago)}),
        (f"What time will it be in {mins} minutes?", {"type": "clock", "want": (now + datetime.timedelta(minutes=mins)).strftime("%H:%M")}),
        (f"What time was it {hrs} hours ago?", {"type": "clock", "want": (now - datetime.timedelta(hours=hrs)).strftime("%H:%M")}),
        (f"Which month will it be in {k} months?", {"type": "text", "want": [[month]]}),
        ("What day was it yesterday?", {"type": "weekday", "want": WEEKDAYS[(now.weekday() - 1) % 7], "allow": [today]}),
        ("What year is it?", {"type": "number", "want": now.year}),
    ]
    return made[i % len(made)]


def _now(r):
    """A date and time for one message: a day in 2026 or 2027, between 08:00 and 18:55 (no reply crosses midnight)."""
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
                message, check = m_time(r, order[j], now)
                history = []
            else:
                message, history, check = {"route": m_route, "fact": m_fact, "earlier": m_earlier}[kind](r, order[j] if kind != "route" else j)
            out.append({"kind": kind, "message": message, "history": history, "now": now.strftime("%Y-%m-%d %H:%M"), "check": check})
    random.Random(f"{seed}:mix").shuffle(out)
    for k, it in enumerate(out):
        it["id"] = f"t{seed}_{k:02d}"
    return [{"id": it.pop("id"), **it} for it in out]


# ---- checks ---------------------------------------------------------------------------------------------------------
def norm(text):
    """Lower case, every run of what is not a letter or a digit one space ('Maple-4417!' -> 'maple 4417')."""
    return " " + re.sub(r"[^0-9a-z]+", " ", str(text).lower()).strip() + " "


def _has(reply, want):
    w = norm(want).strip()
    return bool(w) and f" {w} " in norm(reply)


def numbers(text):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(text)))]


def dates(text):
    """Every date the text names, as 'YYYY-MM-DD' or 'MM-DD' (a day and month with no year by it)."""
    t, out = str(text).lower(), set()
    for y, m, d in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        out.add(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    mon = r"(" + "|".join(m[:3] + r"[a-z]*\.?" for m in MONTHS) + r")"
    for d, m, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + mon + r",?\s*(\d{4})?", t):
        out.add(_dm(m, d, y))
    for m, d, y in re.findall(mon + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b,?\s*(\d{4})?", t):
        out.add(_dm(m, d, y))
    return {x for x in out if x}


def _dm(m, d, y):
    mo = next((k + 1 for k, name in enumerate(MONTHS) if m.startswith(name[:3])), 0)
    if not mo or not 1 <= int(d) <= 31:
        return ""
    return f"{int(y):04d}-{mo:02d}-{int(d):02d}" if y else f"{mo:02d}-{int(d):02d}"


def clocks(text):
    """Every time of day the text names, as 'HH:MM' (3:55 pm, 15:55, 15.55 and 3 pm are all read)."""
    t, out = str(text).lower(), set()
    for h, m, ap in re.findall(r"\b(\d{1,2})[:.](\d{2})\s*((?:a\.?m\.?|p\.?m\.?)(?![a-z]))?", t):
        out.add(_hm(int(h), int(m), ap))
    for h, ap in re.findall(r"\b(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)(?![a-z])", t):
        out.add(_hm(int(h), 0, ap))
    return {x for x in out if x}


def _hm(h, m, ap):
    if ap:
        if not 1 <= h <= 12:
            return ""
        h = h % 12 + (12 if ap.startswith("p") else 0)
    return f"{h:02d}:{m:02d}" if h < 24 and m < 60 else ""


def check(spec, text, way=None):
    """(right, why) for one reply (text) and the route talk.py took (way) against a check spec."""
    t = spec["type"]
    if t == "route":
        return way == spec["want"], f"wants {spec['want']}; took {way}"
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
def sit(seed, who="body", only=(), log=print, run_dir=None):
    """Every message through team/talk.py: route items through talk.route (the decision reply makes, nothing
    answered), the rest through talk.reply with the conversation and the exam's date and time.
    who: 'body' (the body on this machine) or a member name ('t17'). Returns the result (see score())."""
    from team import talk
    base = (None if who == "body" else who) or talk.speaker()
    if not base:
        raise RuntimeError("the hive's body is not on this machine")
    home = Path(run_dir or ROOT / "runs" / "talk_exam" / f"{seed}_{time.strftime('%Y%m%d-%H%M%S')}")
    rows, t00 = [], time.time()
    for it in make(seed):
        if only and it["kind"] not in only:
            continue
        t0 = time.time()
        try:
            if it["kind"] == "route":
                way, text = talk.route(base, it["message"], it["history"])[0], ""
            else:
                out = talk.reply(it["message"], it["history"], run_dir=home / it["id"], base=base,
                                 now=datetime.datetime.strptime(it["now"], "%Y-%m-%d %H:%M"))
                way, text = ("work" if out["worked"] else "talk"), out["text"]
            ok, why = check(it["check"], text, way)
        except Exception as e:  # noqa: BLE001 - a message that broke is a message failed, the sitting goes on
            way, text, ok, why = None, "", False, f"broke: {type(e).__name__}: {e}"
        rows.append({"id": it["id"], "kind": it["kind"], "message": it["message"], "turns": len(it["history"]) // 2,
                     "now": it["now"], "route": way, "reply": text, "ok": bool(ok), "why": why, "seconds": round(time.time() - t0, 1)})
        log(f"{it['id']} {it['kind']:<7} {'RIGHT' if ok else 'wrong'} [{way}] {it['message'][:60]!r} -> {text[:80]!r} ({why})")
    return score(seed, who, base, rows, round((time.time() - t00) / 60, 1))


def score(seed, who, base, rows, minutes=0.0):
    right = sum(r["ok"] for r in rows)
    kinds = {k: [sum(r["ok"] for r in rows if r["kind"] == k), sum(r["kind"] == k for r in rows)] for k in KINDS}
    return {"seed": seed, "who": who, "member": base, "when": time.strftime("%Y-%m-%d %H:%M"), "minutes": minutes,
            "right": right, "of": len(rows), "score": right, "out_of_10": round(10 * right / len(rows), 1) if rows else 0.0,
            "kinds": kinds, "items": rows}


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
        res = sit(seed, opt("--who", "body"), only)
        path = Path(opt("--out") or OUT / f"{seed}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({k: res[k] for k in ("seed", "who", "right", "of", "out_of_10", "kinds", "minutes")}))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
