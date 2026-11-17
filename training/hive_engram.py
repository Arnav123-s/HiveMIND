"""The hive engram: one shared fast memory of the whole hive, that keeps learning between generations.

An engram (team/engram.py) is one checked task kept as one tiny ternary edit. The hive engram is one edit for all of
them: each time the hive has new checked rows, it goes on training from where it stopped, on the new rows and on a
sample of the rows it learned before (replay), so it learns without forgetting. The nightly regrowth folds it into
the trunk (training/merge.py) and it starts again from nothing; the rows it learned are kept for later replay.

    cells/engrams/<dna>+hive.gguf          what the runtime loads (team/ternary.py edits_here finds it as "hive")
    cells/engrams/<dna>+hive.safetensors   the same edit, kept to go on training from
    cells/engrams/hive_rows.jsonl          the rows it has learned (capped: the newest and a random share of older)
    cells/engrams/hive_index.jsonl         one line for each update and each fold
    cells/engrams/folded/                  old hive engrams, moved aside with the generation that folded them

    python3 training/hive_engram.py update ROWS.jsonl [--base t17] [--replay 0.5] [--rank 8] [--steps 24] [--home DIR]
    python3 training/hive_engram.py fold TRUNK_OUT TRUNK_EDIT [--base t17] [--weight 0.2] [--mode add|average] [--gen g40] [--home DIR]

HIVE_ENGRAMS_HOME moves the folder, as for every engram. Nothing calls this unless asked.
"""
import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NAME = "hive"
CAP = 2000  # rows kept in hive_rows.jsonl


def home_of(home=None):
    """The engrams folder: the one given, else team/ternary.py's ENGRAMS (HIVE_ENGRAMS_HOME, or cells/engrams), the
    folder the runtime looks in."""
    if home:
        return Path(home)
    from team import ternary
    return Path(ternary.ENGRAMS)


def files(base, home=None):
    """{kind: path} of the hive engram of this DNA: gguf (what the runtime loads), safetensors, json (its record)."""
    h = home_of(home)
    return {k: h / f"{base}+{NAME}.{k}" for k in ("gguf", "safetensors", "json")}


def read_rows(path):
    try:
        return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def write_rows(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))


def key(row):
    """What makes two rows the same lesson: the exchange and its answer."""
    return json.dumps([row.get("messages"), row.get("output"), row.get("rejected")], sort_keys=True)


def replay_sample(old, n, seed=0):
    """n of the rows learned before: half the newest, half at random from the rest (so old lessons come back too)."""
    n = max(0, min(n, len(old)))
    if not n:
        return []
    newest = old[len(old) - n // 2:] if n // 2 else []
    rest = old[:len(old) - len(newest)]
    return random.Random(seed).sample(rest, n - len(newest)) + newest


def replay_count(new, old, replay):
    """How many old rows go with `new` new ones: replay is their share of what is trained on (0.5: as many old as
    new), never more than there are."""
    if new <= 0 or old <= 0 or replay <= 0:
        return 0
    if replay >= 1:
        return old
    return min(old, max(1, round(new * replay / (1 - replay))))


def cap_rows(rows, cap=CAP, seed=0):
    """At most `cap` rows, in their order: the newest half of the cap, and a random sample of the older ones."""
    if len(rows) <= cap:
        return list(rows)
    keep_new = cap - cap // 2
    older, newest = rows[:len(rows) - keep_new], rows[len(rows) - keep_new:]
    picked = sorted(random.Random(seed).sample(range(len(older)), cap - keep_new))
    return [older[i] for i in picked] + newest


def log_line(home, line):
    h = home_of(home)
    h.mkdir(parents=True, exist_ok=True)
    with open(h / "hive_index.jsonl", "a") as f:
        f.write(json.dumps(line) + "\n")


def update(rows_path, base="t17", home=None, replay=0.5, rank=8, steps=24, cap=CAP, seed=None, log=print):
    """Train the hive engram on new checked rows (a .jsonl like grow.py's), going on from its last weights, with a
    replay sample of rows it learned before. Writes <base>+hive.gguf and .safetensors in the engrams folder, adds
    the new rows to hive_rows.jsonl, one line to hive_index.jsonl, and returns that line (None: no new rows)."""
    from training import grow
    h = home_of(home)
    h.mkdir(parents=True, exist_ok=True)
    f = files(base, h)
    store = h / "hive_rows.jsonl"
    old = read_rows(store)
    known = {key(r) for r in old}
    new, seen = [], set()
    for r in read_rows(rows_path):
        k = key(r)
        if k not in known and k not in seen:
            seen.add(k)
            new.append(r)
    if not new:
        log("hive engram: no new rows, nothing to learn")
        return None
    seed = int(time.time()) if seed is None else seed
    back = replay_sample(old, replay_count(len(new), len(old), replay), seed)
    rows = new + back
    start = f["safetensors"] if f["safetensors"].exists() else None
    work = h / f".{base}+{NAME}.rows.jsonl"
    write_rows(work, rows)
    t0 = time.time()
    try:
        meta = grow.train(str(work), NAME, base=base, epochs=max(1.0, steps / len(rows)), rank=rank, lr=5e-4, layers="last8", accum=1,
                          ternary_edit=True, out_dir=h, checkpoint=False, parent=str(start or ""), log=lambda *a, **k: None) or {}
    finally:
        work.unlink(missing_ok=True)
    trained = Path(grow.GROW) / f"{base}+{NAME}" / "adapter_model.safetensors"
    if trained.exists():
        shutil.copyfile(trained, f["safetensors"])
    write_rows(store, cap_rows(old + new, cap, seed))
    line = {"what": "update", "dna": base, "when": time.strftime("%Y-%m-%d %H:%M"), "rows_new": len(new), "rows_replayed": len(back),
            "rows_kept": min(cap, len(old) + len(new)), "from": f["safetensors"].name if start else "", "rank": rank,
            "seconds": round(time.time() - t0), "loss_first": meta.get("loss_first"), "loss_last": meta.get("loss_last"),
            "megabytes": meta.get("megabytes")}
    log_line(h, line)
    log(f"hive engram: {len(new)} new rows, {len(back)} replayed, {line['seconds']} s, loss {line['loss_first']} -> {line['loss_last']}")
    return line


def rank_of(edit):
    """The rank of an edit: the rows of its A factors (the largest, if they differ)."""
    return max((a.shape[0] for a, _ in edit.values()), default=0)


MODES = ("add", "average")


def fold(trunk_out, trunk_edit, base="t17", weight=0.2, rank=None, gen="", home=None, mode="add", log=print):
    """Fold the hive engram into the trunk, cut to the trunk's rank (training/merge.py), saved at trunk_out (a
    .safetensors file, or a folder PEFT reads). mode "add" (the default): trunk + weight * hive, so the trunk keeps all
    it holds and the hive engram is added on top (an average shrank the trunk by 1 - weight each night, a dilution of
    everything it had learned that nothing gave back). mode "average": (1 - weight) * trunk + weight * hive, as
    before. Both are trained with lora_alpha twice their rank, so their factors weigh alike. Then the hive engram
    starts again: its files move to folded/ with the generation's stamp; hive_rows.jsonl stays for replay. Returns
    what was done."""
    if mode not in MODES:
        raise ValueError(f"fold mode {mode!r}: one of {MODES}")
    from training import merge
    h = home_of(home)
    f = files(base, h)
    trunk = merge.load(trunk_edit)
    rank = rank or rank_of(trunk)
    if f["safetensors"].exists():
        edit, least = merge.merge([trunk, merge.load(f["safetensors"])], [1 - weight, weight] if mode == "average" else [1.0, weight], rank,
                                  normalize=mode == "average")
    else:
        edit, least = trunk, 1.0
    out = Path(trunk_out)
    if out.suffix == ".safetensors":
        merge.save(edit, out)
    else:
        try:
            from training.grow import UNPACKED
            name = UNPACKED.get(base, base)
        except ImportError:
            name = base
        merge.write(edit, out, name, rank)
    stamp = gen or time.strftime("%Y%m%d-%H%M")
    moved = []
    if f["safetensors"].exists():
        aside = h / "folded"
        aside.mkdir(parents=True, exist_ok=True)
        for k, p in f.items():
            if p.exists():
                to = aside / f"{base}+{NAME}.{stamp}.{k}"
                shutil.move(str(p), str(to))
                moved.append(to.name)
    line = {"what": "fold", "dna": base, "when": time.strftime("%Y-%m-%d %H:%M"), "gen": stamp, "folded": bool(moved), "weight": weight,
            "mode": mode, "rank": rank, "trunk": Path(trunk_edit).name, "out": str(out), "least_energy_kept": round(least, 4), "moved": moved}
    log_line(h, line)
    log(f"hive engram {'folded into the trunk (' + mode + ') with weight ' + str(weight) if moved else 'absent: the trunk is as it was'} (rank {rank})")
    return line


def parse(argv):
    p = argparse.ArgumentParser(prog="hive_engram.py", description="The hive's shared engram: update it, or fold it into the trunk.")
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("update", help="train it on new checked rows, with replay")
    u.add_argument("rows")
    u.add_argument("--base", default="t17")
    u.add_argument("--home", default=None)
    u.add_argument("--replay", type=float, default=0.5)
    u.add_argument("--rank", type=int, default=8)
    u.add_argument("--steps", type=int, default=24)
    u.add_argument("--cap", type=int, default=CAP)
    fo = sub.add_parser("fold", help="fold it into the trunk and start it again")
    fo.add_argument("trunk_out")
    fo.add_argument("trunk_edit")
    fo.add_argument("--base", default="t17")
    fo.add_argument("--home", default=None)
    fo.add_argument("--weight", type=float, default=0.2)
    fo.add_argument("--rank", type=int, default=None)
    fo.add_argument("--gen", default="")
    fo.add_argument("--mode", choices=MODES, default="add", help="add: trunk + weight*hive (default); average: (1-weight)*trunk + weight*hive")
    return p.parse_args(argv)


def main(argv):
    a = parse(argv)
    if a.cmd == "update":
        line = update(a.rows, base=a.base, home=a.home, replay=a.replay, rank=a.rank, steps=a.steps, cap=a.cap)
    else:
        line = fold(a.trunk_out, a.trunk_edit, base=a.base, weight=a.weight, rank=a.rank, gen=a.gen, home=a.home, mode=a.mode)
    print(json.dumps(line))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
