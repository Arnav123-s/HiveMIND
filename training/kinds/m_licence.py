"""The kind m_licence: the licence of a model on Hugging Face (live facts).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill

KIND = "m_licence"
FAMILY = "live facts"
HARD = False
ORDER = 90
LESSON_ORDER = 110
NETWORK = True


MODELS = ["google-bert/bert-base-uncased", "FacebookAI/roberta-base", "distilbert/distilbert-base-uncased", "openai-community/gpt2",
          "sentence-transformers/all-MiniLM-L6-v2", "google-t5/t5-small", "FacebookAI/xlm-roberta-base", "microsoft/deberta-v3-base"]


def m_licence(r):
    model = r.choice(MODELS)

    def check(run, report):
        lic = str((B._hf(model).get("cardData") or {}).get("license", "")).lower()
        words = re.findall(r"[a-z]+|\d+(?:\.\d+)?", lic)
        body = B._body(report).lower()
        return bool(words) and all(w in body for w in words), f"licence {lic} in the answer"
    return "live facts", "a fact read from a source", f"Under which licence is {model} published on Hugging Face?", check


def licence(task):
    m = re.search(r"Under which licence is (\S+) published on Hugging Face", task)
    return m and _fill('''import requests

data = requests.get(f"https://huggingface.co/api/models/{__M__}", headers={"User-Agent": "hive/1.0"}, timeout=30).json()
print("licence:", data["cardData"]["license"])
''', m=m.group(1))


make = m_licence
lesson = licence
