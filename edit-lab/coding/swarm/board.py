"""Shared board: the one place every specialist reads and writes.

SQLite (stdlib), one file. Jobs flow through it, lessons accumulate on it,
and every score — eval scores and instruction-fidelity scores alike — is
recorded on it. A step counts as done only when its gate evidence is here.
"""
import json
import sqlite3
import time


class Board:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY, niche TEXT, title TEXT, payload TEXT,
            status TEXT DEFAULT 'open', result TEXT, parent INTEGER);
        CREATE TABLE IF NOT EXISTS lessons(
            id INTEGER PRIMARY KEY, niche TEXT, text TEXT, source TEXT, t TEXT);
        CREATE TABLE IF NOT EXISTS scores(
            id INTEGER PRIMARY KEY, kind TEXT, name TEXT, value REAL, detail TEXT, t TEXT);
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY, who TEXT, what TEXT, detail TEXT, t TEXT);
        """)
        self.db.commit()

    # ---- jobs -------------------------------------------------------------
    def post(self, niche, title, payload=None, parent=None):
        cur = self.db.execute(
            "INSERT INTO jobs(niche,title,payload,parent) VALUES(?,?,?,?)",
            (niche, title, json.dumps(payload or {}), parent))
        self.db.commit()
        return cur.lastrowid

    def claim(self, job_id, who):
        self.db.execute("UPDATE jobs SET status='claimed' WHERE id=?", (job_id,))
        self.db.commit()
        self.event(who, "claim", f"job {job_id}")

    def finish(self, job_id, result):
        self.db.execute("UPDATE jobs SET status='done', result=? WHERE id=?",
                        (json.dumps(result), job_id))
        self.db.commit()

    def fail(self, job_id, why):
        self.db.execute("UPDATE jobs SET status='failed', result=? WHERE id=?",
                        (json.dumps({"error": why}), job_id))
        self.db.commit()

    def job(self, job_id):
        row = self.db.execute(
            "SELECT id,niche,title,payload,status,result,parent FROM jobs WHERE id=?",
            (job_id,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "niche": row[1], "title": row[2],
                "payload": json.loads(row[3]), "status": row[4],
                "result": json.loads(row[5]) if row[5] else None, "parent": row[6]}

    def jobs(self, niche=None, status=None):
        q = "SELECT id FROM jobs WHERE 1=1"
        args = []
        if niche:
            q += " AND niche=?"; args.append(niche)
        if status:
            q += " AND status=?"; args.append(status)
        return [self.job(r[0]) for r in self.db.execute(q, args)]

    # ---- lessons / scores / events ---------------------------------------
    def log_lesson(self, niche, text, source=""):
        self.db.execute("INSERT INTO lessons(niche,text,source,t) VALUES(?,?,?,?)",
                        (niche, text, source, time.strftime("%F %T")))
        self.db.commit()

    def lessons(self, niche=None):
        q = "SELECT niche,text,source FROM lessons"
        args = []
        if niche:
            q += " WHERE niche=?"; args.append(niche)
        return [{"niche": r[0], "text": r[1], "source": r[2]}
                for r in self.db.execute(q, args)]

    def record_score(self, kind, name, value, detail=""):
        self.db.execute("INSERT INTO scores(kind,name,value,detail,t) VALUES(?,?,?,?,?)",
                        (kind, name, float(value), detail, time.strftime("%F %T")))
        self.db.commit()

    def scores(self, kind=None):
        q = "SELECT kind,name,value,detail FROM scores"
        args = []
        if kind:
            q += " WHERE kind=?"; args.append(kind)
        return [{"kind": r[0], "name": r[1], "value": r[2], "detail": r[3]}
                for r in self.db.execute(q, args)]

    def event(self, who, what, detail=""):
        self.db.execute("INSERT INTO events(who,what,detail,t) VALUES(?,?,?,?)",
                        (who, what, detail, time.strftime("%F %T")))
        self.db.commit()

    def events(self):
        return [{"who": r[0], "what": r[1], "detail": r[2]}
                for r in self.db.execute("SELECT who,what,detail FROM events ORDER BY id")]
