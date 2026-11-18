"""Recoverable local work orders and executable proposals for two-record edits."""
import hashlib
import json
import re
import sqlite3
from itertools import combinations


DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def valid_rows(public, rows):
    return (isinstance(rows, dict) and set(rows) == set(public["names"])
            and all(isinstance(row, list) and len(row) == 2 and row[0] in DAYS
                    and row[1] in public["sites"] for row in rows.values()))


def replace(rows, edits):
    result = {name: row.copy() for name, row in rows.items()}
    for name, field, value in edits:
        result[name][field] = value
    return result


def literal(text, public, rows):
    """Only dispatch a complete imperative with literal, schema-known arguments."""
    names = "|".join(map(re.escape, public["names"]))
    days = "|".join(DAYS)
    sites = "|".join(map(re.escape, public["sites"]))
    match = re.fullmatch(fr"(?:Please )?(?:Move|Put|Switch|Set) ({names}) (?:to|at) "
                         fr"({days}|{sites})(?: at ({sites}))?[.!]?", text.strip(), re.I)
    if not match:
        return None
    name, value, site = (part.title() if part else None for part in match.groups())
    if site and value not in DAYS:
        return None
    edits = [(name, int(value not in DAYS), value)]
    if site:
        edits.append((name, 1, site))
    return replace(rows, edits)


def proposals(public, draft):
    """Propose reversible operations on the observed delta and edited literal values."""
    opening, names, latest = public["opening"], public["names"], public["last"]
    states = {}

    def add(label, state):
        states.setdefault(canonical(state), (label, state))

    add("Keep the draft as it stands", draft)
    add("Restore the whole opening plan", opening)
    fields = ("day", "site")
    for source in names:
        destination = next(n for n in names if n != source)
        changed = [j for j in (0, 1) if draft[source][j] != opening[source][j]]
        for size in range(1, len(changed) + 1):
            for subset in combinations(changed, size):
                desc = " and ".join(fields[j] for j in subset)
                undo = [(source, j, opening[source][j]) for j in subset]
                copy = [(destination, j, draft[source][j]) for j in subset]
                add(f"Undo {source}'s {desc} change", replace(draft, undo))
                add(f"Copy {source}'s new {desc} to {destination}, keeping {source}'s changes", replace(draft, copy))
                add(f"Transfer {source}'s {desc} change to {destination}, undoing it on {source}", replace(draft, undo + copy))
    for field, allowed in enumerate((DAYS, public["sites"])):
        for value in allowed:
            if re.search(rf"\b{re.escape(value)}\b", latest, re.I):
                for name in names:
                    for label, base in (("Keep the draft", draft), ("Restore the opening plan", opening)):
                        add(f"{label}, then set {name}'s {fields[field]} to {value}", replace(base, [(name, field, value)]))
    # Stable, task-independent of the expected answer. Identical public requests get identical menus.
    salt = canonical([public, draft])
    return [states[key] for key in sorted(states, key=lambda k: hashlib.sha256((salt + k).encode()).digest())]


class Conflict(ValueError):
    """A late writer or a reused command id cannot alter this work order."""


class Journal:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks(
                id TEXT PRIMARY KEY, context TEXT NOT NULL, rev INTEGER NOT NULL, rows TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipts(
                task TEXT NOT NULL, turn TEXT NOT NULL, base_rev INTEGER NOT NULL,
                body TEXT NOT NULL, PRIMARY KEY(task, turn)
            );
        """)

    def create(self, task, public):
        if not valid_rows(public, public["opening"]):
            raise ValueError("invalid opening")
        self.db.execute("INSERT INTO tasks VALUES (?,?,0,?)", (task, canonical(public), canonical(public["opening"])))

    def read(self, task):
        row = self.db.execute("SELECT context,rev,rows FROM tasks WHERE id=?", (task,)).fetchone()
        if row is None:
            raise KeyError(task)
        return json.loads(row[0]), row[1], json.loads(row[2])

    def apply(self, task, turn, base_rev, rows):
        """Atomically issue a local write and persist its receipt across process loss."""
        body = canonical(rows)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            public, rev, _ = self.read(task)
            receipt = self.db.execute("SELECT base_rev,body FROM receipts WHERE task=? AND turn=?", (task, turn)).fetchone()
            if receipt is not None:
                if receipt != (base_rev, body):
                    raise Conflict("command id already identifies a different write")
            else:
                if rev != base_rev:
                    raise Conflict("stale base revision")
                if not valid_rows(public, rows):
                    raise ValueError("illegal tool state")
                self.db.execute("UPDATE tasks SET rev=rev+1, rows=? WHERE id=?", (body, task))
                self.db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (task, turn, base_rev, body))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return base_rev + 1
