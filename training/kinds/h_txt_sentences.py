"""The kind h_txt_sentences: a text split into sentences (abbreviations and decimals do not end one), the longest
found by its words (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training.kinds._common import _fill, _line_says, every, HARD_NAMES as NAMES

KIND = "h_txt_sentences"
FAMILY = "hard: text"
HARD = True
GIVEN_FILE = True
ORDER = 460

ABBR = ["Dr.", "Mr.", "Ms.", "St.", "e.g.", "approx."]
PARTS = [["the", "museum", "on", "{abbr_st}", "Mark's", "Square", "opens", "at", "nine"],
         ["{abbr_dr}", "{name}", "measured", "{dec}", "litres", "of", "rain", "in", "one", "night"],
         ["bring", "warm", "things,", "{abbr_eg}", "a", "coat", "and", "boots"],
         ["what", "a", "day", "it", "was"],
         ["is", "the", "train", "to", "the", "coast", "late", "again"],
         ["{abbr_mr}", "{name}", "sold", "{abbr_ap}", "{dec}", "kilos", "of", "apples", "at", "the", "market", "today"],
         ["nobody", "came"],
         ["the", "bridge", "is", "closed", "until", "the", "end", "of", "May"],
         ["{abbr_ms}", "{name}", "paid", "{dec}", "dollars", "for", "a", "map", "of", "the", "old", "town"],
         ["we", "waited", "for", "an", "hour", "and", "then", "we", "walked", "home", "in", "the", "rain"]]
EXTRA = ["slowly", "quietly", "together", "again", "there"]


def h_txt_sentences(r):
    chosen = [list(p) for p in r.sample(PARTS, r.randrange(5, 9))]
    for s in chosen:  # some sentences one or two words longer, so the longest is not always the same
        for _ in range(r.randrange(0, 3)):
            s.append(r.choice(EXTRA))
    counts = [len(s) for s in chosen]
    while counts.count(max(counts)) > 1:  # a tie has no single answer: the first of the longest gets one more word
        chosen[counts.index(max(counts))].append(r.choice(EXTRA))
        counts = [len(s) for s in chosen]
    values = {"abbr_st": "St.", "abbr_dr": "Dr.", "abbr_eg": "e.g.", "abbr_mr": "Mr.", "abbr_ap": "approx.", "abbr_ms": "Ms."}
    out = []
    for s in chosen:
        words = [w.format(name=r.choice(NAMES), dec=f"{r.randrange(1, 40)}.{r.randrange(1, 10)}", **values) for w in s]
        words[0] = words[0][0].upper() + words[0][1:]
        end = "?" if words[0] == "Is" else r.choice([".", ".", "!"])
        out.append(" ".join(words) + end)
    text = " ".join(out)
    longest = counts.index(max(counts)) + 1

    check = every(_line_says("sentences", len(chosen)), _line_says("longest", longest), _line_says("words", max(counts)))
    return ("hard: text", "a text split into sentences", "Here is a text:\n" + text + "\nSplit it into sentences. A sentence ends with "
            "'.', '!' or '?' followed by a space or by the end of the text, except that these abbreviations never end one: "
            + ", ".join(ABBR) + " (and a decimal point inside a number does not either). A word is anything between spaces. How many "
            "sentences are there, which one has the most words (counting from 1), and how many words does it have? Answer in three "
            "lines: 'sentences: ', 'longest: ', 'words: '.", check)


def sentences(task, copy=False):
    """The text is data the task gives: the runtime saves it as a file, so the program reads it from one (any name it
    opens and does not find is that file); copy: the text copied into the program instead (a task of several parts
    whose first block of data is another part's)."""
    m = re.search(r"Here is a text:\n(.*?)\nSplit it into sentences\..*?never end one: (.*?) \(and a decimal", task, re.S)
    if not m:
        return None
    return _fill('''a, n = __ABBR__.split(", "), [0]
for w in __TEXT__.split():
    n[-1] += 1
    if w[-1] in ".!?" and w not in a:
        n.append(0)
n = [x for x in n if x]
print("sentences:", len(n))
print("longest:", n.index(max(n)) + 1)
print("words:", max(n))
''', abbr=m.group(2)).replace("__TEXT__", repr(m.group(1)) if copy else 'open("text.txt").read()')


make = h_txt_sentences
lesson = sentences
