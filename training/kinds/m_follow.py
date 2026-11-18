"""The kind m_follow: a form followed to the letter (a list, one word, capitals, JSON, two sentences) (instructions).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import NAMES, _fill, _json_in

KIND = "m_follow"
FAMILY = "instructions"
HARD = False
ORDER = 120
LESSON_ORDER = 70
COPIES = 2


LISTS = {"fruits": None, "European capital cities": None, "programming languages": None, "colours": None, "musical instruments": None}


OPPOSITES = {"hot": "cold", "early": "late", "empty": "full", "heavy": "light", "ancient": "modern", "generous": ("stingy", "selfish", "mean", "greedy")}


def m_follow(r):
    kind = r.choice(["list", "one word", "capitals", "json", "sentences"])
    if kind == "list":
        n, what = r.randrange(3, 7), r.choice(sorted(LISTS))

        def check(run, report):
            items = re.findall(r"^\s*\d+[.)]\s+\S", B._body(report), re.M)
            return len(items) == n, f"{len(items)} numbered items, {n} asked"
        return "instructions", "follow a form to the letter", f"Give me exactly {n} {what} as a numbered list and nothing else.", check
    if kind == "one word":
        word = r.choice(sorted(OPPOSITES))
        want = OPPOSITES[word] if isinstance(OPPOSITES[word], tuple) else (OPPOSITES[word],)

        def check(run, report):
            body = B._body(report).strip().strip(".!\"'*` ").lower()
            return body in want, f"the answer is {body[:40]!r}; one word of {want} was asked"
        return "instructions", "follow a form to the letter", f"Answer with one word and nothing else: what is the opposite of '{word}'?", check
    if kind == "capitals":
        word = r.choice(["harbour", "lantern", "meadow", "compass", "orchard", "thunder"])

        def check(run, report):
            body = B._body(report).strip().strip(".!\"'*` ")
            return body == word.upper(), f"the answer is {body[:40]!r}; {word.upper()!r} was asked"
        return "instructions", "follow a form to the letter", f"Write the word '{word}' in capital letters and nothing else.", check
    if kind == "json":
        name, age, city = r.choice(NAMES), r.randrange(19, 80), r.choice(["Lisbon", "Oslo", "Kyoto", "Lima", "Cairo", "Perth"])

        def check(run, report):
            got = _json_in(B._body(report))
            ok = isinstance(got, dict) and got.get("name") == name and str(got.get("age")) == str(age) and got.get("city") == city and len(got) == 3
            return ok, f"the answer's JSON: {str(got)[:80]}"
        return ("instructions", "follow a form to the letter", f"Give me a JSON object with exactly the keys name, age and city for {name}, who is "
                f"{age} years old and lives in {city}. Only the JSON, nothing else.", check)
    topic, word = r.choice([("why the sky is blue", "scatter"), ("why the sea is salty", "salt"), ("why leaves fall in autumn", ("light", "cold", "chlorophyll", "water")),
                            ("why the moon has phases", ("sun", "orbit"))])
    words = word if isinstance(word, tuple) else (word,)

    def check(run, report):
        body = B._body(report)
        n = len(B._sentences(body))
        return n == 2 and any(w in body.lower() for w in words), f"{n} sentences (two asked); speaks of {words}: {any(w in body.lower() for w in words)}"
    return "instructions", "follow a form to the letter", f"Explain {topic} in exactly two sentences.", check


LIST_ITEMS = {"fruits": ["apple", "banana", "orange", "mango", "pear", "cherry", "grape"],
              "European capital cities": ["Paris", "Berlin", "Madrid", "Rome", "Lisbon", "Vienna", "Oslo"],
              "programming languages": ["Python", "Java", "C", "Rust", "Go", "JavaScript", "Ruby"],
              "colours": ["red", "blue", "green", "yellow", "purple", "orange", "black"],
              "musical instruments": ["piano", "violin", "guitar", "flute", "drum", "trumpet", "cello"]}


TWO_SENTENCES = {
    "why the sky is blue": "Sunlight is scattered by the molecules of the air, and blue light is scattered much more than red light because its waves are shorter. So blue light reaches our eyes from every part of the sky.",
    "why the sea is salty": "Rain wears down rocks on land, and rivers carry the salt from them into the sea. When sea water evaporates the salt stays behind, so over millions of years the sea has become salty.",
    "why leaves fall in autumn": "In autumn the days grow shorter and colder, so trees stop making chlorophyll and their leaves lose their green colour. The tree then seals each leaf off to save water through the winter, and the leaf falls.",
    "why the moon has phases": "The moon does not shine by itself but reflects light from the sun, so only the half that faces the sun is lit. As the moon travels along its orbit around the earth, we see more or less of that lit half, and these are its phases.",
}


def form(task):
    m = re.search(r"Give me exactly (\d+) (.+?) as a numbered list and nothing else", task)
    if m and m.group(2) in LIST_ITEMS:
        return _fill('''# well known, and nothing to compute: written into the program
items = __ITEMS__
for i, item in enumerate(items[:__N__], 1):
    print(f"{i}. {item}")
''', items=LIST_ITEMS[m.group(2)], n=int(m.group(1)))
    m = re.search(r"what is the opposite of '(\w+)'\?", task)
    if m and m.group(1) in OPPOSITES:
        word = OPPOSITES[m.group(1)]
        return _fill("# one word and nothing else\nprint(__W__)\n", w=word[0] if isinstance(word, tuple) else word)
    m = re.search(r"Write the word '(\w+)' in capital letters and nothing else", task)
    if m:
        return _fill("print(__W__.upper())\n", w=m.group(1))
    m = re.search(r"keys name, age and city for (\w+), who is (\d+) years old and lives in (\w+)\. Only the JSON", task)
    if m:
        return _fill('''import json

print(json.dumps({"name": __NAME__, "age": __AGE__, "city": __CITY__}))
''', name=m.group(1), age=int(m.group(2)), city=m.group(3))
    m = re.search(r"Explain (.+?) in exactly two sentences", task)
    if m and m.group(1) in TWO_SENTENCES:
        return _fill("# something only I can write: the text is put in a string and printed\nprint(__T__)\n", t=TWO_SENTENCES[m.group(1)])
    return None


make = m_follow
lesson = form
