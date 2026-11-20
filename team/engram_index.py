"""Cache catalogue metadata and lexical postings. Weight presence, revisions and checksums stay live."""
from collections import Counter, defaultdict
from functools import lru_cache
import json
import re

from . import memory


GROWTH_VALIDATION = "t80-output-graph-safe-v2"


def rows(path):
    result = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            result.append(row)
    return result


def identity(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


class Shelf:
    """One DNA's last record for each immutable edit name, its label edits, and its episode-word index."""
    def __init__(self, records):
        self.records = records
        self.labels = []
        self.sizes = {}
        self.postings = defaultdict(list)
        for name, row in records.items():
            if row.get("form") == "label":
                self.labels.append(name)
            elif not row.get("form") and isinstance(row.get("task"), str):
                words = memory.words(row["task"])
                self.sizes[name] = len(words)
                for word in words:
                    self.postings[word].append(name)

    def matches(self, words, least):
        if least <= 0:
            return self.sizes.keys()  # Zero overlap is eligible at this threshold.
        common = Counter(name for word in words for name in self.postings.get(word, ()))
        return [name for name, count in common.items()
                if count / max(1, len(words) + self.sizes[name] - count) >= least]


@lru_cache(maxsize=8)
def catalog(path, revision):
    """Process-local snapshot of one on-disk generation, rebuilt after an append or replacement."""
    by_dna = defaultdict(dict)
    for row in rows(path):
        dna, name = row.get("dna"), row.get("name")
        if isinstance(dna, str) and isinstance(name, str) and re.fullmatch(r"[a-zA-Z0-9_-]+", name):
            by_dna[dna][name] = row
    return {dna: Shelf(records) for dna, records in by_dna.items()}


EMPTY = Shelf({})
UNREADABLE = Shelf({})


def shelf(home, base):
    path = home / "index.jsonl"
    try:
        return catalog(path, identity(path.stat())).get(base, EMPTY)
    except FileNotFoundError:
        return None
    except (ValueError, OSError):
        return UNREADABLE
