"""Bounded I/O hints extracted from checked earlier lessons. No task literals are rendered."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from team.deliverables import wanted


HERE = Path(__file__).resolve().parent
CARDS = {
    "read_csv": "CSV input: open INPUT with newline='', pass the file to csv.DictReader, and use the actual header names.",
    "read_jsonl": "JSON-lines input: import json; read each nonblank line of INPUT and decode that line with json.loads(line).",
    "write_csv": "CSV output: open(DEST, 'w', newline=''), make csv.writer(f), then call writerow(HEADER) and writerows(ROWS).",
    "write_json": "JSON output: with open(DEST, 'w') as f: json.dump(RESULT, f). Construct the requested JSON shape first.",
    "write_module": "Module output: define and test the requested functions, then write their source and required imports to the requested .py file.",
}
PREFIX = "I/O pattern from checked work. Substitute this task's filenames, values and rules.\n"
FILE = re.compile(r"(?<![\w./-])([\w-]+\.(?:csv|jsonl|ndjson|txt|log|json|py|tsv))\b", re.I)
READ = re.compile(r"\b(?:read|reads|reading|from|using|use|input|given|supplied|attached|contains|here is|here are)\b", re.I)
JSONL = re.compile(r"\b(?:json[ -]?lines|newline[- ]delimited json|one json (?:object|record) per line)\b", re.I)
NEGATED = re.compile(r"\b(?:not|never|no need to|without|avoid|skip|don't|do not)\s+(?:reading|writing|saving|creating|read|write|save|create|open|touch|modify|overwrite)\b", re.I)


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def signature(request):
    # The gate excludes repeated source requests even with case/spacing differences.
    return digest(" ".join(request.casefold().split()))


def roles(request):
    outputs = {name.lower() for name in wanted(request)}
    found = set()
    for name in outputs:
        role = {".py": "write_module", ".csv": "write_csv", ".json": "write_json"}.get(Path(name).suffix)
        if role:
            found.add(role)
    for m in FILE.finditer(request):
        name = m[1].lower()
        if name in outputs:
            continue
        start = max(request.rfind(mark, 0, m.start()) for mark in ("\n", ";", ". ")) + 1
        end = re.search(r"\n|;|\.(?: |$)", request[m.end():])
        clause = request[start:m.end() + (end.start() if end else 80)]
        if READ.search(clause):
            if name.endswith(".csv"):
                found.add("read_csv")
            if name.endswith((".jsonl", ".ndjson")) or (name.endswith((".log", ".txt")) and JSONL.search(request)):
                found.add("read_jsonl")
    return [key for key in CARDS if key in found]


@lru_cache(maxsize=1)
def load_bank():
    return json.loads((HERE / "bank.json").read_text())


def select(request, bank=None, protected=False):
    if protected or not request or NEGATED.search(request):
        return []
    bank = load_bank() if bank is None else bank
    if signature(request) in bank["source_prompts"]:
        return []
    return [r for r in roles(request) if r in bank["cards"]]


def render(request, protected=False):
    """Suffix for the user's task, or the empty string. Includes its own separator."""
    bank = load_bank()
    keys = select(request, bank, protected)
    if not keys:
        return ""
    suffix = "\n\n" + PREFIX + "\n".join(CARDS[k] for k in keys)
    # Every supported combination was tokenized as a complete suffix at freeze.
    return suffix if bank["tokens"]["+".join(keys)] <= 180 else ""
