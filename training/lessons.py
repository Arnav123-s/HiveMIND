"""Lessons: right programs for the kinds of task the hive cannot do yet, checked before they are taught.

    python training/lessons.py --seed S [--per-kind 1] [--several 4] [--failures failures.jsonl] [--most-failures 12] [--own-rows rows.jsonl ...] [--record generations.jsonl --dna t80] [--out rows.jsonl]
    python training/lessons.py --show MAKER [--seed S] [--level L]      one lesson: its task, its program, what it printed

Why (from first principles): the hive learns only from programs that its own checks confirmed. On a kind of task it
never gets right (reading a website, walking a site over pages, saving a file, writing a module) it has nothing to
learn from, so practising that kind more teaches nothing: in generation 27 such kinds stood at 0 of 2 or 0 of 3 for
generation after generation. A child learns a new skill from someone showing it once, done right. These are those
showings: for each kind, a program written the way a careful member would write it (fetch the site's first page,
follow its links, never make an address up; copy given data into the program; save a module from functions the
program has tested), made for a fresh task of that kind with fresh values every generation.

Nothing is taught unless it is right: every lesson's program is run in the hive's own runtime (team/tools/sandbox)
and put to the task's own check, the same one the exam uses. A lesson whose program fails its check (a site that
changed, a service down) is dropped, never taught.

Two kinds of rows come out, in the same form as the hive's own (training/grow.rows_of):
  first, done   the task and the right program; the program's output and DONE
  fix           where the hive got this very task wrong before (failures.jsonl from practice): its own wrong program
                and what it printed, then the right program. The task is made again from the same seed and level.

The kinds held out of practice (exam_hard.HELD_OUT) are never taught: they measure whether what is learned carries
over to work never shown.
"""
import json
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ---- the lessons: each kind's in its own file (training/kinds/, docs/KINDS.md), found there by the registry ------------
# The old names stay here, so what imported them from this module still finds them.
from training import kinds as K  # noqa: E402
from training.kinds._common import CATEGORY, DATE, FIND_AUTHOR, HEAD, PYPI, _fill  # noqa: E402,F401
from team.deliverables import wanted as _wanted  # noqa: E402
from training.kinds.h_age import age  # noqa: E402,F401
from training.kinds.h_join import join  # noqa: E402,F401
from training.kinds.h_log import LOG_COUNT, log  # noqa: E402,F401
from training.kinds.h_module import MODULES, module  # noqa: E402,F401
from training.kinds.h_search import search  # noqa: E402,F401
from training.kinds.h_since import since  # noqa: E402,F401
from training.kinds.h_table import table  # noqa: E402,F401
from training.kinds.h_walk import walk  # noqa: E402,F401
from training.kinds.h_web import WIKIDATA, wikidata  # noqa: E402,F401
from training.kinds.m_born import born  # noqa: E402,F401
from training.kinds.m_code import code  # noqa: E402,F401
from training.kinds.m_csv import csv_page  # noqa: E402,F401
from training.kinds.m_days import days  # noqa: E402,F401
from training.kinds.m_fix import mend  # noqa: E402,F401
from training.kinds.m_follow import LIST_ITEMS, TWO_SENTENCES, form  # noqa: E402,F401
from training.kinds.m_know import know  # noqa: E402,F401
from training.kinds.m_licence import licence  # noqa: E402,F401
from training.kinds.m_percent import percent  # noqa: E402,F401
from training.kinds.m_pypi import pypi_version  # noqa: E402,F401
from training.kinds.m_steps import orders  # noqa: E402,F401
from training.kinds.m_table import small_table  # noqa: E402,F401
from training.kinds.m_units import units  # noqa: E402,F401
from training.kinds.m_weekday import weekday  # noqa: E402,F401

# the makers taught, and how each one's program is written (each kind's `lesson`). The held-out kinds are never here.
SOLVERS = dict(K.SOLVERS)


def _maker(name):
    return K.get(name).make


def program_for(task, check):
    """The right program for a task, or None where a part has no lesson. A task of several parts (team/parts.py) gets
    its parts' programs one after another, each printing its answers under its own heading."""
    from team import parts as P
    pieces = P.of_task(task)
    if getattr(check, "maker", "") != "compound" or not pieces:
        return SOLVERS[check.maker](task) if check.maker in SOLVERS else None
    from team.tools.sandbox import given
    blocks = given(task)
    out = []
    for (letter, text), part in zip(sorted(pieces.items()), check.parts):
        kind = K.find(part[0])
        if kind and kind.GIVEN_FILE:  # the file the runtime saves holds the task's first block of data: this part's, or another's
            mine = given(text)
            prog = kind.lesson(text, copy=not (mine and blocks and blocks[0]["text"] == mine[0]["text"]))
        else:
            prog = SOLVERS[part[0]](text) if part[0] in SOLVERS else None
        if not prog:
            return None
        out.append(f"# ---- PART {letter}: each part is done by itself and printed under its own heading\n"
                   f"print({'PART ' + letter!r})\n" + prog.strip() + "\n")
    return "\n\n".join(out)


def lesson(maker, rseed, level=0, parts=None, timeout=300):
    """One lesson: the task made again from its maker (or its parts), its program, and whether the task's own check
    says it is right. {"maker", "rseed", "level", "parts", "task", "kind", "program", "answer", "ok", "why"}."""
    from training import exam
    from team.tools.sandbox import give, run_python
    made = exam.remake(maker, rseed, level, parts)
    if not made:
        return {"maker": maker, "rseed": rseed, "level": level, "parts": parts, "task": "", "kind": "", "ok": False, "why": "the task cannot be made again"}
    field, kind, task, check = made
    out = {"maker": maker, "rseed": rseed, "level": level, "parts": parts, "task": task, "kind": kind, "program": "", "answer": "", "ok": False, "why": ""}
    program = program_for(task, check)
    if not program:
        out["why"] = "no program for this form of the task"
        return out
    out["program"] = program
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        # the task's data saved where its program can open it, as the runtime does for a member (team/solo.member)
        give(task, work, skip=_wanted(task))
        res = run_python(program, work, name="lesson.py", timeout=timeout)
        out["answer"] = res["stdout"].strip()
        if res["returncode"] != 0 or not out["answer"]:
            out["why"] = f"the program failed: {(res['stderr'].strip().splitlines() or ['no output'])[-1][:200]}"
            return out
        (work / "lesson.py").unlink(missing_ok=True)
        try:
            ok, why = check(Path(tmp), out["answer"])
        except Exception as e:  # noqa: BLE001 - a check that cannot be made: not taught
            ok, why = False, f"check failed: {type(e).__name__}: {e}"
    out["ok"], out["why"] = bool(ok), why
    return out


def _const(name):
    """A constant of the members' own code (team/solo.py), read from its source: the orders a taught member works under
    and what it is asked after a program ran. Read, not imported, so that lessons need no model library."""
    import ast
    tree = ast.parse((ROOT / "team" / "solo.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


LIMIT = 508  # the longest row (in the DNA's pieces) a runner that trains in 32 bits takes (training/grow.train, fits)
_PIECE = re.compile(r"\d| ?[A-Za-z]{1,7}|\n| {2,}|[^\w\s]{1,2}")
_TOK = []


def _tokenizer():
    """The DNA's own tokenizer (the 1.7B's; the members share it), from the local Hugging Face cache or fetched (one
    small file); None where neither can be had, and pieces() then counts by a rule."""
    if not _TOK:
        try:
            from huggingface_hub import hf_hub_download, try_to_load_from_cache
            from tokenizers import Tokenizer
            from training import grow
            path = try_to_load_from_cache(grow.UNPACKED["t17"], "tokenizer.json")
            path = path if isinstance(path, str) else hf_hub_download(grow.UNPACKED["t17"], "tokenizer.json")
            _TOK.append(Tokenizer.from_file(path))
        except Exception:  # noqa: BLE001 - no library, no cache and no network: counted by the rule
            _TOK.append(None)
    return _TOK[0]


def pieces(text):
    """How many of the DNA's pieces a text is: by its tokenizer, or with none at hand by a rule that comes within
    about a sixth of it (every digit, short word, line end, indent and pair of signs one piece)."""
    tok = _tokenizer()
    return len(tok.encode(text or "", add_special_tokens=False).ids) if tok else len(_PIECE.findall(text or ""))


def row_pieces(row):
    """How many pieces a training row is with its chat template, as training/grow.train's encode counts it."""
    return 9 + sum(pieces(m["content"]) + 5 for m in row["messages"]) + pieces(row["output"])


ONE_LINE, ONE_HEAD, ONE_TAIL = 300, 70, 40  # a block of one line longer than ONE_LINE characters is cut to head * ONE_HEAD first and tail * ONE_TAIL last characters


def lean(task, program, head=3, tail=2, cut_one=False):
    """The task as a lesson's rows show it. A block of data the task gives (team/tools/sandbox.given) that the program
    does not copy in, because it reads the file the runtime saves, keeps only its first and last lines and a line
    that says how many are left out between: what is taught is the program, which never needs the rest. A log of 16
    to 34 lines is 400 to 850 pieces by itself, more than a row may hold on a runner that trains in 32 bits (T4)."""
    from team.tools.sandbox import given
    for b in given(task):
        lines = b["text"].splitlines()
        if len(lines) == 1 and len(lines[0]) > ONE_LINE and cut_one and lines[0].strip() not in program:
            # one long line (a message, a text): its start and its end, and how many characters are left out between
            ln, a, z = lines[0], head * ONE_HEAD, tail * ONE_TAIL
            task = task.replace(ln, ln[:a].rsplit(" ", 1)[0] + f" ... ({len(ln) - a - z} more characters like these) ... "
                                + (ln[len(ln) - z:].split(" ", 1)[-1] if z else ""), 1)
            continue
        if len(lines) > head + tail + 2 and not any(ln.strip() in program for ln in lines if len(ln.strip()) > 12):
            cut = lines[:head] + [f"... ({len(lines) - head - tail} more lines like these) ..."] + lines[len(lines) - tail:]
            task = task.replace(b["text"], "\n".join(cut), 1)
    return task


def rows(les, wrong=None, today=None):
    """Training rows of a lesson that its check passed, in the hive's own form (training/grow.rows_of). wrong: a
    failure record of the hive for this very task ({"program", "printed"}): a fix row is added from its program."""
    if not les.get("ok"):
        return []
    from training import grow
    short, more = _const("SHORT"), _const("MORE")
    fenced = f"```python\n{les['program'].strip()}\n```"
    base = {"task": les["task"], "kind": les["kind"], "seed": les["rseed"], "who": "lesson", "member": 0, "lesson": les["maker"]}  # noqa: E501
    # a block of data the program reads from its file keeps its first three and last two lines in the prompt; where the
    # row is then over LIMIT (an access log or JSON lines: 40 to 60 pieces a line), fewer: its first and last, its first (T4);
    # one long line (a message to read) is then cut to its first and last words
    for keep in ((3, 2), (3, 2, True), (1, 1, True), (1, 0, True)):
        head = [{"role": "system", "content": short.format(today=today or time.strftime("%Y-%m-%d (%A)"))},
                {"role": "user", "content": f"TASK: {lean(les['task'], les['program'], *keep)}"}]
        out = [base | {"type": "first", "messages": head, "output": fenced},
               base | {"type": "done", "messages": head + [{"role": "assistant", "content": fenced},
                                                             {"role": "user", "content": f"OUTPUT:\n{les['answer'][-1800:]}\n\n{more}"}], "output": "DONE"}]
        if max(row_pieces(r) for r in out) <= LIMIT:
            break
    if wrong and wrong.get("program") and wrong["program"].strip() != les["program"].strip():
        printed, lines = wrong.get("printed") or "(it printed nothing)", wrong["program"].strip().splitlines()
        # what is taught is the right program; the wrong one and what it printed are context. Over LIMIT, they are
        # cut (the middle of the program, the start of what it printed) more than training/grow.shorten would (T4)
        for keep, tail in ((len(lines), 1200), (6, 300), (3, 120), (0, 60)):
            cut = f"# ... ({len(lines) - keep} lines of this program left out) ..."
            shown = lines if len(lines) <= keep + 1 else lines[:keep - keep // 3] + [cut] + lines[len(lines) - keep // 3:] if keep else [cut]
            row = base | {"type": "fix", "messages": head + [{"role": "assistant", "content": "```python\n" + "\n".join(shown) + "\n```"},
                                                             {"role": "user", "content": grow.MEND.format(shown=f"OUTPUT:\n{printed[-tail:]}")}], "output": fenced}
            if row_pieces(row) <= LIMIT:
                break
        out.append(row)
    return out


OWN = 3  # a kind with this many right programs of the hive's own is the hive's to learn: it gets no more lessons


def own_counts(*row_files):
    """{kind: how many right programs the hive found itself} (rows of type "first" that no lesson wrote), from the
    rows gathered so far: practice, dreams, the trunk's and the cells' own work."""
    count = {}
    for f in row_files:
        for ln in Path(f).read_text().splitlines() if f and Path(f).exists() else []:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("type") == "first" and r.get("who") != "lesson":
                count[r.get("kind", "")] = count.get(r.get("kind", ""), 0) + 1
    return count


def pulse_counts(record, dna, last=3):
    """{kind: [passed, sat]} over the last `last` pulses of this DNA's body (training/reports/generations.jsonl)."""
    lines = []
    for ln in Path(record).read_text().splitlines() if record and Path(record).exists() else []:
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        kinds = d.get("arms", {}).get("after", {}).get("kinds") if isinstance(d, dict) else None
        if d.get("dna", "t17") == dna and isinstance(kinds, dict) and kinds:
            lines.append(kinds)
    out = {}
    for kinds in lines[-last:]:
        for k, v in kinds.items():
            if isinstance(v, list) and len(v) == 2:
                a = out.setdefault(k, [0, 0])
                a[0], a[1] = a[0] + v[0], a[1] + v[1]
    return out


def reason(why):
    """Why a lesson was not taught, in a few words: "timed out", "site refused" (the site answered with an error or
    not at all), "program failed" (it stopped with an error or printed nothing), "not made" (the task could not be made
    again), or "check failed" (it ran and printed, and the task's own check said no)."""
    w = (why or "").lower()
    if "timeout" in w or "timed out" in w:
        return "timed out"
    if any(x in w for x in ("connectionerror", "connection refused", "connection reset", "max retries", "httperror",
                            "too many requests", "forbidden", "service unavailable", "bad gateway", "nameresolution",
                            "name or service not known", "remotedisconnected", "sslerror", "is a web page (html), not json")) \
            or re.search(r"\b(403|429|5\d\d) (client|server) error", w):
        return "site refused"
    if w.startswith("check failed: jsondecodeerror"):  # the check read the site, and the site sent no JSON
        return "site refused"
    if w.startswith(("could not be made", "the task cannot be made", "no program")):
        return "not made"
    if w.startswith("the program failed"):
        return "program failed"
    return "check failed"


def by_kind_line(by_kind, failed):
    """The printed line: right of made for every kind, worst first, the main reason of its failures beside it."""
    parts = []
    for k, (r, n) in sorted(by_kind.items(), key=lambda kv: (kv[1][0] / max(kv[1][1], 1), kv[0])):
        why = failed.get(k) or {}
        main = max(why, key=why.get) if why else ""
        parts.append(f"{k} {r}/{n}" + (f" ({main})" if main else ""))
    return "lessons by kind: " + (", ".join(parts) or "none made")


def fitting(maker, rseed, level=0, parts=None, fresh=True, tries=8):
    """A lesson whose rows (first and done) fit LIMIT pieces. A fresh lesson (no task the hive got wrong) whose task
    drew values so long that they do not (a module asked of two 4 by 4 matrices: they are in the task and again in the
    program) is drawn again, with the seed and a number, up to `tries` times; the shortest right one is kept when none
    fits, for the runners that take longer rows (a join's always: its tables are in the task and in the program). A
    task the hive got wrong is its own and is never drawn again; nor is a task of several parts (its parts' seeds)."""
    best, n_best, plain = None, None, None
    for j in range(tries if fresh and maker != "compound" else 1):
        try:
            les = lesson(maker, rseed if j == 0 else f"{rseed}:{j}", level, parts)
        except Exception as e:  # noqa: BLE001 - a task that cannot be made (a site down): no lesson
            les = {"maker": maker, "ok": False, "why": f"could not be made: {type(e).__name__}: {str(e)[:120]}"}
        if not les.get("ok"):
            if best is None and j == 0:
                return les  # a lesson that is not right (a site down) is not drawn again: its failure is counted
            continue
        n = max(row_pieces(r) for r in rows(les, today="2026-01-01 (Thursday)"))  # its first and its done row
        if n <= LIMIT:
            # a kind with a detail the members get wrong (its module's `shows`): the task that asks it is the lesson; one
            # that does not is kept for the last draw
            if fresh and maker != "compound" and not _shows(maker, les) and j < tries - 1:
                plain = plain or les
                continue
            return les
        if best is None or n < n_best:
            best, n_best = les, n
    return plain or best


def _shows(maker, les):
    """True where the kind has no `shows`, or its task asks the detail (training/kinds/h_prog_lru.shows)."""
    fn = getattr(K.get(maker), "shows", None) if maker in SOLVERS else None
    return True if fn is None else bool(fn(les["task"]))


def agreed_wrong_kinds(failures):
    """{kind}: the kinds of tasks in the failures record whose wrong answer the hive delivered (its members agreed on
    it: training/grow.remember_failure writes "delivered"). Such a kind is not the hive's to learn alone: members that
    agree on a wrong detail confirm each other, so their own programs never correct it."""
    out = set()
    for ln in Path(failures).read_text().splitlines() if failures and Path(failures).exists() else []:
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        if isinstance(f, dict) and f.get("delivered") and f.get("kind"):
            out.add(f["kind"])
    return out


def teach(seed, per_kind=1, failures=None, most_failures=12, out=None, log=print, levels=None, minutes=0, several=4, own=None, pulse=None):  # noqa: F811
    """A generation's lessons: per_kind fresh tasks of every taught kind, at the body's levels, `several` fresh tasks of
    several parts, and the most recent tasks the hive got wrong (of the taught kinds), each made again and shown done
    right. Rows appended to out.
    own: {kind: right programs the hive found itself} (own_counts). Lessons only start a kind: one where the hive has
    OWN of its own gets none, so its practice and its dreams carry it from there, as they do every kind it can learn
    from its own work.
    pulse: {kind: [passed, sat]} of the body's last pulses (pulse_counts). A kind the body still fails more often than
    not is taught whatever it has of its own: generation 34 had 25 right programs of modules and passed 0 of 6, and
    with rows from every confirmed member a kind has 3 of its own long before the body passes it.
    Returns {"lessons" (planned, the kinds left to the hive among them), "made", "right", "rows", "dropped": [why],
    "left_to_the_hive": [kind], "by_kind": {kind: [right, made]},
    "failed_by_kind": {kind: {reason: n}}} (reason() gives the words), and logs the by-kind line last."""
    from training import grow
    levels = grow.body_levels() if levels is None else levels
    t0 = time.time()
    from training import exam
    plan = [(m, f"lesson:{seed}:{m}:{i}", levels.get(m, 0), None, None) for i in range(per_kind) for m in SOLVERS]
    # tasks of several parts, as practice gives them (half of it): as many parts as the body's level says
    pool = [_maker(m) for m in SOLVERS]
    k = max(2, int(levels.get("compound", 2) or 2))
    for i in range(several):
        rseed = f"lesson:{seed}:several:{i}"
        try:
            plan.append(("compound", rseed, k, exam.compound(rseed, k, pool, levels)[3].parts, None))
        except Exception as e:  # noqa: BLE001 - a part that cannot be made now (a site that does not answer): one lesson fewer
            log(f"lesson of several parts {i}: could not be made: {type(e).__name__}", flush=True)
    seen = set()
    for ln in reversed(Path(failures).read_text().splitlines() if failures and Path(failures).exists() else []):
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        key = (f.get("maker"), f.get("rseed"), f.get("level", 0))
        taught = f.get("maker") in SOLVERS or (f.get("maker") == "compound" and f.get("parts") and all(p[0] in SOLVERS for p in f["parts"]))
        if taught and key not in seen and len(seen) < most_failures:
            seen.add(key)
            plan.append((f["maker"], f["rseed"], f.get("level", 0), f.get("parts"), f))
    made, right, dropped, left = [], 0, [], set()
    agreed = agreed_wrong_kinds(failures)
    by_kind, failed = {}, {}
    for maker, rseed, level, parts, wrong in plan:
        if minutes and time.time() - t0 > minutes * 60:
            dropped.append("out of time")
            break
        if own is not None:
            try:
                made_now = exam.remake(maker, rseed, level, parts)
            except Exception:  # noqa: BLE001 - made below again, where the failure is said
                made_now = None
            p, n = (pulse or {}).get(made_now[1], [0, 0]) if made_now else (0, 0)
            if made_now and own.get(made_now[1], 0) >= OWN and not (n and 2 * p < n) and made_now[1] not in agreed:
                left.add(made_now[1])
                continue
        les = fitting(maker, rseed, level, parts, fresh=wrong is None)
        new = rows(les, wrong)
        right += bool(les.get("ok"))
        made += new
        kind = les.get("kind") or ("several parts" if maker == "compound" else maker)
        tally = by_kind.setdefault(kind, [0, 0])
        tally[0], tally[1] = tally[0] + bool(les.get("ok")), tally[1] + 1
        if not les.get("ok"):
            why = failed.setdefault(kind, {})
            r = reason(les.get("why", ""))
            why[r] = why.get(r, 0) + 1
            dropped.append(f"{maker}: {les.get('why', '')[:160]}")
        log(f"lesson {maker} {'(a task got wrong before) ' if wrong else ''}{'right' if les.get('ok') else 'NOT taught'}: {les.get('why', '')[:150]}", flush=True)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with open(out, "a") as f:
            for r in made:
                f.write(json.dumps(r) + "\n")
    if left:
        log(f"left to the hive (it has {OWN} or more right programs of its own): {', '.join(sorted(left))}", flush=True)
    log(by_kind_line(by_kind, failed), flush=True)
    return {"lessons": len(plan), "made": sum(n for _, n in by_kind.values()), "right": right, "rows": len(made), "dropped": dropped,
            "left_to_the_hive": sorted(left), "seconds": round(time.time() - t0), "by_kind": by_kind, "failed_by_kind": failed}


def main(argv):
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    if "--show" in argv:
        les = lesson(opt("--show"), opt("--seed", "show"), int(opt("--level", 0)))
        print(les["task"], "\n\n" + les["program"], "\n" + les["answer"], "\n\nright:", les["ok"], "-", les["why"])
        return 0 if les["ok"] else 1
    owned = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--own-rows"]
    res = teach(opt("--seed", time.strftime("%Y%m%d%H")), int(opt("--per-kind", 1)), opt("--failures"), int(opt("--most-failures", 12)),
                opt("--out", "lessons.jsonl"), minutes=float(opt("--minutes", 0)), several=int(opt("--several", 4)),
                own=own_counts(*owned) if owned else None, pulse=pulse_counts(opt("--record"), opt("--dna", "t80")) if opt("--record") else None)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
