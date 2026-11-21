"""Retain complementary kept bodies by grading their actual trunks on the same four development requests."""
from functools import lru_cache
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MAKERS = ("h_prog_calc", "h_tab_group", "h_txt_sentences", "m_percent")
TRUNK = re.compile(r"(t17|t40|t80)\+(g[1-9]\d{0,5}trunk)")
CELL = re.compile(r"g[1-9]\d{0,5}(?:sources|code|data|words)\d{0,2}")
DIGEST = re.compile(r"[a-f0-9]{64}")


def enabled():
    k = os.environ.get("HIVE_ARCHIVE_K", "0")
    if k not in ("0", "3"):
        raise ValueError("HIVE_ARCHIVE_K must be 0 or 3")
    return k == "3"


def digest(path):
    with path.open("rb") as f:
        h = sha256()
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
        return h.hexdigest()


@lru_cache(maxsize=16)
def file_digest(path, size, modified, inode):
    return digest(path)


def matches(path, checksum):
    try:
        s = path.stat()
        return DIGEST.fullmatch(checksum) and file_digest(path, s.st_size, s.st_mtime_ns, s.st_ino) == checksum
    except (OSError, TypeError):
        return False


def asset(actor):
    if not TRUNK.fullmatch(actor):
        raise ValueError("invalid trunk")
    return actor.replace("+", ".") + ".gguf"


def read(path):
    try:
        data = json.loads(Path(path).read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def panel(slot):
    from training import exam, kinds
    from team.ternary import organ
    if not 1 <= slot <= len(MAKERS):
        raise ValueError("unknown panel slot")
    maker = MAKERS[slot - 1]
    if maker in kinds.HELD_OUT:
        raise ValueError("archive panel cannot use a held-out family")
    _, _, task, check = exam.remake(maker, f"archive-development-v1/{maker}")
    return task, check, organ(task)


@lru_cache(maxsize=1)
def protocol():
    # A different worker, task generator, checker, or serving protocol requires a fresh comparison.
    paths = ["team/solo.py", "team/ternary.py", "team/tools/sandbox.py", "training/exam.py",
             "training/body_archive.py"] + [f"training/kinds/{m}.py" for m in (*MAKERS, "_common", "_tab", "_programs")]
    return sha256("".join(digest(ROOT / p) for p in paths).encode()).hexdigest()


def profile(actor, slot, output):
    """Run exactly one named actor with empty memory; a timeout or missing individual grade supplies no observation."""
    from team import ternary
    from training import exam
    asset(actor)
    weights = ternary.ADAPTERS / (actor + ".gguf")
    checksum = digest(weights)
    task, check, organ = panel(slot)
    env = dict(os.environ, HIVE_MEMBERS=actor, HIVE_ARCHIVE_K="0", HIVE_ENGRAMS="0",
               HIVE_LIBRARY="0", HIVE_NOTES="0", HIVE_SHORT_ORDERS="1", HIVE_FULL_ORDERS="0",
               AGENT_TEAM_SOLO_TURNS="2", HIVE_ROTATE="", HIVE_SEATING="")
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        env["AGENT_TEAM_HOME"] = str(home / "memory")
        code, _ = exam.run_task([sys.executable, "-m", "training.body_archive", "one", str(slot), tmp],
                                180, cwd=ROOT, env=env)
        grades = exam.each_member(home, check) if code == 0 else []
        if len(grades) != 1 or grades[0]["who"] != actor or grades[0]["member"] != 1:
            raise ValueError(f"missing individual grade for {actor}, slot {slot}")
    receipt = {"actor": actor, "sha256": checksum, "protocol": protocol(), "slot": slot,
               "question": sha256(task.encode()).hexdigest(), "organ": organ, "ok": grades[0]["ok"]}
    Path(output).write_text(json.dumps(receipt) + "\n")


def collect(folder, arm, body, gen, expected_digest=None):
    """Consume only complete, matched development receipts. Fresh/held exam files never enter this function."""
    dna, trunk, cells = (body.get(k) for k in ("dna", "trunk", "cells"))
    actor = f"{dna}+{trunk}"
    if not TRUNK.fullmatch(actor) or not isinstance(cells, list) or not all(isinstance(c, str) and CELL.fullmatch(c) for c in cells):
        return None
    results, checksum = {}, None
    for slot in range(1, len(MAKERS) + 1):
        row = read(Path(folder) / f"archive-{arm}-{slot}" / "profile.json")
        task, _, organ = panel(slot)
        key = sha256(task.encode()).hexdigest()
        if (row.get("actor") != actor or row.get("slot") != slot or type(row.get("ok")) != bool
                or row.get("question") != key or row.get("organ") != organ or row.get("protocol") != protocol()
                or not DIGEST.fullmatch(str(row.get("sha256", ""))) or (checksum and checksum != row["sha256"])):
            return None
        checksum = row["sha256"]
        results[key] = {"organ": organ, "ok": row["ok"]}
    if expected_digest and expected_digest != checksum:
        return None
    return {"generation": body["generation"], "recorded_at": gen, "dna": dna, "cells": cells, "trunk": trunk,
            "actor": actor, "asset": asset(actor), "sha256": checksum, "protocol": protocol(), "results": results}


def solved(row):
    return {q for q, result in row["results"].items() if result["ok"]}


def retain(existing, incumbent, prior=None):
    """Keep the incumbent plus the smallest subset giving maximum measured joint coverage."""
    if not incumbent:
        return existing
    candidates, seen = [], {incumbent["sha256"]}
    for row in ([prior] if prior else []) + existing.get("bodies", []):
        if (not isinstance(row, dict) or row.get("dna") != incumbent["dna"] or row.get("protocol") != incumbent["protocol"]
                or row.get("sha256") in seen or row.get("generation", -1) >= incumbent["generation"]
                or set(row.get("results", {})) != set(incumbent["results"])):
            continue
        seen.add(row["sha256"])
        candidates.append(row)
    sets = [group for n in range(min(2, len(candidates)) + 1) for group in combinations(candidates, n)]
    def score(group):
        covered = solved(incumbent).union(*(solved(r) for r in group))
        return len(covered), -len(group), sum(len(solved(r)) for r in group), tuple(r["generation"] for r in group)
    best = max(sets, key=score)
    return {"bodies": [incumbent, *best], "incumbent": incumbent["actor"],
            "incumbent_solved": len(solved(incumbent)), "joint_solved": score(best)[0], "questions": len(incumbent["results"])}


def route(order, organ, archive, directory):
    """Seat one available archived trunk only for a task organ where matched diagnostics show a gain."""
    bodies = archive.get("bodies", [])
    if (not order or not TRUNK.fullmatch(order[0]) or not isinstance(bodies, list) or not bodies
            or order[0] != archive.get("incumbent") or not isinstance(bodies[0], dict) or bodies[0].get("actor") != order[0]):
        return order
    now = bodies[0]
    if not isinstance(now.get("results"), dict) or not matches(directory / (now["actor"] + ".gguf"), now.get("sha256", "")):
        return order
    best, margin = None, 0
    for row in bodies[1:3]:
        if not isinstance(row, dict) or not isinstance(row.get("results"), dict) or set(row["results"]) != set(now["results"]):
            continue
        actor = row.get("actor", "")
        if (not isinstance(actor, str) or not TRUNK.fullmatch(actor) or not matches(directory / (actor + ".gguf"), row.get("sha256", ""))):
            continue
        questions = [q for q, r in now["results"].items() if isinstance(r, dict) and r.get("organ") == organ and r.get("ok") is False]
        gain = sum(isinstance(row["results"][q], dict) and row["results"][q].get("ok") is True for q in questions)
        if gain > margin:
            best, margin = actor, gain
    return [order[0], best, *(a for a in order[1:] if a != best)] if best else order


def freeze(folder, body, roster, directory, gen, existing):
    """Freeze both arms' panel measurements before a fresh or held request can be read."""
    dna = body.get("dna")
    incoming = {"dna": dna, "trunk": gen + "trunk", "generation": int(gen[1:]),
                "cells": [a.split("+")[1] for a in roster if a.startswith(f"{dna}+") and CELL.fullmatch(a.split("+")[1])]}
    previous = collect(folder, "before", body, gen)
    candidate = collect(folder, "after", incoming, gen)
    if not previous or not candidate:
        return {}
    names = [actor for actor in roster if TRUNK.fullmatch(actor)]
    primary = max(names, key=lambda a: int(a.partition("+g")[2].removesuffix("trunk")), default="")
    current = next((r for r in (previous, candidate) if r["actor"] == primary), None)
    if not current or not matches(directory / (primary + ".gguf"), current["sha256"]):
        return {}
    return retain(existing, current, previous if current == candidate else None)


def fetch(directory, archive):
    repo = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
    for row in archive.get("bodies", [])[1:3]:
        actor = row.get("actor", "")
        if not TRUNK.fullmatch(actor) or row.get("asset") != asset(actor):
            continue
        path = directory / (actor + ".gguf")
        if matches(path, row["sha256"]):
            continue
        directory.mkdir(exist_ok=True, parents=True)
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            dest = Path(tmp) / "download"
            try:
                urllib.request.urlretrieve(f"https://github.com/{repo}/releases/download/hive-grown/{asset(actor)}", dest)
                if matches(dest, row["sha256"]):
                    dest.replace(path)
                else:
                    print(f"{actor} unavailable: checksum mismatch", file=sys.stderr)
            except OSError as exc:
                print(f"{actor} unavailable: {exc}", file=sys.stderr)


if __name__ == "__main__":
    from team import ternary
    command, *args = sys.argv[1:]
    if command == "one":
        from team import solo
        solo.run(panel(int(args[0]))[0], Path(args[1]) / "members", members=1)
    elif command == "fetch":
        if enabled():
            fetch(ternary.ADAPTERS, read(os.environ.get("HIVE_ARCHIVE_PATH") or ternary.BODY.parent / "body_archive.json"))
    elif command == "freeze":
        folder, gen, output = args
        snapshot = freeze(folder, read(ternary.BODY), ternary.roster(), ternary.ADAPTERS, gen,
                          read(ternary.BODY.parent / "body_archive.json"))
        Path(output).write_text(json.dumps(snapshot) + "\n")
        fetch(ternary.ADAPTERS, snapshot)
    elif command == "profile":
        slot, out = args
        names = [m for m in ternary.roster() if TRUNK.fullmatch(m)]
        if names:
            profile(max(names, key=ternary._born), int(slot), out)
