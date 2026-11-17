"""Read one generation's GitHub run the way the lead asks for it, in one pass, from the run's own artifacts and logs.

    python scripts/read_generation.py RUN_ID [--compare RUN_ID ...] [--dir FOLDER] [--programs]

(1) the pulse: easy and hard, p of n, and each hard kind beside the compared runs; a seat whose server died (every
    task wrong in a few minutes) is left out and counted.
(2) the lessons: for every cell slice, its passes and seconds a row, and for each hard subject that is new to this
    line its rows, passes, first and last loss (a kind is being learned when its loss ends below about 0.3); and the
    lessons kept back (2 of every kind, never trained on), their loss before and after training, by kind.
(3) the gather step's lesson line, and from all-rows the rows by "by" (who vouched for them) and by kind.
(4) with --programs: every failed hard task, with its folder in gate-work, how many programs the members wrote, the
    last program's error, and the lesson maker of its kind (`python training/lessons.py --show MAKER`), to read the
    members' way beside the lesson's.

It downloads only the small artifacts (gate-*, gate-work-*, all-rows); the cells' own records come from the train
jobs' logs, where each slice prints its record (with its subjects) at the end.
"""
import collections
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# the parsing is shared with the record job, which writes the read of every generation (docs/reads/)
from training.reads import LEARNED, kept_back, pulse, record_in_log, score, strip_log, subject_kind  # noqa: E402,F401
REPO = "Arnav123-s/HiveMIND"


def gh(*args, text=True):
    return subprocess.run(["gh", *args], capture_output=True, text=text, check=True).stdout


def artifacts(run):
    out = gh("api", f"repos/{REPO}/actions/runs/{run}/artifacts", "--paginate", "--jq", ".artifacts[] | [.name, .expired] | @tsv")
    return [line.split("\t")[0] for line in out.splitlines() if line.endswith("false")]


def fetch(run, names, home):
    for n in names:
        d = home / n
        if not d.exists():
            subprocess.run(["gh", "run", "download", str(run), "-R", REPO, "-n", n, "-D", str(d)], capture_output=True)
    return home


def jobs(run):
    out = gh("api", f"repos/{REPO}/actions/runs/{run}/jobs", "--paginate", "--jq", ".jobs[] | [.id, .name, .conclusion] | @tsv")
    return [line.split("\t") for line in out.splitlines()]


def log(job):
    try:
        text = gh("api", f"repos/{REPO}/actions/jobs/{job}/logs")
    except subprocess.CalledProcessError:
        return ""
    return strip_log(text)


def makers():
    """kind -> lesson maker, from the lessons' own list."""
    sys.path.insert(0, str(ROOT))
    from training import exam, lessons
    out = {}
    for m in lessons.SOLVERS:
        try:
            made = exam.remake(m, "1", 0, None)
        except Exception:  # noqa: BLE001 - a maker that cannot be made again here is left out
            continue
        if made:
            out.setdefault(made[1], m)
    return out


def records(run):
    """Every train slice's record, read from the JSON it prints at the end of its log (training/reads.record_in_log)."""
    return [{"job": name, "conclusion": concl, "record": record_in_log(log(job))} for job, name, concl in jobs(run) if name.startswith("train")]


def main(argv):
    run = argv[1]
    compare = [argv[i + 1] for i, a in enumerate(argv) if a == "--compare"]
    base = Path(argv[argv.index("--dir") + 1]) if "--dir" in argv else ROOT / "runs" / "read"
    home = base / run
    home.mkdir(parents=True, exist_ok=True)
    names = artifacts(run)
    fetch(run, [n for n in names if n.startswith("gate-") and not n.startswith("gate-work") or n == "all-rows"], home)
    if "--programs" in argv:
        fetch(run, [n for n in names if n.startswith("gate-work")], home)

    # (1) the pulse
    seats, dead = pulse(home)
    by, kinds = score(seats)
    others = {}
    for c in compare:
        ch = base / c
        ch.mkdir(parents=True, exist_ok=True)
        fetch(c, [n for n in artifacts(c) if n.startswith("gate-") and not n.startswith("gate-work")], ch)
        others[c] = score(pulse(ch)[0])
    print(f"## (1) pulse of run {run}: easy {by['e'][0]}/{by['e'][1]}, hard {by['h'][0]}/{by['h'][1]}; "
          f"{len(seats)} seats sat, {len(dead)} left out (server died: seeds {[d['summary']['seed'] for d in dead]})")
    for c, (b, _) in others.items():
        print(f"   run {c}: easy {b['e'][0]}/{b['e'][1]}, hard {b['h'][0]}/{b['h'][1]}")
    allk = sorted(set(kinds) | {k for _, (_, ks) in others.items() for k in ks})
    print("| hard kind | " + " | ".join([run] + compare) + " |")
    print("|---|" + "---|" * (1 + len(compare)))
    for k in allk:
        cells = [f"{kinds[k][0]}/{kinds[k][1]}" if k in kinds else "-"]
        cells += [f"{o[1][k][0]}/{o[1][k][1]}" if k in o[1] else "-" for o in others.values()]
        print(f"| {k} | " + " | ".join(cells) + " |")

    # (2) the lessons
    hard = set(kinds) | {k for _, (_, ks) in others.items() for k in ks}
    print("\n## (2) cells: passes, seconds a row; new hard subjects (rows, passes, first -> last loss)")
    print("| slice | result | passes | s/row | new hard subjects: rows passes first->last |")
    print("|---|---|---|---|---|")
    learned = collections.defaultdict(list)
    recs = records(run)
    for r in recs:
        rec = r["record"]
        if not rec:
            print(f"| {r['job']} | {r['conclusion']} | - | - | no record |")
            continue
        subs = [s for s in rec.get("subjects", []) if " · new" in s["subject"] and subject_kind(s["subject"]) in hard]
        parts = []
        for s in subs:
            f_, l_ = s["loss_first"], s["loss_last"]
            parts.append(f"{s['subject']}: {s['rows']} {s['passes']} {f_}->{l_}")
            if l_ is not None:
                learned[subject_kind(s["subject"])].append(l_)
        print(f"| {rec['member']} {rec.get('shard', '')} | {r['conclusion']} | {rec['passes']} | {rec['seconds_a_row']} | "
              + ("; ".join(parts) or "none") + " |")
    print("\n| hard kind | slices | mean last loss | learned (< 0.3) |")
    print("|---|---|---|---|")
    for k in sorted(learned):
        v = learned[k]
        print(f"| {k} | {len(v)} | {sum(v) / len(v):.3f} | {sum(x < LEARNED for x in v)}/{len(v)} |")
    print("\n## (2b) lessons kept back (never trained on): loss before -> after training, by kind")
    print("\n".join(kept_back(recs)))

    # (3) gather and rows
    print("\n## (3) gather and rows")
    for job, name, _ in jobs(run):
        if name == "gather":
            for line in log(job).splitlines():
                if line.startswith('{"lessons"'):
                    print("gather:", line[:600])
    rows = [json.loads(x) for f in home.glob("all-rows/**/rows.jsonl") for x in f.read_text().splitlines() if x.strip()]
    byby = collections.Counter(str(x.get("by")) for x in rows)
    print(f"{len(rows)} rows; by 'by': {dict(byby)}; lesson rows: {sum(x.get('who') == 'lesson' for x in rows)}")
    check = collections.Counter(x["kind"] for x in rows if x.get("by") == "check")
    for k, n in check.most_common():
        print(f"   by check: {n:3d}  {k}")

    # (4) failed hard tasks
    if "--programs" in argv:
        mk = makers()
        print("\n## (4) failed hard tasks: folder, programs written, last error, lesson maker")
        for d in seats:
            for t in d["tasks"]:
                if t["id"][0] != "h" or t["ok"]:
                    continue
                folder = next(home.glob(f"gate-work-*/**/{t['id']}"), None)
                progs = sorted(folder.rglob("member*_*.py"), key=lambda p: p.stat().st_mtime) if folder else []
                err = ""
                if progs:
                    e = progs[-1].with_name("." + progs[-1].name + ".err")
                    err = (e.read_text(errors="replace").strip().splitlines() or [""])[-1][:160] if e.exists() else ""
                print(f"- {t['id']} [{t['kind']}] maker {mk.get(t['kind'], 'none')}: {t['why'][:120]}\n"
                      f"    {len(progs)} programs in {folder.relative_to(home) if folder else '?'}; last error: {err}")


if __name__ == "__main__":
    main(sys.argv)
