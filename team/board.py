"""The hive mind: one shared board every specialist reads from and writes to.

Steps, results, facts (with source URL and exact quote), artifacts, approvals
and a full event log live in one SQLite file per run, so the whole team sees
the same state and every run leaves an inspectable trace.
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS steps(
  id TEXT PRIMARY KEY, agent TEXT, task TEXT, needs TEXT, for_each TEXT,
  done_when TEXT, status TEXT, attempts INTEGER DEFAULT 0,
  result TEXT, verdict TEXT, feedback TEXT, started REAL, finished REAL);
CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, step TEXT, claim TEXT, url TEXT,
  quote TEXT, status TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS artifacts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, step TEXT, path TEXT, kind TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT, kind TEXT, msg TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT, kind TEXT, detail TEXT, decision TEXT);
"""


class Board:
    def __init__(self, run_dir, echo=True):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "board.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()
        self.echo = echo
        self.goal = ""

    # ---- events -------------------------------------------------------
    def log(self, agent, kind, msg, data=None):
        with self.lock:
            self.db.execute("INSERT INTO events(ts,agent,kind,msg,data) VALUES(?,?,?,?,?)",
                            (time.time(), agent, kind, msg, json.dumps(data) if data is not None else None))
            self.db.commit()
        with open(self.dir / "events.jsonl", "a") as f:
            f.write(json.dumps({"ts": round(time.time(), 2), "agent": agent, "kind": kind,
                                "msg": msg, "data": data}, default=str) + "\n")
        if self.echo:
            print(f"[{time.strftime('%H:%M:%S')}] {agent:<11} {kind:<9} {msg[:300]}", flush=True)

    # ---- steps --------------------------------------------------------
    def add_step(self, s):
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO steps(id,agent,task,needs,for_each,done_when,status) VALUES(?,?,?,?,?,?,?)",
                (s["id"], s["agent"], s["task"], json.dumps(s.get("needs", [])), s.get("for_each"),
                 s.get("done_when", ""), "todo"))
            self.db.commit()

    def update_step(self, sid, **kw):
        if not kw:
            return
        for k in ("result",):
            if k in kw and not isinstance(kw[k], str):
                kw[k] = json.dumps(kw[k], default=str)
        cols = ",".join(f"{k}=?" for k in kw)
        with self.lock:
            self.db.execute(f"UPDATE steps SET {cols} WHERE id=?", (*kw.values(), sid))
            self.db.commit()

    def step(self, sid):
        r = self.db.execute("SELECT * FROM steps WHERE id=?", (sid,)).fetchone()
        return self._row(r) if r else None

    def steps(self):
        return [self._row(r) for r in self.db.execute("SELECT * FROM steps ORDER BY rowid")]

    @staticmethod
    def _row(r):
        d = dict(r)
        d["needs"] = json.loads(d["needs"] or "[]")
        if d.get("result"):
            try:
                d["result"] = json.loads(d["result"])
            except json.JSONDecodeError:
                pass
        return d

    # ---- facts & artifacts -------------------------------------------
    def add_fact(self, step, claim, url, quote, status="unchecked", note=""):
        with self.lock:
            cur = self.db.execute("INSERT INTO facts(step,claim,url,quote,status,note) VALUES(?,?,?,?,?,?)",
                                  (step, claim, url, quote, status, note))
            self.db.commit()
            return cur.lastrowid

    def set_fact(self, fid, status, note=""):
        with self.lock:
            self.db.execute("UPDATE facts SET status=?, note=? WHERE id=?", (status, note, fid))
            self.db.commit()

    def facts(self, step=None, status=None):
        q, args = "SELECT * FROM facts WHERE 1=1", []
        if step:
            q += " AND (step=? OR step LIKE ?)"
            args += [step, step + "[%"]
        if status:
            q += " AND status=?"
            args.append(status)
        return [dict(r) for r in self.db.execute(q, args)]

    def add_artifact(self, step, path, kind, note=""):
        with self.lock:
            self.db.execute("INSERT INTO artifacts(step,path,kind,note) VALUES(?,?,?,?)", (step, str(path), kind, note))
            self.db.commit()

    def artifacts(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM artifacts")]

    # ---- approvals ----------------------------------------------------
    def record_approval(self, agent, kind, detail, decision):
        with self.lock:
            self.db.execute("INSERT INTO approvals(ts,agent,kind,detail,decision) VALUES(?,?,?,?,?)",
                            (time.time(), agent, kind, detail, decision))
            self.db.commit()

    def approvals(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM approvals")]

    # ---- shared context: what one specialist sees of the others' work --
    def context_for(self, needs, max_chars=3500):
        parts = []
        for sid in needs:
            rows = [s for s in self.steps() if s["id"] == sid or s["id"].startswith(sid + "[")]
            for s in rows:
                res = s.get("result") or {}
                if not isinstance(res, dict):
                    res = {"summary": str(res)}
                line = f"## {s['id']} ({s['agent']}, verdict={s.get('verdict')}): {s['task'][:200]}\n"
                if res.get("summary"):
                    line += f"Result: {res['summary'][:900]}\n"
                if res.get("items"):
                    line += "Items: " + json.dumps(res["items"])[:700] + "\n"
                if res.get("files"):
                    line += "Files: " + ", ".join(res["files"]) + "\n"
                facts = [f for f in self.facts(s["id"]) if f["status"] == "supported"]
                for f in facts[:8]:
                    line += f"- {f['claim']} [{f['url']}]\n"
                parts.append(line)
        text = "\n".join(parts)
        return text[-max_chars:] if len(text) > max_chars else text
