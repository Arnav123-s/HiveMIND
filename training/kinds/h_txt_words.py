"""The kind h_txt_words: the most frequent words of a text, stopwords left out, ties broken by a rule (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill

KIND = "h_txt_words"
FAMILY = "hard: text"
HARD = True
ORDER = 420

WORDS = ["river", "garden", "lamp", "harbour", "winter", "bread", "letter", "window", "market", "music", "stone", "train", "cloud", "paper"]
VERBS = ["saw", "kept", "found", "painted", "carried", "lost", "liked"]
STOP = ["the", "a", "and", "of", "to", "in", "we", "it", "was", "on", "by", "with"]


def h_txt_words(r):
    nouns = r.sample(WORDS, 8)
    weight = [r.randrange(1, 6) for _ in nouns]
    sentences = []
    for _ in range(r.randrange(9, 14)):
        a, b = r.choices(nouns, weight, k=2)
        s = r.choice(["The {a} and the {b} {v} it.", "We {v} a {a} by the {b}!", "It was the {a} of the {b}.",
                      "{A}, {b}, and {a} again?", "On the {a} we {v} the {b}.", "The {b} was in the {a}; it {v} us."])
        sentences.append(s.format(a=a, b=b, A=a.upper() if r.random() < 0.3 else a.capitalize(), v=r.choice(VERBS)))
    text = " ".join(s[0].upper() + s[1:] for s in sentences)
    stop = sorted(set(r.sample(STOP, 8)) | {"the", "a"})
    k = r.randrange(3, 6)
    count = {}
    for w in re.findall(r"[a-z]+", text.lower()):
        if w not in stop:
            count[w] = count.get(w, 0) + 1
    want = sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))[:k]

    def check(run, report):
        got = [(m.group(1).lower(), int(m.group(2))) for ln in B._body(report).splitlines()
               if (m := re.match(r"\W*([A-Za-z]+)\W*:\s*(\d+)\s*$", ln.strip()))]
        ok = got == want
        return ok, f"wants {want}; got {got[:8]}"
    return ("hard: text", "the most frequent words of a text", "Here is a text:\n" + text + "\nStopwords: " + ", ".join(stop)
            + f".\nCount the words of the text (a word is a run of letters; capital and small letters are the same word), leaving "
            f"out the stopwords. Give the {k} most frequent, the most frequent first; words with the same count go in alphabetical "
            "order. One per line, written 'word: count', and nothing else.", check)


def words(task):
    m = re.search(r"Here is a text:\n(.*?)\nStopwords: (.*?)\.\nCount the words.*?Give the (\d+) most frequent", task, re.S)
    if not m:
        return None
    return _fill('''import re
s, c = __STOP__.split(", "), {}
for w in re.findall("[a-z]+", __TEXT__.lower()):
    if w not in s:
        c[w] = c.get(w, 0) + 1
for w in sorted(c, key=lambda w: (-c[w], w))[:__K__]:
    print(f"{w}: {c[w]}")
''', text=m.group(1), stop=m.group(2), k=int(m.group(3)))


make = h_txt_words
lesson = words
