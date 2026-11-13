# Muse's work — Muse's side
# Companion eval-only anatomy runner for mill/CANDIDATES-J.md items J-022, J-013, J-047.
# Imports train.py (never edits it): Tiny, Layered, Direct, STE, offsets, held_windows,
# held_loss, EASE. Trains a config seed-matched (same seed -> same init, same batch
# stream, same step count as the filed runs.jsonl record), then computes PER-TARGET
# held losses and tags each target by (a) leaked vs unique (offsets sidecar) and
# (b) source class / GATE0 bucket.
#
# Modes:
#   --build-sidecar   build offsets_sidecar.npz (piece offset -> line_id; per-held-target
#                     line_id, leaked flag, window bucket, fine class) + sidecar_summary.json
#   --run --arm A [--rope] --seed S --steps N   train + per-target eval -> anatomy_runs/
#   --aggregate       print aggregate tables over anatomy_runs/*.json for the report
import argparse, hashlib, importlib.util, json, sys, time
from pathlib import Path
import numpy as np

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import train as T  # noqa: E402  (train.py: Tiny, Layered, Direct, STE, offsets, held_windows, held_loss)

BOS = 1
CTX, HELD_EVERY = T.CTX, T.HELD_EVERY
SIDECAR = LAB / "offsets_sidecar.npz"
OUTDIR = LAB / "anatomy_runs"

# ---------------------------------------------------------------- sidecar ----
def build_sidecar():
    import torch
    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    arr = np.asarray(data)
    n = len(arr)
    bos_pos = np.flatnonzero(arr == BOS).astype(np.int64)
    n_lines = len(bos_pos)
    ends = np.append(bos_pos[1:], n)
    print(f"pieces={n} lines={n_lines}", flush=True)

    def content_key(i):
        s, e = int(bos_pos[i]) + 1, int(ends[i])
        return hashlib.sha1(arr[s:e].tobytes()).digest() if e > s else b""

    def touches_held(i):
        s, e = int(bos_pos[i]), int(ends[i]) - 1  # inclusive span of the instance
        b0, b1 = s // CTX, e // CTX
        return any(b % HELD_EVERY == 0 for b in range(b0, b1 + 1))

    # Training-side content set: line contents with >=1 instance lying fully outside
    # every held-candidate block (train.py offsets() can never draw a window that
    # touches a held block, so a verbatim line is trainable only via such an instance).
    train_keys = set()
    for i in range(n_lines):
        if not touches_held(i):
            train_keys.add(content_key(i))
    print(f"training-side distinct line contents={len(train_keys)}", flush=True)

    held = T.held_windows(data)  # [128, CTX+1], exact train.py construction
    starts = [w * CTX for w in range(0, (n - CTX) // CTX) if w % HELD_EVERY == 0]
    pick = [starts[int(i * (len(starts) - 1) / 127)] for i in range(128)]
    assert all(int(held[k, 0]) == int(arr[pick[k]]) for k in range(128))

    # GATE0 bucket per held window (bucket_probe is the classifier J-047 names).
    spec = importlib.util.spec_from_file_location("bucket_probe", LAB / "scale-next" / "bucket_probe.py")
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    win_bucket = []
    for s in pick:
        b, _, _ = bp.bucket_of(np.asarray(arr[s:s + CTX]))
        win_bucket.append(b)

    # Per-target tags. Target of window k, position j is stream position q=s+1+j;
    # its line is the BOS instance containing q.
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(str(Path.home() / "workspace/fable-audit-copy/cells/scratch/tokenizer.json"))
    BOILER = ("copyright", "license", "licence", "permission is hereby", "warranty",
              "redistribution", "all rights reserved", "permission to use", "contributors")
    line_id_t = np.zeros((128, CTX), dtype=np.int64)
    leaked_t = np.zeros((128, CTX), dtype=bool)
    fine_t = np.empty((128, CTX), dtype=object)
    line_text_cache = {}
    for k, s in enumerate(pick):
        for j in range(CTX):
            q = s + 1 + j
            li = int(np.searchsorted(bos_pos, q, side="right") - 1)
            line_id_t[k, j] = li
            leaked_t[k, j] = content_key(li) in train_keys
            b = win_bucket[k]
            if b == "numeric":
                fine = "numeric_dump"
            elif b == "gibberish":
                fine = "merges_gibberish"
            elif b == "german":
                fine = "german"
            elif b == "lists":
                fine = "boilerplate"
            else:  # prose bucket: refine per line — license boilerplate vs prose/lab notes
                if li not in line_text_cache:
                    cs, ce = int(bos_pos[li]) + 1, int(ends[li])
                    txt = tk.decode([int(x) for x in arr[cs:ce] if x != BOS]).lower()
                    line_text_cache[li] = any(w in txt for w in BOILER)
                fine = "boilerplate" if line_text_cache[li] else "prose_lab"
            fine_t[k, j] = fine
    fine_codes = {c: i for i, c in enumerate(
        ["numeric_dump", "merges_gibberish", "boilerplate", "german", "prose_lab"])}
    fine_idx = np.vectorize(fine_codes.get)(fine_t).astype(np.int64)
    bucket_codes = {c: i for i, c in enumerate(["numeric", "gibberish", "german", "lists", "prose"])}
    bucket_idx = np.array([bucket_codes[b] for b in win_bucket], dtype=np.int64)
    np.savez_compressed(SIDECAR, bos_pos=bos_pos, held_starts=np.array(pick),
                        line_id=line_id_t, leaked=leaked_t, fine_idx=fine_idx,
                        bucket_idx=bucket_idx)
    tot = leaked_t.size
    summary = {
        "pieces": int(n), "lines": int(n_lines),
        "training_side_distinct_line_contents": len(train_keys),
        "held_targets": int(tot), "leaked_targets": int(leaked_t.sum()),
        "leaked_share": round(float(leaked_t.mean()), 4),
        "window_buckets": {b: win_bucket.count(b) for b in sorted(set(win_bucket))},
        "fine_class_targets": {c: int((fine_idx == i).sum()) for c, i in fine_codes.items()},
        "bucket_targets": {c: int((bucket_idx == i).sum() * CTX) for c, i in bucket_codes.items()},
    }
    (LAB / "sidecar_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1), flush=True)

# ------------------------------------------------------------------- run ----
def run_one(arm, rope, seed, steps, minutes_cap):
    import random
    import torch
    import torch.nn.functional as F
    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    held = T.held_windows(data)
    torch.manual_seed(seed)
    layers = 2 if arm in ("layered_half", "plain_half", "ste_half") else 4
    model = T.Tiny(layers=layers, rotary=rope)
    if arm in ("ste", "ste_half"):
        trainer = T.STE(model)
    elif arm in ("layered", "layered_half"):
        trainer = T.Layered(model)
    else:
        trainer = T.Direct(model, mode="plain" if arm == "plain_half" else arm)
    h0 = T.held_loss(model, held)
    rnd, t0 = random.Random(seed), time.time()
    done_steps = 0
    while done_steps < steps:
        if time.time() - t0 > minutes_cap * 60:
            raise SystemExit(f"safety cap hit at step {done_steps}")
        done = done_steps / steps
        T.EASE[0] = min(1.0, done / 0.5) if arm in ("ste", "ste_half") else 1.0
        at = T.offsets(rnd, len(data), 32)
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        trainer.step(loss, done)
        done_steps += 1
        if done_steps % 40 == 0:
            print(f"step {done_steps}/{steps} elapsed {time.time()-t0:.0f}s", flush=True)
    pooled = T.held_loss(model, held)
    # per-target held losses, reduction='none'
    old = T.EASE[0]
    T.EASE[0] = 1.0
    model.eval()
    per = np.zeros((len(held), CTX), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(held), 32):
            xb = held[i:i + 32]
            logits = model.next_piece(xb[:, :-1])
            per[i:i + 32] = F.cross_entropy(
                logits.reshape(-1, T.VOCAB), xb[:, 1:].reshape(-1),
                reduction="none").numpy().reshape(len(xb), CTX)
    model.train()
    T.EASE[0] = old
    label = arm + ("_rope" if rope else "")
    OUTDIR.mkdir(exist_ok=True)
    np.savez_compressed(OUTDIR / f"{label}_s{seed}.npz", per_target=per)
    rec = {"label": label, "arm": arm, "rope": rope, "seed": seed, "steps": done_steps,
           "wall_s": round(time.time() - t0, 1), "held_init": round(h0, 4),
           "held_pooled": round(pooled, 4),
           "held_from_targets": round(float(per.mean()), 4)}
    (OUTDIR / f"{label}_s{seed}.json").write_text(json.dumps(rec, indent=1))
    print("ANATOMY_RESULT " + json.dumps(rec), flush=True)

# ------------------------------------------------------------- aggregate ----
FINE = ["numeric_dump", "merges_gibberish", "boilerplate", "german", "prose_lab"]
BUCKETS = ["numeric", "gibberish", "german", "lists", "prose"]

def aggregate():
    sc = np.load(SIDECAR)
    leaked, fine_idx, bucket_idx = sc["leaked"], sc["fine_idx"], sc["bucket_idx"]
    bucket_t = np.repeat(bucket_idx[:, None], CTX, axis=1)
    runs = {}
    for p in sorted(OUTDIR.glob("*.npz")):
        runs[p.stem] = np.load(p)["per_target"]
    fams = {}
    for stem, per in runs.items():
        label, seed = stem.rsplit("_s", 1)
        fams.setdefault(label, []).append((int(seed), per))
    out = {}
    for label, lst in sorted(fams.items()):
        lst.sort()
        pers = [p for _, p in lst]
        def stats(mask):
            ms = [float(p[mask].mean()) for p in pers]
            return {"mean_of_seed_means": round(float(np.mean(ms)), 4),
                    "per_seed": [round(m, 4) for m in ms],
                    "pooled_all_seeds": round(float(np.concatenate(
                        [p[mask].ravel() for p in pers]).mean()), 4)}
        fam = {"n_seeds": len(lst), "steps_seeds": [s for s, _ in lst],
               "pooled": stats(np.ones_like(leaked)),
               "leaked": stats(leaked), "unique": stats(~leaked),
               "unique_only_pooled_check": None,
               "fine": {}, "buckets": {}}
        for i, c in enumerate(FINE):
            m = fine_idx == i
            if m.sum():
                st = stats(m)
                st["target_share"] = round(float(m.mean()), 4)
                st["loss_mass_share"] = round(float(np.mean(
                    [float(p[m].sum()) for p in pers]) / np.mean(
                    [float(p.sum()) for p in pers])), 4)
                fam["fine"][c] = st
        for i, b in enumerate(BUCKETS):
            m = bucket_t == i
            if m.sum():
                st = stats(m)
                st["windows"] = int((bucket_idx == i).sum())
                st["target_share"] = round(float(m.mean()), 4)
                fam["buckets"][b] = st
        out[label] = fam
    # champion cross-class leak split (J-022 secondary: gap by class)
    if "layered_half_rope" in fams:
        pers = [p for _, p in sorted(fams["layered_half_rope"])]
        cross = {}
        for i, c in enumerate(FINE):
            row = {}
            for nm, m in (("leaked", leaked), ("unique", ~leaked)):
                mm = (fine_idx == i) & m
                if mm.sum():
                    row[nm] = {"share_of_class": round(float(mm.sum() / (fine_idx == i).sum()), 4),
                               "mean": round(float(np.mean([float(p[mm].mean()) for p in pers])), 4)}
            cross[c] = row
        out["champion_leak_by_class"] = cross
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-sidecar", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--arm", default="layered_half")
    ap.add_argument("--rope", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=160)
    ap.add_argument("--minutes-cap", type=float, default=90.0)
    a = ap.parse_args()
    if a.build_sidecar:
        build_sidecar()
    elif a.run:
        run_one(a.arm, a.rope, a.seed, a.steps, a.minutes_cap)
    elif a.aggregate:
        aggregate()
