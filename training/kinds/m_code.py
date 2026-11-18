"""The kind m_code: a small program to write and run (code).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training.kinds._common import _fill, says

KIND = "m_code"
FAMILY = "code"
HARD = False
ORDER = 60
LESSON_ORDER = 50


def m_code(r):
    word = r.choice(["imagination", "encyclopedia", "watermelon", "architecture", "photosynthesis", "refrigerator", "university"])
    n = r.randrange(10_000, 9_999_999)
    sent = r.choice(["the quick brown fox jumps over the lazy dog", "a journey of a thousand miles begins with a single step",
                     "all that glitters is not gold", "to be or not to be that is the question"])
    kind = r.choice(["vowels", "digits", "long", "evens"])
    if kind == "vowels":
        return ("code", "write and run a program", f"Write a Python function that counts the vowels in a word and tell me how many vowels "
                f"'{word}' has.", says(sum(c in "aeiou" for c in word), 0.1))
    if kind == "digits":
        return ("code", "write and run a program", f"Write a Python function that adds up the digits of a number and tell me the result for {n}.",
                says(sum(map(int, str(n))), 0.1))
    if kind == "long":
        return ("code", "write and run a program", "Write a Python function that counts the words with more than four letters in a sentence and "
                f"tell me the count for '{sent}'.", says(sum(len(w) > 4 for w in sent.split()), 0.1))
    k = r.randrange(30, 90)
    return ("code", "write and run a program", f"Write Python code that adds up all the even numbers from 1 to {k} and tell me the total.",
            says(sum(i for i in range(1, k + 1) if i % 2 == 0), 0.1))


def code(task):
    m = re.search(r"how many vowels '(\w+)' has", task)
    if m:
        return _fill('''def vowels(word):
    return sum(c in "aeiou" for c in word.lower())


print(vowels(__W__))
''', w=m.group(1))
    m = re.search(r"adds up the digits of a number and tell me the result for (\d+)", task)
    if m:
        return f"def digit_sum(n):\n    return sum(int(c) for c in str(n))\n\n\nprint(digit_sum({int(m.group(1))}))\n"
    m = re.search(r"more than four letters in a sentence and tell me the count for '(.+?)'", task)
    if m:
        return _fill('''def long_words(sentence):
    return sum(len(w) > 4 for w in sentence.split())


print(long_words(__S__))
''', s=m.group(1))
    m = re.search(r"adds up all the even numbers from 1 to (\d+)", task)
    if m:
        return f"print(sum(i for i in range(1, {int(m.group(1))} + 1) if i % 2 == 0))\n"
    return None


make = m_code
lesson = code
