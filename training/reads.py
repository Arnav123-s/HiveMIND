"""The read of a generation, written by the record job itself: docs/reads/gNN.md and docs/reads/latest.md.

    python3 training/reads.py facts RUN --gate gate [--practice-work pw] [--out facts.json]
    python3 training/reads.py knowledge GEN [--record ...] [--knowledge docs/knowledge.json]   one entry a generation
    python3 training/reads.py write GEN --facts facts.json --gate gate --rows got/rows.jsonl [--lessons lessons.json]
                                   [--record training/reports/generations.jsonl] [--out docs/reads] [--svg docs/progress/chain.svg]

`facts` asks the GitHub API about the run (GITHUB_TOKEN or GH_TOKEN when set): each job's start and end, which train
slices were lost, each train slice's record (the JSON it prints at the end of its log, and how many rows it left out
as too long), gather's lessons line, who started the run; and from the gate's folders, the pulse seats whose server
died. The record line takes its hours, dead seats and lost slices from it (training/grow_record.py gate --facts).

`write` writes the read (docs/DECISIONS.md, order 2): the numbers of docs/PLAN.md's top table beside the last record
and the body before (the paired gate's before arm); the chain, one row a taught hard kind,

    lessons right of made -> rows that fit in training -> kept-back loss falls (beside the untaught kinds)
        -> the child alone writes it at the exam (beside its parent alone) -> the body passes it

the hours of each step; and one line `next piece:`, chosen by the rules of docs/DECISIONS.md: the first rule that
holds for the most taught hard kinds. It also draws the chain as bars by kind (docs/progress/chain.svg).

The parsing here is shared with scripts/read_generation.py (the reader run by hand). Needs nothing but Python, and
runs nothing the hive wrote: names are taken from other jobs only when this repository knows them.
"""
import collections
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # run as `python3 training/reads.py`: the kinds (training/kinds/) are found from the folder above
    sys.path.insert(0, str(ROOT))
REPO = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
RECORD = ROOT / "training" / "reports" / "generations.jsonl"
TALK = ROOT / "training" / "reports" / "talk"  # <generation>.json: the body's sitting of the talk exam (training/talk_exam.py)
STAGES = ("practice", "dream", "gather", "plan", "train", "join", "merge", "gate", "record")
LEARNED = 0.3
GAP = 15  # points: a taught kind's kept-back loss must fall this much more than the untaught kinds' (DECISIONS step 4)
KIND = r"[\w ,.:'()-]{1,80}"


# ---- the kinds, read from the sources (no network) -------------------------------------------------------------------
def maker_kinds():
    """{maker: kind} of every hard maker (training/kinds/, the kinds with HARD): each returns (field, kind, task,
    check), its kind read from its source. A maker whose field is a name, not written out (the program kinds,
    h_prog_*: `return (FAMILY, "a queue served ...", ...)`), is not read by kinds.written; its kind is taken from a task
    it makes, which needs no network (a kind that reads a site while it makes a task writes its kind out). Before, the
    two held-out program kinds were missing, so g45's held-out tasks were counted 0 of 9, not 0 of 10."""
    from training import kinds
    out = {}
    for m in kinds.HARD_KINDS:
        w = kinds.written(m.KIND)
        if w:
            out[m.KIND] = w[0]
        elif not m.NETWORK:
            try:
                out[m.KIND] = kinds.sample(m.KIND)[1]
            except Exception:  # noqa: BLE001 - a maker that cannot make a task offline is left out, as before
                pass
    return out


def taught_hard():
    """{maker: kind} of the hard kinds that have lessons: training/lessons.SOLVERS less the held-out kinds."""
    from training import kinds
    by = maker_kinds()
    return {m: by[m] for m in sorted(kinds.SOLVERS) if m in by and m not in kinds.HELD_OUT}


def held_out():
    from training import kinds
    by = maker_kinds()
    return {by[m] for m in kinds.HELD_OUT if m in by}


# ---- the pulse (shared with scripts/read_generation.py) --------------------------------------------------------------
def pulse(home, arm="*"):
    """The seats that sat, and apart the seats whose server died (every task wrong in a few minutes)."""
    seats, dead = [], []
    for f in sorted(Path(home).glob(f"gate-{arm}/*_mixed.json")):
        if f.parent.name.startswith("gate-work") or f.stat().st_size > 2_000_000:
            continue
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        s = d.get("summary") if isinstance(d, dict) else None
        if not isinstance(s, dict):
            continue
        d["arm"] = f.parent.name.split("-")[1] if f.parent.name.count("-") >= 2 else ""
        (dead if s.get("passed", 0) == 0 and s.get("minutes", 99) <= 3 else seats).append(d)
    return seats, dead


def score(seats):
    """({"e": [passed, sat], "h": [...]}, {hard kind: [passed, sat]})."""
    by = {"e": [0, 0], "h": [0, 0]}
    kinds = collections.defaultdict(lambda: [0, 0])
    for d in seats:
        for t in d.get("tasks") or []:
            lv = str(t.get("id", "?"))[:1]
            if lv not in by:
                continue
            by[lv][0] += bool(t.get("ok"))
            by[lv][1] += 1
            if lv == "h":
                kinds[t.get("kind")][0] += bool(t.get("ok"))
                kinds[t.get("kind")][1] += 1
    return by, kinds


def strip_log(text):
    """A job's log without the time stamp GitHub puts before each line."""
    return "\n".join(re.sub(r"^\S+Z ", "", ln) for ln in text.lstrip("﻿").splitlines())


def record_in_log(text):
    """The record a train slice prints at its end (a JSON object starting with "member"), or None."""
    i = text.rfind('\n{\n "member"')
    if i < 0:
        return None
    depth, j = 0, i + 1
    for k in range(j, len(text)):
        depth += {"{": 1, "}": -1}.get(text[k], 0)
        if depth == 0:
            try:
                return json.loads(text[j:k + 1])
            except json.JSONDecodeError:
                return None
    return None


def long_in_log(text):
    """(rows left out as too long, the limit in pieces) a train slice said, or (0, None)."""
    m = re.search(r"^(\d+) rows are longer than (\d+) pieces and are left out", text, re.M)
    return (int(m.group(1)), int(m.group(2))) if m else (0, None)


def lessons_in_log(text):
    """gather's lessons line (training/lessons.py prints it as JSON last), or None."""
    for ln in reversed(text.splitlines()):
        if ln.startswith('{"lessons"'):
            try:
                return json.loads(ln)
            except ValueError:
                return None
    return None


# what a train slice said of the owner's Colab notebook (training/colab.py), most telling first: only these phrases are
# taken from the log
COLAB_SAID = (("colab: the notebook could not grow it", "the notebook could not grow it"),
              ("colab: no cell from the notebook in", "no cell back in time"),
              ("colab: no notebook alive in", "notebook not there within the wait"),
              ("colab: no notebook (", "notebook gone before the order"),
              ("colab: could not", "the release could not be reached"),
              ("colab: no notebook seen in the last", "notebook not seen"))


def colab_in_log(text):
    """What a train slice said of the notebook, as one of COLAB_SAID's phrases, or None when it said nothing."""
    for start, said in COLAB_SAID:
        if re.search(r"^" + re.escape(start), text, re.M):
            return said
    return None


def _median(xs):
    xs = sorted(xs)
    return (xs[len(xs) // 2] + xs[(len(xs) - 1) // 2]) / 2 if xs else None


def _colab_split(slices):
    """(the records the notebook grew, the CPU slices' records)."""
    recs = [s.get("record") for s in slices if isinstance(s.get("record"), dict)]
    return [r for r in recs if r.get("grown_on") == "colab"], [r for r in recs if r.get("grown_on") != "colab"]


def _child(rec):
    c = str(rec.get("member", "?")).split("+")[-1]
    return c if re.fullmatch(r"g\d+[a-z]+\d{0,2}", c) else "?"


def colab_line(slices):
    """The read's line on the owner's Colab notebook: the child it grew, on which GPU, in how many minutes and steps,
    beside the CPU slices' median; or why it was not used."""
    if not slices:
        return "Colab: not measured (no train slice was read)"
    grown, cpu = _colab_split(slices)
    steps = [r["steps"] for r in cpu if isinstance(r.get("steps"), (int, float))]
    mins = [r["seconds"] / 60 for r in cpu if isinstance(r.get("seconds"), (int, float))]
    beside = (f"CPU slices: median {_median(steps):.0f} steps in {_median(mins):.0f} minutes" if steps and mins else "CPU slices: none measured")
    if grown:
        r = grown[0]
        gpu = str(r.get("gpu") or "?")
        gpu = gpu if re.fullmatch(r"[\w .()-]{1,40}", gpu) else "?"
        m = r.get("minutes") if isinstance(r.get("minutes"), (int, float)) else "?"
        st = r.get("steps") if isinstance(r.get("steps"), (int, float)) else "?"
        return f"Colab: {_child(r)} grown on {gpu} in {m} minutes, {st} steps ({beside})"
    said = {s.get("colab") for s in slices if s.get("colab")}
    why = next((w for _, w in COLAB_SAID if w in said), "notebook not seen")
    return f"Colab: not used ({why})"


def subject_kind(s):
    return s.split(" · ")[0]


def kept_back(recs):
    """The lessons kept back (never trained on; training/grow.kept_back), by kind: their loss where each slice started
    and where it ended, and the mean over the slices, as table lines. recs: [{"job", "record"}]."""
    by = collections.defaultdict(list)
    for r in recs:
        rec = r.get("record") or {}
        for k, v in (rec.get("kept_back") or {}).items():
            if v.get("before") is not None and v.get("after") is not None:
                by[k].append((f"{rec.get('member', r.get('job', '?'))} {rec.get('shard', '')}".strip(), v))
    if not by:
        return ["no slice's record has lessons kept back"]
    out = ["| kind | slices | rows | mean before -> after | change | each slice: before -> after |", "|---|---|---|---|---|---|"]
    for k in sorted(by):
        v = by[k]
        b = sum(x["before"] for _, x in v) / len(v)
        a = sum(x["after"] for _, x in v) / len(v)
        each = "; ".join(f"{who}: {x['before']:.3f} -> {x['after']:.3f}" for who, x in v)
        out.append(f"| {k} | {len(v)} | {v[0][1].get('rows', '-')} | {b:.3f} -> {a:.3f} | {a - b:+.3f} | {each} |")
    return out


# ---- the GitHub API (facts) ------------------------------------------------------------------------------------------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _get(url, raw=False):
    """GET from the API with the token when there is one; a redirect (a log's storage) is followed without it."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "hive-record"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=60) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            with urllib.request.urlopen(urllib.request.Request(e.headers["Location"], headers={"User-Agent": "hive-record"}), timeout=120) as r:
                body = r.read()
        else:
            raise
    return body.decode("utf-8", "replace") if raw else json.loads(body)


def api_jobs(run, repo=REPO):
    jobs, page = [], 1
    while True:
        d = _get(f"https://api.github.com/repos/{repo}/actions/runs/{run}/jobs?per_page=100&page={page}")
        jobs += d.get("jobs") or []
        if len(jobs) >= d.get("total_count", 0) or not d.get("jobs"):
            return jobs
        page += 1


def _when(s):
    try:
        return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) if isinstance(s, str) else None
    except ValueError:
        return None


def stage_of(name):
    """The step a job belongs to, by its name ("train (g38code, ...)" -> train); None for another job."""
    first = re.split(r"[ (]", str(name), maxsplit=1)[0]
    return first if first in STAGES else None


def hours_of(jobs, now=None):
    """({step: minutes from its first job starting to its last ending}, hours from the run's first job to its last
    end, or to now for a job still running). jobs: [{"name", "started_at", "completed_at", "conclusion"}]."""
    now = now or time.time()
    by, first, last = {}, None, None
    for j in jobs:
        if j.get("conclusion") == "skipped":
            continue
        a, b = _when(j.get("started_at")), _when(j.get("completed_at")) or now
        if a is None or b < a:
            continue
        first, last = min(first or a, a), max(last or b, b)
        s = stage_of(j.get("name"))
        if s:
            lo, hi = by.get(s, (a, b))
            by[s] = (min(lo, a), max(hi, b))
    minutes = {s: round((by[s][1] - by[s][0]) / 60) for s in STAGES if s in by}
    return minutes, round((last - first) / 3600, 2) if first is not None else None


def lost_slices(jobs):
    """[lost, of]: the train jobs that did not succeed, of all train jobs."""
    train = [j for j in jobs if stage_of(j.get("name")) == "train" and j.get("conclusion") != "skipped"]
    return [sum(1 for j in train if j.get("conclusion") not in ("success", None)), len(train)]


def _slim(rec):
    """What the read needs of a slice's record."""
    keep = ("member", "shard", "rows", "used", "steps", "passes", "seconds", "kept_back", "long", "long_by_kind", "rows_by_kind", "loss_first", "loss_last",
            "grown_on", "gpu", "minutes")
    out = {k: rec[k] for k in keep if k in rec}
    out["subjects"] = [s for s in rec.get("subjects") or [] if isinstance(s, dict) and str(s.get("subject", "")).endswith(" · new")]
    return out


def facts(run, gate=None, practice_work=None, repo=REPO, log=print):
    """What the run says of itself (see the module's doc). Whatever cannot be asked is left out and said."""
    out = {"run": str(run), "repo": repo, "missing": []}
    try:
        info = _get(f"https://api.github.com/repos/{repo}/actions/runs/{run}")
        actor = (info.get("triggering_actor") or info.get("actor") or {}).get("login", "")
        out["started_by"] = "line" if info.get("event") == "schedule" or actor == "github-actions[bot]" else "person"
        out["run_number"] = info.get("run_number")
    except (OSError, ValueError) as e:
        out["missing"].append(f"the run: {type(e).__name__}")
    try:
        jobs = api_jobs(run, repo)
    except (OSError, ValueError) as e:
        jobs = []
        out["missing"].append(f"the jobs: {type(e).__name__}")
    out["jobs"] = [{k: j.get(k) for k in ("id", "name", "started_at", "completed_at", "conclusion")} for j in jobs]
    if jobs:
        out["minutes_by_step"], out["hours"] = hours_of(out["jobs"])
        out["lost_slices"] = lost_slices(out["jobs"])
    slices = []
    for j in out["jobs"]:
        st = stage_of(j["name"])
        if st not in ("train", "gather") or j.get("conclusion") == "skipped":
            continue
        try:
            text = strip_log(_get(f"https://api.github.com/repos/{repo}/actions/jobs/{j['id']}/logs", raw=True))
        except (OSError, ValueError) as e:
            if j.get("conclusion") == "success":  # a lost runner keeps no log: it is counted in lost_slices
                out["missing"].append(f"log of {j['name']}: {type(e).__name__}")
            text = ""
        if st == "gather":
            out["gather_lessons"] = lessons_in_log(text)
            continue
        rec = record_in_log(text)
        n, most = long_in_log(text)
        slices.append({"job": j["name"], "conclusion": j.get("conclusion"), "record": _slim(rec) if rec else None, "long": n, "max_len": most}
                      | ({"colab": c} if (c := colab_in_log(text)) else {}))
    out["slices"] = slices
    if gate:
        out["dead_seats"] = len(pulse(gate)[1])
    if practice_work and Path(practice_work).is_dir():
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            import selfreliance
            r = selfreliance.row("first try", [practice_work])
            if r["tasks"]:
                out["first_try"] = [r["right_first_try"], r["tasks"]]
                out["hints_per_task"] = r["hints_per_task"]
        except Exception as e:  # noqa: BLE001 - the read goes on without it
            out["missing"].append(f"first try: {type(e).__name__}")
    log(f"facts of run {run}: {len(out['jobs'])} jobs, {sum(1 for s in slices if s['record'])} of {len(slices)} slice records, "
        f"hours {out.get('hours')}, lost slices {out.get('lost_slices')}, dead seats {out.get('dead_seats')}"
        + (f"; missing: {'; '.join(out['missing'])}" if out["missing"] else ""))
    return out


# ---- the chain -------------------------------------------------------------------------------------------------------
def load_rows(path):
    out = []
    for ln in Path(path).read_text().splitlines() if path and Path(path).exists() else []:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def lessons_by_kind(summary, rows=(), gen=""):
    """({kind: [right, made]}, how it was known). gather's by_kind (from generation 39); before it, the right ones are
    counted from this generation's lesson rows (a lower bound: rows with the same exchange are kept once) and the
    failed ones from the summary's dropped list ("maker: why"); with nothing dropped every lesson made was right."""
    if isinstance(summary, dict) and isinstance(summary.get("by_kind"), dict):
        return {k: [int(v[0]), int(v[1])] for k, v in summary["by_kind"].items()
                if isinstance(k, str) and isinstance(v, list) and len(v) == 2}, "gather"
    if not summary and not rows:
        return {}, "none"
    seeds = collections.defaultdict(set)
    for r in rows:
        if r.get("who") == "lesson" and r.get("gen") == gen and isinstance(r.get("kind"), str):
            seeds[r["kind"]].add(str(r.get("seed") or r.get("task")))
    out = {k: [len(v), len(v)] for k, v in seeds.items()}
    kinds = maker_kinds()
    for d in (summary or {}).get("dropped") or []:
        m = str(d).split(":", 1)[0].strip()
        if m in kinds:
            out.setdefault(kinds[m], [0, 0])[1] += 1
    return out, "rows"


def _used_new(rec):
    """{kind: rows of this generation (not mended ones) the slice trained on}, from its subjects."""
    used = collections.Counter()
    for s in rec.get("subjects") or []:
        parts = str(s.get("subject", "")).split(" · ")
        if len(parts) == 3 and parts[2] == "new" and parts[1] not in ("mend", "done"):
            used[parts[0]] += int(s.get("rows") or 0)
    return used


def left_exact(slices):
    """Whether every slice that kept a record counted its rows too long by kind (rows_by_kind, or long_by_kind)."""
    recs = [s["record"] for s in slices if s.get("record")]
    return bool(recs) and all(isinstance(r.get("rows_by_kind"), dict) or isinstance(r.get("long_by_kind"), dict) for r in recs)


def rows_left_out(slices, rows, gen):
    """{kind: [too long, of, skipped for memory]} of this generation's rows, over the slices that kept a record.

    From generation 42 each slice's record says rows_by_kind (training/grow.train): of the rows new this generation,
    by kind, how many it was given, left out as too long, never trained on because the memory guard skipped them, and
    trained on; those are taken as they are (a row not reached before the time was up is none of the three left out).
    A record that says long_by_kind (too long, of) is taken as it is, with nothing said of memory (None).

    Older records say only which rows were studied, so the rest is an estimate (see left_exact): every slice studies
    all the rows new this generation, so what it did not study of them is counted as left out (kept back ones taken
    off), whether too long, skipped for memory, or not reached in time. g41's read named T4 on it for two kinds of
    which T4 measured no row too long."""
    recs = [s["record"] for s in slices if s.get("record")]
    if not recs:
        return {}
    if all(isinstance(r.get("rows_by_kind"), dict) for r in recs):
        out = collections.defaultdict(lambda: [0, 0, 0])
        for r in recs:
            for k, v in r["rows_by_kind"].items():
                if isinstance(v, dict):
                    out[k][0] += int(v.get("too_long") or 0)
                    out[k][1] += int(v.get("given") or 0)
                    out[k][2] += int(v.get("skipped_memory") or 0)
        return {k: v for k, v in out.items() if v[1]}
    if all(isinstance(r.get("long_by_kind"), dict) for r in recs):
        out = collections.defaultdict(lambda: [0, 0])
        for r in recs:
            for k, v in r["long_by_kind"].items():
                if isinstance(v, list) and len(v) == 2:
                    out[k][0] += int(v[0])
                    out[k][1] += int(v[1])
        return {k: v + [None] for k, v in out.items()}
    measured = any("kept_back" in r for r in recs)
    seen, uniq = set(), []
    for r in rows:
        key = json.dumps([r.get("messages", [None])[1:], r.get("output"), r.get("rejected")], sort_keys=True)
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    back = set()
    if measured:
        sys.path.insert(0, str(ROOT))  # run as `python3 training/reads.py`, the folder above is not on the path
        from training import grow
        back = {t for ts in grow.kept_back(uniq).values() for t in ts}
    want = collections.Counter(r.get("kind") for r in uniq if r.get("gen") == gen and r.get("type") not in ("done", "mend") and r.get("task") not in back)
    used = [_used_new(r) for r in recs]
    out = {}
    for k in set(want) | {k for u in used for k in u}:
        of = max([want.get(k, 0)] + [u.get(k, 0) for u in used])
        if of:
            out[k] = [sum(max(0, of - u.get(k, 0)) for u in used), of * len(used), None]
    return out


HIVE_TYPES = ("first", "done", "fix", "pair", "foresee", "mend")  # rows from the hive's own checked work (training/grow.py)
RAW_TYPES = ("read", "judged")  # raw text read and judged pairs (training/raw.py)


def rows_by_source(rows, gen):
    """{"hive", "hive_fix", "lessons", "raw", "other"}: this generation's new rows (stamped gen by gather, and the
    mended ones) by where they came from. hive: the members' own checked practice and dreams (training/grow.py rows
    of a member, "fix" rows among them as hive_fix); lessons: the hand-written lesson makers (training/lessons.py with
    training/kinds/, who "lesson"); raw: text read and judged pairs (training/raw.py). None when no row says its gen."""
    new = [r for r in rows if (gen and r.get("gen") == gen) or r.get("type") == "mend"]
    if not new:
        return None
    out = dict.fromkeys(("hive", "hive_fix", "lessons", "raw", "other"), 0)
    for r in new:
        if r.get("who") == "lesson":
            out["lessons"] += 1
        elif r.get("type") in RAW_TYPES:
            out["raw"] += 1
        elif r.get("type") in HIVE_TYPES:
            out["hive"] += 1
            out["hive_fix"] += r.get("type") in ("fix", "mend")
        else:
            out["other"] += 1
    return out


def self_taught_line(src, slices):
    """The read's line on how much the hive taught itself: rows given to training by source, and why the rows trained
    on by source are not measured (each slice's record says trained rows by kind only)."""
    if src is None:
        given = "not measured (no row of this generation was given to the read: gather's rows, field gen)"
    else:
        mine, of = src["hive"], src["hive"] + src["lessons"]
        given = (f"{src['hive']} from the hive's own checked practice and dreams ({src['hive_fix']} of them fix rows), "
                 f"{src['lessons']} from the hand-written lesson makers (training/lessons.py, training/kinds/)"
                 + (f", {src['raw']} raw text read and judged" if src["raw"] else "")
                 + (f", {src['other']} other" if src["other"] else "")
                 + (f": the hive's own are {round(100 * mine / of)}% of those two" if of else ""))
    recs = [s["record"] for s in slices if s.get("record")]
    trained = ("by source: " + ", ".join(f"{k} {v}" for k, v in sorted(_sum_by_source(recs).items()))) if recs and all(
        isinstance(r.get("rows_by_source"), dict) for r in recs) else (
        "not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; "
        "a field rows_by_source {source: trained} would measure it)")
    return f"How much the hive taught itself: of this generation's new rows, {given}. Rows trained on: {trained}."


def _sum_by_source(recs):
    out = collections.Counter()
    for r in recs:
        for k, v in r["rows_by_source"].items():
            if isinstance(k, str) and re.fullmatch(r"\w{1,20}", k) and isinstance(v, int):
                out[k] += v
    return out


def lesson_counts(rows):
    """{kind: distinct lesson tasks} in the rows the slices trained on (kept back ones among them)."""
    by = collections.defaultdict(set)
    for r in rows:
        if r.get("who") == "lesson" and r.get("task"):
            by[r.get("kind") or "?"].add(r["task"])
    return {k: len(v) for k, v in by.items()}


def kept_losses(slices):
    """{kind: (mean before, mean after)} of the lessons kept back, over the slices."""
    by = collections.defaultdict(list)
    for s in slices:
        for k, v in ((s.get("record") or {}).get("kept_back") or {}).items():
            if isinstance(v, dict) and isinstance(v.get("before"), (int, float)) and isinstance(v.get("after"), (int, float)):
                by[k].append((v["before"], v["after"]))
    return {k: (sum(b for b, _ in v) / len(v), sum(a for _, a in v) / len(v)) for k, v in by.items()}


def fall(b, a):
    """How far a loss fell, in points (per cent of where it started)."""
    return 100.0 * (b - a) / b if b else 0.0


def untaught(losses, counts, taught_now, keep=2):
    """(the kinds the gap is read against, what they are). The untaught kinds are those whose every lesson was kept
    back (no lesson of theirs trained on); when there are none, the kinds that got no lesson this generation."""
    none_trained = [k for k in losses if 0 < counts.get(k, 0) <= keep]
    if none_trained:
        return none_trained, "kinds none of whose lessons were trained on"
    not_now = [k for k in losses if k not in taught_now]
    return not_now, "kinds with no lesson this generation"


def members_by_kind(seats, children, parents):
    """({kind: [child alone right, sat]}, {kind: [parent alone right, sat]}) from each member's own answer put to the
    task's check (training/exam.each_member), or ({}, {}) when the pulse kept none."""
    child, parent = collections.defaultdict(lambda: [0, 0]), collections.defaultdict(lambda: [0, 0])
    kids, olds = set(children), set(parents)
    for d in seats:
        for t in d.get("tasks") or []:
            for m in t.get("members") or []:
                if not isinstance(m, dict):
                    continue
                who = str(m.get("who", "")).split("+", 1)[-1]
                for names, table in ((kids, child), (olds, parent)):
                    if who in names:
                        table[t.get("kind")][0] += m.get("ok") is True
                        table[t.get("kind")][1] += 1
    return dict(child), dict(parent)


def chain(line, facts_, seats, rows, lessons_summary=None):
    """One row a taught hard kind: {"kind", "lessons", "left", "kept", "gap", "child", "parent", "body", "before"} and
    notes on what was not measured and how."""
    gen = line.get("generation", "")
    taught = taught_hard()
    les, how = lessons_by_kind(lessons_summary or facts_.get("lessons") or facts_.get("gather_lessons"), rows, gen)
    slices = facts_.get("slices") or []
    left = rows_left_out(slices, rows, gen)
    exact = left_exact(slices)
    losses = kept_losses(slices)
    base, base_is = untaught(losses, lesson_counts(rows), {k for k, v in les.items() if v[1]})
    base = [k for k in base if re.fullmatch(KIND, str(k))]
    base = [k for k in base if k not in taught.values()] or base
    base_fall = sum(fall(*losses[k]) for k in base) / len(base) if base else None
    after_seats = [d for d in seats if d.get("arm") in ("after", "")]
    children = [c for c in line.get("cells") or []]
    parents = sorted(set((line.get("parents") or {}).values()))
    child, parent = members_by_kind(after_seats, children, [])
    _, parent = members_by_kind(seats, [], parents)
    body = (line.get("arms") or {}).get("after", {}).get("kinds") or {}
    before = (line.get("arms") or {}).get("before", {}).get("kinds") or {}
    rows_out = []
    for m, k in taught.items():
        kl = losses.get(k)
        lo = left.get(k)
        r = {"kind": k, "maker": m, "lessons": les.get(k), "left": lo[:2] if lo else None,
             "left_memory": lo[2] if lo else None, "left_exact": exact,
             "kept": [round(kl[0], 3), round(kl[1], 3)] if kl else None,
             "gap": round(fall(*kl) - base_fall, 1) if kl and base_fall is not None else None,
             "child": child.get(k), "parent": parent.get(k), "body": body.get(k), "before": before.get(k) if before else None}
        rows_out.append(r)
    notes = []
    if how == "rows":
        notes.append("lessons: gather printed no count by kind this generation; the right ones are counted from the lesson rows "
                     "(rows with the same exchange are kept once, so this is at least), the failed ones from its dropped list")
    if how == "none":
        notes.append("lessons: no lessons line from gather was found")
    if not left:
        notes.append("rows left out: no train slice's record was read")
    elif exact:
        notes.append("rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in "
                     "brackets those the memory guard skipped every time they came up. Rows not reached before the time was "
                     "up are not left out")
    else:
        notes.append("rows left out: an estimate, the slices' records being older than rows_by_kind: by kind, this generation's "
                     "rows each slice did not study, of those it was given, whether too long, skipped for memory or not reached "
                     "in time (the slices say only their total too long: "
                     f"{', '.join(str(s.get('long')) for s in slices if s.get('record'))}). Rule 2 counts rows too long only, "
                     "so it holds on no estimate")
    if not losses:
        notes.append("kept-back loss: no slice's record has lessons kept back (training/grow.py kept_back, from generation 39)")
    elif base_fall is None:
        notes.append("gap: no untaught kind had lessons kept back to read the taught ones against")
    else:
        notes.append(f"gap: the kind's fall beside the mean fall of the {base_is} ({', '.join(sorted(base))}: {base_fall:.0f} points)")
    grown, _ = _colab_split(slices)
    if grown:
        def gap_of(group):
            ls = kept_losses(group)
            bs = [fall(*ls[k]) for k in base if k in ls]
            gs = [fall(*ls[k]) - sum(bs) / len(bs) for k in taught.values() if k in ls] if bs else []
            return f"{sum(gs) / len(gs):+.0f} points" if gs else "not measured"
        on_gpu = [s for s in slices if (s.get("record") or {}).get("grown_on") == "colab"]
        on_cpu = [s for s in slices if s.get("record") and s["record"].get("grown_on") != "colab"]
        notes.append(f"kept-back gap by where the child grew (mean over the taught hard kinds, against the same untaught kinds): "
                     f"{_child(grown[0])} on the Colab GPU {gap_of(on_gpu)}; the CPU children {gap_of(on_cpu)}")
    if not child and not parent:
        notes.append("child and parent alone: the pulse kept no member's own answer (training/exam.each_member)")
    else:
        notes.append(f"child alone: the answers of this generation's cells ({len(children)}) in the pulse; parent alone: those of their "
                     f"parents ({', '.join(parents) or 'none'}) in every arm. Two members sit a task, so these are few")
        if not parent:
            notes.append("parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the "
                         "newest cells first; the paired gate's before arm seats the body before, parents among it)")
    return rows_out, notes


# ---- the next piece (docs/DECISIONS.md, "The standing loop") ---------------------------------------------------------
RULES = [
    (1, "lessons right under 8 of 12", "lessons: mend that kind's lesson or its maker (R3 when the site is at fault)"),
    (2, "more than 1 row in 5 of the kind left out", "T4: shorter lessons"),
    (3, f"kept-back gap under {GAP} points", "dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial"),
    (4, f"gap {GAP} or more, the child alone right more often than its parent, the body not", "R1: a right member is not lost"),
    (5, f"gap {GAP} or more, the child alone not right", "T3: read 10 of its programs first; then the key lines weigh more"),
    (6, "taught hard kinds 12 of 23, two generations running", "K1: then K2 (wider) and M1 (the talk exam)"),
]


def _share(c):
    return c[0] / c[1] if c and c[1] else None


def holds(rule, r):
    """Whether a rule of 1-5 holds for one row of the chain (an unmeasured link holds no rule)."""
    if rule == 1:
        return bool(r["lessons"] and r["lessons"][1]) and r["lessons"][0] * 12 < 8 * r["lessons"][1]
    if rule == 2:
        # rows too long only: not those the memory guard skipped, nor those not reached in time (an estimate mixes
        # the three, so it holds no rule)
        return r.get("left_exact", True) and bool(r["left"] and r["left"][1]) and 5 * r["left"][0] > r["left"][1]
    if rule == 3:
        return r["gap"] is not None and r["gap"] < GAP
    if r["gap"] is None or r["gap"] < GAP or not (r["child"] and r["child"][1]):
        return False
    if rule == 4:
        if not (r["parent"] and r["parent"][1]):
            return False  # the parent sat no task of the kind: nothing to set the child beside
        ps = _share(r["parent"])
        body_not = (r["body"] or [0, 0])[0] <= (r["before"] or [0, 0])[0] if r["before"] else not (r["body"] or [0])[0]
        return _share(r["child"]) > ps and body_not
    if rule == 5:
        return r["child"][0] == 0
    return False


def taught_passed(line):
    """[passed, sat] of the taught hard kinds in a record line's pulse (after arm)."""
    kinds = (line.get("arms") or {}).get("after", {}).get("kinds") or {}
    taught = set(taught_hard().values())
    p = [v for k, v in kinds.items() if k in taught and isinstance(v, list) and len(v) == 2]
    return [sum(v[0] for v in p), sum(v[1] for v in p)]


PLAN = ROOT / "docs" / "PLAN.md"
NONE_HOLDS = "no rule holds: the loop holder chooses from the board"


def done_pieces(plan=PLAN):
    """The ids of the board's pieces that are done (docs/PLAN.md): those on the line "Done (do not redo):" (and the
    lines that carry it on, to the next blank line), and every board row whose Who column says done."""
    out, inside = set(), False
    text = Path(plan).read_text() if plan and Path(plan).exists() else ""
    for ln in text.splitlines():
        if ln.startswith("Done (do not redo):"):
            inside = True
        elif not ln.strip():
            inside = False
        if inside:
            out |= set(re.findall(r"\b([A-Z]\d+)\b", ln))
        m = re.match(r"^\| ([A-Z]\d+) \|.*\|([^|]*)\|\s*$", ln)
        if m and re.search(r"\bdone\b", m.group(2), re.I):
            out.add(m.group(1))
    return out


def piece_id(piece):
    """The board id a rule's piece starts with ("T4: shorter lessons" -> "T4"), or None."""
    m = re.match(r"([A-Z]\d+)\b", piece)
    return m.group(1) if m else None


def next_piece(rows, line, prev=None, done=frozenset()):
    """(rule, piece, kinds it holds for, counts {rule: kinds}): the rule that holds for the most taught hard kinds (a
    tie goes to the earlier rule), skipping a rule whose piece is done on the board (`done`, done_pieces()): then the
    next rule that holds is named. Rule 6 is the body's, not a kind's: when it holds it holds for every taught kind.
    When no rule holds, or only rules whose pieces are done, (7, NONE_HOLDS, [], counts)."""
    counts = {n: [r["kind"] for r in rows if holds(n, r)] for n in range(1, 6)}
    now, before = taught_passed(line), taught_passed(prev) if prev else [0, 0]
    counts[6] = [r["kind"] for r in rows] if now[0] >= 12 and before[0] >= 12 else []
    pieces = dict((n, p) for n, _, p in RULES)
    for n in sorted(range(1, 7), key=lambda n: (-len(counts[n]), n)):
        if counts[n] and piece_id(pieces[n]) not in done:
            return n, pieces[n], counts[n], counts
    return 7, NONE_HOLDS, [], counts


# ---- the read --------------------------------------------------------------------------------------------------------
def lines_of(record):
    out = []
    for ln in Path(record).read_text().splitlines() if Path(record).exists() else []:
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def unattended(lines, upto):
    """Generations recorded running, up to and with `upto`, that nobody started (started_by "line")."""
    n = 0
    for d in reversed([d for d in lines[:upto + 1] if not d.get("trial")]):
        if d.get("started_by") != "line":
            break
        n += 1
    return n


def _pq(c):
    return f"{c[0]} of {c[1]}" if c and c[1] else "-"


def talk_of(gen, folder=None):
    """The generation's talk exam (training/reports/talk/<gen>.json), or None when it did not sit one."""
    try:
        d = json.loads((Path(folder or TALK) / f"{gen}.json").read_text())
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and d.get("of") else None


def _talk(t):
    """A sitting of the talk exam in the table: out of 10, and by kind."""
    if not t:
        return "not sat"
    by = ", ".join(f"{k} {p} of {n}" for k, (p, n) in (t.get("kinds") or {}).items() if n)
    return f"{t.get('out_of_10')} of 10" + (f" ({by})" if by else "")


def fixed_held(line, arm="after"):
    """One arm's sitting of the fixed held-out exam in a record line (grow_record.held_exam), or None."""
    h = ((line or {}).get("held_exam") or {}).get(arm)
    return h if isinstance(h, dict) and h.get("of") else None


def held_cell(fixed, pulse):
    """The held-out row: the fixed exam's kinds passed (the goal's bar is half of them) and its tasks, with the
    pulse's few held-out tasks beside it; only the pulse's when the fixed exam was not sat."""
    if not fixed:
        return _pq(pulse)
    k = fixed.get("kinds") or [0, 0]
    return f"{k[0]} of {k[1]} kinds ({fixed['right']} of {fixed['of']} tasks of the fixed exam; pulse {_pq(pulse)})"


def top_table(line, prev, f, lines, idx, talk=(None, None)):
    """The rows of docs/PLAN.md's top table: (what, this generation, the last record, the body before).
    talk: the talk exam's sittings of this generation and the last record, when they sat it (a Talk row then)."""
    a = (line.get("arms") or {}).get("after", {})
    b = (line.get("arms") or {}).get("before", {})
    pa = (prev or {}).get("arms", {}).get("after", {})
    has_b = bool(b.get("seeds"))
    held = held_out()

    def held_c(arm):
        k = arm.get("kinds") or {}
        v = [k[x] for x in held if x in k]
        return [sum(x[0] for x in v), sum(x[1] for x in v)] if v else arm.get("unpractised")

    ft = f.get("first_try") or line.get("first_try")
    pft = (prev or {}).get("first_try")
    hours = f.get("hours") if f.get("hours") is not None else line.get("hours")
    pi = lines.index(prev) if prev in lines else -1
    return [
        ("Easy kinds passed", _pq(a.get("easy")), _pq(pa.get("easy")), _pq(b.get("easy")) if has_b else "-"),
        ("Hard kinds that have lessons", _pq(taught_passed(line)), _pq(taught_passed(prev)) if prev else "-",
         _pq(taught_passed({"arms": {"after": b}})) if has_b else "-"),
        ("Hard kinds never practised (held out)", held_cell(fixed_held(line), held_c(a)), held_cell(fixed_held(prev), held_c(pa)) if prev else "-",
         held_cell(fixed_held(line, "before"), held_c(b)) if has_b else "-"),
        ("Right at the first try (practice)", f"{ft[0] / ft[1]:.2f} ({_pq(ft)})" if ft and ft[1] else "not measured",
         f"{pft[0] / pft[1]:.2f}" if pft and pft[1] else "-", "-"),
        ("Hours for one generation", f"{hours:.1f}" if isinstance(hours, (int, float)) else "not measured",
         f"{prev['hours']:.1f}" if prev and isinstance(prev.get("hours"), (int, float)) else "-", "-"),
        ("Generations recorded with nobody's hand", str(unattended(lines, idx)), str(unattended(lines, pi)) if pi >= 0 else "-", "-"),
    ] + ([("Talk (the talk exam, out of 10; the bar is 8)", _talk(talk[0]), _talk(talk[1]) if prev else "-", "-")] if talk[0] else [])


def _left(r):
    """The chain's "rows left out": too long of given, those skipped for memory in brackets, or the estimate."""
    if not r["left"]:
        return "not measured"
    if not r.get("left_exact", True):
        return f"{_pq(r['left'])} (estimate)"
    return _pq(r["left"]) + (f" ({r['left_memory']} skipped for memory)" if r.get("left_memory") else "")


def render(line, prev, f, rows, notes, piece, lines, idx, talk=(None, None), done=frozenset()):
    gen = line.get("generation", "?")
    rule, what, kinds, counts = piece
    run = f.get("run", "")
    repo = f.get("repo", REPO)
    out = [f"# The read of {gen}", "",
           f"Run [{run}](https://github.com/{repo}/actions/runs/{run}), recorded {line.get('when', '?')}: the body was "
           f"**{line.get('verdict') or ('kept' if line.get('kept') else 'dropped')}**. {line.get('why', '')}", "",
           "Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.", "",
           "## The numbers", "",
           f"| What is measured | {gen} | {prev.get('generation', '-') if prev else '-'} (last record) | the body before (same seeds) |",
           "|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in top_table(line, prev, f, lines, idx, talk)]
    out += ["", "## The chain, by taught hard kind", "",
            "lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child "
            "alone writes it at the exam -> the body (two agree) passes it.", "",
            "| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        kept = f"{r['kept'][0]:.3f} -> {r['kept'][1]:.3f}" if r["kept"] else "not measured"
        gap = f"{r['gap']:+.0f}" if r["gap"] is not None else "not measured"
        les = _pq(r["lessons"]) if r["lessons"] and r["lessons"][1] else "none made"
        out.append(f"| {r['kind']} | {les} | {_left(r)} | {kept} | {gap} | "
                   f"{_pq(r['child']) if r['child'] else '-'} | {_pq(r['parent']) if r['parent'] else '-'} | {_pq(r['body'])} | {_pq(r['before'])} |")
    out += [""] + [f"- {n}" for n in notes] + ["", self_taught_line(f.get("_by_source"), f.get("slices") or [])]
    out += ["", "![The chain by kind](../progress/chain.svg)", "", "## Hours", ""]
    mins = f.get("minutes_by_step") or line.get("minutes_by_step") or {}
    if mins:
        out += ["| step | minutes |", "|---|---|"] + [f"| {s} | {mins[s]} |" for s in STAGES if s in mins]
        hrs = f.get("hours") if f.get("hours") is not None else line.get("hours")
        out += ["", f"From the first job to the last: **{hrs} hours** (the bar is 3). Each step runs from its first job's start to its last job's end; "
                "practice and dream run side by side."]
    else:
        out.append("Not measured: the run's jobs could not be read.")
    ls = f.get("lost_slices") or line.get("lost_slices")
    dead = f.get("dead_seats", line.get("dead_seats"))
    out += ["", f"Train slices lost: {_pq(ls) if ls else 'not measured'}. Pulse seats whose server died: "
            f"{dead if dead is not None else 'not measured'}.", "", colab_line(f.get("slices") or [])]
    skipped = [(n, p) for n, _, p in RULES if counts[n] and piece_id(p) in done]
    out += ["", "## Next piece", "", (f"next piece: {what} (rule {rule}: {RULES[rule - 1][1]}, for {len(kinds)} of {len(rows)} "
                                      f"taught hard kinds: {', '.join(kinds)})") if rule != 7 else
            f"next piece: none (rule 7: {NONE_HOLDS})", ""]
    if skipped:
        out += ["Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: "
                + "; ".join(f"rule {n} ({piece_id(p)})" for n, p in skipped) + ".", ""]
    out += ["| # | the chain shows | holds for |", "|---|---|---|"]
    out += [f"| {n} | {words} | {len(counts[n])}{': ' + ', '.join(counts[n]) if counts[n] and n != 6 else ''}"
            f"{' (piece done)' if counts[n] and piece_id(p) in done else ''} |" for n, words, p in RULES]
    unmeasured = [w for n, w in ((1, "lessons"), (2, "rows left out"), (3, "kept-back gap"), (4, "child alone"))
                  if all((r["lessons"], r["left"] if r.get("left_exact", True) else None, r["gap"], r["child"])[n - 1] in (None, [], {})
                         for r in rows)]
    if unmeasured:
        out += ["", f"Not measured this generation, so no rule could hold on it: {', '.join(unmeasured)}."]
    if f.get("missing"):
        out += ["", "What the run could not be asked: " + "; ".join(f["missing"]) + "."]
    return "\n".join(out) + "\n"


# ---- the chain as bars by kind ---------------------------------------------------------------------------------------
BARS = [("lessons", "lessons right", "#2a78d6", "#3987e5"), ("kept", "rows studied", "#eb6834", "#d95926"),
        ("fall", "kept-back loss fallen", "#1baf7a", "#199e70"), ("child", "child alone right", "#eda100", "#c98500"),
        ("body", "body right", "#e87ba4", "#d55181")]


def _bar_values(r):
    les = _share(r["lessons"])
    kept = 1 - _share(r["left"]) if r["left"] and r["left"][1] else None
    fallen = max(0.0, min(1.0, fall(*r["kept"]) / 100)) if r["kept"] else None
    return {"lessons": les, "kept": kept, "fall": fallen, "child": _share(r["child"]), "body": _share(r["body"])}


def chain_svg(rows, gen, w=760):
    """The chain as horizontal bars, one group a taught hard kind, each link a share from 0 to 100 %."""
    sys.path.insert(0, str(ROOT))
    from training.progress import _text
    label_w, top, bar_h, gap = 250, 78, 9, 2
    group = len(BARS) * (bar_h + gap) + 14
    h = top + group * max(1, len(rows)) + 30
    pw = w - label_w - 70
    light = "".join(f".c{k}{{fill:{c}}}" for k, _, c, _ in BARS)
    dark = "".join(f".c{k}{{fill:{c}}}" for k, _, _, c in BARS)
    style = ("<style>.bg{fill:#fcfcfb}.ink{fill:#0b0b0b}.ink2{fill:#52514e}.grid{stroke:#e4e3df}" + light
             + "@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.ink{fill:#f0efec}.ink2{fill:#c3c2b7}.grid{stroke:#2c2c2a}" + dark + "}"
             + 'text{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}</style>')
    b = [_text(16, 24, f"The chain of {gen}, by taught hard kind", size=15, weight="600"),
         _text(16, 42, "each link as a share: where a bar falls short, the chain breaks there; a missing bar was not measured", "ink2", 12)]
    for j, (_, name, _, _) in enumerate(BARS):
        x = 16 + j * 145
        b.append(f'<rect class="c{BARS[j][0]}" x="{x}" y="54" width="10" height="10" rx="2"/>' + _text(x + 15, 63, name, "ink", 11))
    for v in (0, .5, 1):
        x = label_w + pw * v
        b.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{top - 4}" y2="{h - 24}" stroke-width="1"/>' + _text(x, h - 10, f"{int(v * 100)}%", "ink2", 11, "middle"))
    for i, r in enumerate(rows):
        y0 = top + i * group
        b.append(_text(label_w - 10, y0 + group / 2, r["kind"][:40], "ink", 11, "end"))
        vals = _bar_values(r)
        for j, (k, name, _, _) in enumerate(BARS):
            y = y0 + j * (bar_h + gap)
            v = vals[k]
            if v is None:
                continue
            bw = max(2.0, pw * v)
            b.append(f'<rect class="c{k}" x="{label_w}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h}" rx="2">'
                     f'<title>{escape(r["kind"])}, {name}: {round(100 * v)}%</title></rect>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="the chain by kind">'
            + style + f'<rect class="bg" width="{w}" height="{h}" rx="8"/>' + "".join(b) + "</svg>\n")


def write(gen, facts_, gate, rows_file, lessons=None, record=RECORD, out=None, svg=None, talk_dir=None, plan=PLAN):
    """Writes docs/reads/GEN.md and latest.md (and the chain's bars); returns the next piece's line. talk_dir: where
    the talk exam's sittings are (training/reports/talk): a generation that sat it has a Talk row."""
    lines = lines_of(record)
    idx = max((i for i, d in enumerate(lines) if d.get("generation") == gen), default=-1)
    line = lines[idx] if idx >= 0 else {"generation": gen}
    if "started_by" not in line and facts_.get("started_by") in ("line", "person"):
        line = dict(line, started_by=facts_["started_by"])
        if idx >= 0:
            lines[idx] = line
    prev = next((d for d in reversed(lines[:idx]) if not d.get("trial") and (d.get("arms") or {}).get("after", {}).get("tasks")), None) if idx >= 0 else None
    seats, _ = pulse(gate) if gate else ([], [])
    rows = load_rows(rows_file)
    summary = None
    if lessons and Path(lessons).exists():
        try:
            summary = json.loads(Path(lessons).read_text().strip().splitlines()[-1])
        except (ValueError, IndexError):
            summary = None
    table, notes = chain(line, facts_, seats, rows, summary)
    facts_ = dict(facts_, _by_source=rows_by_source(rows, gen))
    done = done_pieces(plan)
    piece = next_piece(table, line, prev, done)
    talk = (talk_of(gen, talk_dir), talk_of(prev.get("generation"), talk_dir) if prev else None)
    text = render(line, prev, facts_, table, notes, piece, lines, idx, talk, done)
    out = Path(out or ROOT / "docs" / "reads")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{gen}.md").write_text(text)
    (out / "latest.md").write_text(text)
    svg = Path(svg or ROOT / "docs" / "progress" / "chain.svg")
    svg.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text(chain_svg(table, gen))
    said = next(ln for ln in text.splitlines() if ln.startswith("next piece:"))
    print(f"{out / (gen + '.md')}: {said}")
    return said


KNOWLEDGE = ROOT / "docs" / "knowledge.json"
ENTRY = ("id", "generation", "when", "verdict", "after", "before", "hard", "easy", "held_out", "first_try", "talk", "hours", "why")


def generation_entry(line, talk=None):
    """One generation as docs/knowledge.json keeps it ("generations"): the verdict, after and before (passed, of) on
    the same seeds, the hard kinds that have lessons, easy, held out, the first try (a share), the talk exam (out of
    10) and the hours; None for what was not measured."""
    a = (line.get("arms") or {}).get("after", {})
    b = (line.get("arms") or {}).get("before", {})
    held = held_out()
    k = a.get("kinds") or {}
    hv = [k[x] for x in held if x in k]
    pq = lambda c: [int(c[0]), int(c[1])] if isinstance(c, list) and len(c) == 2 and c[1] else None  # noqa: E731
    ft = line.get("first_try")
    return {"id": f"gen-{line.get('generation')}", "generation": line.get("generation"), "when": line.get("when", ""),
            "verdict": line.get("verdict") or ("kept" if line.get("kept") else "dropped"),
            "after": pq([a.get("passed"), a.get("tasks")]), "before": pq([b.get("passed"), b.get("tasks")]) if b.get("seeds") else None,
            "hard": pq(taught_passed(line)), "easy": pq(a.get("easy")),
            "held_out": pq([sum(x[0] for x in hv), sum(x[1] for x in hv)] if hv else a.get("unpractised")),
            "first_try": round(ft[0] / ft[1], 2) if isinstance(ft, list) and len(ft) == 2 and ft[1] else None,
            "talk": (talk or {}).get("out_of_10") if isinstance((talk or {}).get("out_of_10"), (int, float)) else None,
            "hours": line.get("hours") if isinstance(line.get("hours"), (int, float)) else None,
            "why": str(line.get("why", ""))[:300]}


def add_generation(gen, record=RECORD, knowledge=KNOWLEDGE, talk_dir=None):
    """Appends the generation's entry to docs/knowledge.json ("generations"), once: a second run for the same
    generation leaves it as it is."""
    line = next((d for d in reversed(lines_of(record)) if d.get("generation") == gen), None)
    if line is None:
        print(f"{gen}: no record line, so no entry")
        return 1
    k = json.loads(Path(knowledge).read_text())
    gens = k.setdefault("generations", [])
    entry = generation_entry(line, talk_of(gen, talk_dir))
    if any(g.get("id") == entry["id"] for g in gens):
        print(f"{knowledge}: {entry['id']} is there already")
        return 0
    gens.append(entry)
    Path(knowledge).write_text(json.dumps(k, indent=1, ensure_ascii=False) + "\n")
    print(f"{knowledge}: {entry['id']} added ({entry['verdict']}, after {entry['after']}, before {entry['before']})")
    return 0


def record_fields(f):
    """What the record line takes from the facts: only numbers in bounds and names this file knows."""
    out = {}
    m = f.get("minutes_by_step")
    if isinstance(m, dict):
        out["minutes_by_step"] = {s: int(v) for s, v in m.items() if s in STAGES and isinstance(v, (int, float)) and 0 <= v < 10000}
    if isinstance(f.get("hours"), (int, float)) and 0 <= f["hours"] < 100:
        out["hours"] = round(float(f["hours"]), 2)
    if isinstance(f.get("dead_seats"), int) and 0 <= f["dead_seats"] < 100:
        out["dead_seats"] = f["dead_seats"]
    ls = f.get("lost_slices")
    if isinstance(ls, list) and len(ls) == 2 and all(isinstance(x, int) and 0 <= x < 1000 for x in ls):
        out["lost_slices"] = ls
    ft = f.get("first_try")
    if isinstance(ft, list) and len(ft) == 2 and all(isinstance(x, int) and 0 <= x < 100000 for x in ft):
        out["first_try"] = ft
    if f.get("started_by") in ("line", "person"):
        out["started_by"] = f["started_by"]
    return out


def main(argv):
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    if argv[:1] == ["facts"] and len(argv) >= 2:
        f = facts(argv[1], opt("--gate"), opt("--practice-work"))
        Path(opt("--out", "facts.json")).write_text(json.dumps(f) + "\n")
        return 0
    if argv[:1] == ["knowledge"] and len(argv) >= 2:
        if not re.fullmatch(r"g\d{1,6}", argv[1]):
            print("not a generation's name")
            return 1
        return add_generation(argv[1], opt("--record", RECORD), opt("--knowledge", KNOWLEDGE))
    if argv[:1] == ["write"] and len(argv) >= 2:
        if not re.fullmatch(r"g\d{1,6}", argv[1]):
            print("not a generation's name")
            return 1
        fp = opt("--facts")
        f = json.loads(Path(fp).read_text()) if fp and Path(fp).exists() else {}
        write(argv[1], f, opt("--gate"), opt("--rows"), opt("--lessons"), opt("--record", RECORD), opt("--out"), opt("--svg"))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
