#!/usr/bin/env python3
"""Muse's work, Muse's side — flaglab verification driver (workspace copy; the
/tmp originals did not survive the 2026-11-13 runtime restart, so the suites are
re-run from here).

Suites:
  base    — live train.py vs train_next.py on the 8 chassis configs: records must
            be identical on held_init/held_final/train_last100/steps/weights/
            mech_state_bytes/state_hist (the default-off claim, cross-file).
  neutral — flag present at its default value vs absent, same file: identical.
  pairs   — --vote-kernel fused vs current on non-default configs: identical
            (the kernel stream's bitwise claim, end-to-end through main()).
  smoke1/smoke2 — flag ON at a non-default value: trains, finite losses, and the
            expected mill_flags marker (or corpus marker) is recorded.
Usage: verify.py [base|neutral|pairs|smoke1|smoke2|all]
"""
import json
import subprocess
import sys

TINY = ["--dim", "64", "--layers-n", "2", "--batch", "8", "--steps", "8",
        "--minutes", "6", "--seed", "0", "--rope", "--tag", "flagnext"]
L = ["--arm", "layered_half"] + TINY
P = ["--arm", "plain_half"] + TINY
S = ["--arm", "ste_half"] + TINY
LF = ["--arm", "layered"] + TINY
CMP_FIELDS = ["held_init", "held_final", "train_last100", "steps",
              "ternary_weights", "mech_state_bytes", "state_hist"]


def run(file, args, timeout=420):
    out = subprocess.run(["python3", "verify_one.py", "--file", file,
                          "--timeout", str(timeout), "--"] + args,
                         capture_output=True, text=True, cwd="/home/hatch/workspace/edit-lab/bitnet-lab/flaglab")
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return {"rc": "driver-error", "rec": None, "tail": [out.stdout[-300:], out.stderr[-300:]]}


def finite(rec):
    return rec is not None and all(isinstance(rec[k], (int, float)) and abs(rec[k]) < 1e6
                                   for k in ("held_init", "held_final", "train_last100"))


def same_record(a, b):
    return a is not None and b is not None and all(a.get(k) == b.get(k) for k in CMP_FIELDS)


def suite_base():
    cases = [("layered_half", L), ("plain_half", P), ("ste_half", S),
             ("layered_half+carry", L + ["--carry"]),
             ("layered_half+cooldown", L + ["--cooldown"]),
             ("layered full", LF), ("mag", ["--arm", "mag"] + TINY),
             ("anneal", ["--arm", "anneal"] + TINY)]
    npass = 0
    for name, args in cases:
        a = run("train.py", args)
        b = run("train_next.py", args)
        ok = a["rc"] == 0 and b["rc"] == 0 and same_record(a["rec"], b["rec"])
        npass += ok
        print(f"{'PASS' if ok else 'FAIL'} base {name} "
              f"live_held={a['rec'] and a['rec'].get('held_final')} next_held={b['rec'] and b['rec'].get('held_final')}",
              flush=True)
        if not ok:
            print("  live tail:", a["tail"], "\n  next tail:", b["tail"], flush=True)
    print(f"BASE: {npass}/{len(cases)} identical", flush=True)
    return npass, len(cases)


NEUTRAL = [
    ("layered --gate-q 0.5", L + ["--gate-q", "0.5"], L),
    ("layered --clamp 1.0", L + ["--clamp", "1.0"], L),
    ("layered --comps 2", L + ["--comps", "2"], L),
    ("layered --leak 1.0", L + ["--leak", "1.0"], L),
    ("layered --flip-rule t1-first", L + ["--flip-rule", "t1-first"], L),
    ("layered --opt-lr 1e-3", L + ["--opt-lr", "0.001"], L),
    ("layered --wd 0", L + ["--wd", "0"], L),
    ("layered --vote-kernel current", L + ["--vote-kernel", "current"], L),
    ("plain --gate-q 0.5", P + ["--gate-q", "0.5"], P),
    ("plain --clamp 1.0", P + ["--clamp", "1.0"], P),
    ("plain --wd 0", P + ["--wd", "0"], P),
    ("plain --vote-kernel current", P + ["--vote-kernel", "current"], P),
    ("ste --ste-lr 3e-3", S + ["--ste-lr", "0.003"], S),
    ("ste --ste-wd 0", S + ["--ste-wd", "0"], S),
    ("plain --ease 1.0", P + ["--ease", "1.0"], P),
    ("plain --fp-first 0", P + ["--fp-first", "0"], P),
    ("plain --buffer 0", P + ["--buffer", "0"], P),
    ("plain --corpus v1", P + ["--corpus", "v1"], P),
    ("layered --qk-norm off", L + ["--qk-norm", "off"], L),
    ("layered --ffn swiglu", L + ["--ffn", "swiglu"], L),
    ("layered --norm rms", L + ["--norm", "rms"], L),
    ("layered --scale-gran tensor", L + ["--scale-gran", "tensor"], L),
    ("layered --wquant absmean", L + ["--wquant", "absmean"], L),
    ("layered --agrid legacy", L + ["--agrid", "legacy"], L),
    ("layered --rope-frac 1.0", L + ["--rope-frac", "1.0"], L),
    ("layered --moe-top 1", L + ["--moe-top", "1"], L),
    ("layered --swa off", L + ["--swa", "off"], L),
    ("layered --repeat 1 (sampler no-op)", L + ["--repeat", "1"], L),
]


def suite_neutral():
    npass = 0
    for name, args, ref in NEUTRAL:
        a = run("train_next.py", ref)
        b = run("train_next.py", args)
        ok = a["rc"] == 0 and b["rc"] == 0 and same_record(a["rec"], b["rec"])
        npass += ok
        print(f"{'PASS' if ok else 'FAIL'} neutral {name}", flush=True)
        if not ok:
            print("  ref:", a["rec"] and {k: a["rec"].get(k) for k in CMP_FIELDS},
                  "\n  got:", b["rec"] and {k: b["rec"].get(k) for k in CMP_FIELDS},
                  "\n  tails:", a["tail"], b["tail"], flush=True)
    print(f"NEUTRAL: {npass}/{len(NEUTRAL)} identical", flush=True)
    return npass, len(NEUTRAL)


PAIRS = [
    ("fused layered_half", L, ["--vote-kernel", "fused"]),
    ("fused plain_half", P, ["--vote-kernel", "fused"]),
    ("fused layered+carry", L + ["--carry"], ["--vote-kernel", "fused"]),
    ("fused mag", ["--arm", "mag"] + TINY, ["--vote-kernel", "fused"]),
    ("fused comps3 counter", L + ["--comps", "3", "--comp-v", "32:48:64", "--flip-rule", "counter"],
     ["--vote-kernel", "fused"]),
    ("fused leak 0.99", L + ["--leak", "0.99"], ["--vote-kernel", "fused"]),
]


def suite_pairs():
    npass = 0
    for name, base, extra in PAIRS:
        a = run("train_next.py", base)
        b = run("train_next.py", base + extra)
        ok = a["rc"] == 0 and b["rc"] == 0 and same_record(a["rec"], b["rec"])
        npass += ok
        print(f"{'PASS' if ok else 'FAIL'} pair {name}", flush=True)
        if not ok:
            print("  cur:", a["rec"] and {k: a["rec"].get(k) for k in CMP_FIELDS},
                  "\n  fus:", b["rec"] and {k: b["rec"].get(k) for k in CMP_FIELDS},
                  "\n  tails:", a["tail"], b["tail"], flush=True)
    print(f"PAIRS: {npass}/{len(PAIRS)} identical", flush=True)
    return npass, len(PAIRS)


# (name, argv, marker) — marker is ("mf", key) for mill_flags, ("corpus", "v2"),
# ("rec", field) for a plain record field, or None for trains+finite only.
SMOKE1 = [
    ("qk-norm", L + ["--qk-norm"], ("mf", "qk_norm")),
    ("qk-norm-q", L + ["--qk-norm-q"], ("mf", "qk_norm_q")),
    ("qk-clip", L + ["--qk-clip", "30"], ("mf", "qk_clip")),
    ("gated-attn", L + ["--gated-attn"], ("mf", "gated_attn")),
    ("gated-attn proj", L + ["--gated-attn", "proj"], ("mf", "gated_attn")),
    ("sink-logit", L + ["--sink-logit"], ("mf", "sink_logit")),
    ("scale-gran channel", P + ["--scale-gran", "channel"], ("mf", "scale_gran")),
    ("scale-gran group64", P + ["--scale-gran", "group64"], ("mf", "scale_gran")),
    ("scale-gran boundary", P + ["--scale-gran", "boundary"], ("mf", "scale_gran")),
    ("wquant absmax", P + ["--wquant", "absmax"], ("mf", "wquant")),
    ("learn-scale", P + ["--learn-scale"], ("mf", "learn_scale")),
    ("mag-cal 1.0", P + ["--mag-cal", "1.0"], ("mf", "mag_cal")),
    ("mag-cal 0.5", P + ["--mag-cal", "0.5"], ("mf", "mag_cal")),
    ("ease 0.5", P + ["--ease", "0.5"], ("mf", "ease")),
    ("fp-first 0.25", P + ["--fp-first", "0.25"], ("mf", "fp_first")),
    ("leak 0.99", L + ["--leak", "0.99"], ("mf", "leak")),
    ("ileak 0.99", L + ["--ileak", "0.99"], ("mf", "ileak")),
    ("hybrid 0.5:ste", L + ["--hybrid", "0.5:ste"], ("mf", "hybrid")),
    ("corpus v2", L + ["--corpus", "v2"], ("corpus", "v2")),
    ("wd 0.1 + cooldown", L + ["--wd", "0.1", "--cooldown"], ("mf", "wd")),
    ("wd 0.1 plain", P + ["--wd", "0.1"], ("mf", "wd")),
    ("buffer 2", P + ["--buffer", "2"], ("mf", "buffer")),
    ("log-level-hist", L + ["--log-level-hist"], ("rec", "level_hist")),
    ("cooldown-noemb", L + ["--cooldown", "--cooldown-noemb"], ("mf", "cooldown_noemb")),
    ("vote-kernel fused", L + ["--vote-kernel", "fused"], ("mf", "vote_kernel")),
]

SMOKE2 = [
    ("agree 0.9", L + ["--agree", "0.9"], ("mf", "agree")),
    ("freeze 0.05", ["--arm", "layered_half", "--dim", "64", "--layers-n", "2", "--batch", "8",
                     "--steps", "44", "--minutes", "6", "--seed", "0", "--rope", "--tag", "flagnext",
                     "--freeze", "0.05"], ("mf", "freeze")),
    ("clamp 0.5 (no flips by construction)", L + ["--clamp", "0.5"], ("mf", "clamp")),
    ("clamp none", L + ["--clamp", "none"], ("mf", "clamp")),
    ("flip-rule counter", L + ["--flip-rule", "counter"], ("mf", "flip_rule")),
    ("flip-rule sign-agree", L + ["--flip-rule", "sign-agree"], ("mf", "flip_rule")),
    ("flip-rule alternate", L + ["--flip-rule", "alternate"], ("mf", "flip_rule")),
    ("vsched 48:16", L + ["--vsched", "48:16"], ("mf", "vsched")),
    ("vlayer 0.002", L + ["--vlayer", "0.002"], ("mf", "vlayer")),
    ("whiten", L + ["--whiten"], ("mf", "whiten")),
    ("comps 3", L + ["--comps", "3", "--comp-v", "16:32:64"], ("mf", "comps")),
    ("gate-q 0.75 layered", L + ["--gate-q", "0.75"], ("mf", "gate_q")),
    ("gate-q 0.25 plain", P + ["--gate-q", "0.25"], ("mf", "gate_q")),
    ("opt-lr 0.002 layered", L + ["--opt-lr", "0.002"], ("mf", "opt_lr")),
    ("emb-int8", L + ["--emb-int8"], ("mf", "emb_int8")),
    ("untie-head", L + ["--untie-head"], ("mf", "untie_head")),
    ("init-std 0.01", L + ["--init-std", "0.01"], ("mf", "init_std")),
    ("agrid balanced", P + ["--agrid", "balanced"], ("mf", "agrid")),
    ("lowrank 8", P + ["--lowrank", "8"], ("mf", "lowrank")),
    ("hadamard", P + ["--hadamard"], ("mf", "hadamard")),
    ("rope-frac 0.5", L + ["--rope-frac", "0.5"], ("mf", "rope_frac")),
    ("rope-base 500", L + ["--rope-base", "500"], ("mf", "rope_base")),
    ("nope-every 2", L + ["--nope-every", "2"], ("mf", "nope_every")),
    ("swa 32:224", L + ["--swa", "32:224"], ("mf", "swa")),
    ("gqa 2", L + ["--gqa", "2"], ("mf", "gqa")),
    ("heads 2", L + ["--heads", "2"], ("mf", "heads")),
    ("norm prepost", L + ["--norm", "prepost"], ("mf", "norm")),
    ("norm post", L + ["--norm", "post"], ("mf", "norm")),
    ("norm none", L + ["--norm", "none"], ("mf", "norm")),
    ("subln", L + ["--subln"], ("mf", "subln")),
    ("no-ffn-norm", L + ["--no-ffn-norm"], ("mf", "no_ffn_norm")),
    ("ffn gelu", L + ["--ffn", "gelu"], ("mf", "ffn")),
    ("ffn relu2", L + ["--ffn", "relu2"], ("mf", "ffn")),
    ("ffn-width 256", L + ["--ffn-width", "256"], ("mf", "ffn_width")),
    ("moe 4", L + ["--moe", "4"], ("mf", "moe")),
    ("moe 4 top2 shared", L + ["--moe", "4", "--moe-top", "2", "--moe-shared"], ("mf", "moe")),
    ("moe hash-first", L + ["--moe", "4", "--moe-hash-first"], ("mf", "moe_hash_first")),
    ("deltanet 1", L + ["--deltanet", "1"], ("mf", "deltanet")),
    ("rwkv 1", L + ["--rwkv", "1"], ("mf", "rwkv")),
    ("act-sparsify 0.1", L + ["--act-sparsify", "0.1"], ("mf", "act_sparsify")),
    ("ste ste-warmup 4", S + ["--ste-warmup", "4"], ("mf", "ste_warmup")),
    ("ste ste-wd 0.1", S + ["--ste-wd", "0.1"], ("mf", "ste_wd")),
    ("ste two-stage", S + ["--two-stage"], ("mf", "two_stage")),
    ("ste two-stage-wd", S + ["--two-stage-wd"], ("mf", "two_stage_wd")),
    ("ste muon", S + ["--muon"], ("mf", "muon")),
    ("ste muon-split", S + ["--muon", "--muon-split"], ("mf", "muon_split")),
    ("ste polish", S + ["--polish"], ("mf", "polish")),
    ("arm annealflip", ["--arm", "annealflip"] + TINY, None),
    ("arm disarm", ["--arm", "disarm"] + TINY, None),
    ("arm resid8", ["--arm", "resid8"] + TINY, None),
    ("arm resid16", ["--arm", "resid16"] + TINY, None),
    ("arm fisherflip", ["--arm", "fisherflip"] + TINY, None),
    ("arm fisherflip share", ["--arm", "fisherflip", "--share", "0.5"] + TINY, ("mf", "share")),
    ("kd 0.5", ["--arm", "layered_half", "--dim", "64", "--layers-n", "2", "--batch", "8",
                "--steps", "12", "--minutes", "6", "--seed", "0", "--rope", "--tag", "flagnext",
                "--kd", "0.5"], ("mf", "kd")),
    ("kd-attn", ["--arm", "layered_half", "--dim", "64", "--layers-n", "2", "--batch", "8",
                 "--steps", "12", "--minutes", "6", "--seed", "0", "--rope", "--tag", "flagnext",
                 "--kd", "0.5", "--kd-attn"], ("mf", "kd_attn")),
    ("mtp 0.1", L + ["--mtp", "0.1"], ("mf", "mtp")),
    ("failweight 2", L + ["--failweight", "2"], ("mf", "failweight")),
    ("hybrid 0.5:votes", S + ["--hybrid", "0.5:votes"], ("mf", "hybrid")),
    ("modal 4", ["--arm", "layered_half", "--dim", "64", "--layers-n", "2", "--batch", "8",
                 "--steps", "24", "--minutes", "6", "--seed", "0", "--rope", "--tag", "flagnext",
                 "--modal", "4"], ("rec", "held_final_state")),
    ("verify-flips", ["--arm", "layered_half", "--dim", "64", "--layers-n", "2", "--batch", "8",
                      "--steps", "12", "--minutes", "6", "--seed", "0", "--rope", "--tag", "flagnext",
                      "--verify-flips"], ("mf", "verify_flips")),
    ("repeat 2", L + ["--repeat", "2"], ("mf", "repeat")),
    ("ctx-curr", L + ["--ctx-curr"], ("mf", "ctx_curr")),
    ("ctx-curr rev", L + ["--ctx-curr", "rev"], ("mf", "ctx_curr")),
    ("dedup", L + ["--dedup"], ("mf", "dedup")),
    ("freq-balance", L + ["--freq-balance"], ("mf", "freq_balance")),
    ("shift-aug", L + ["--shift-aug"], ("mf", "shift_aug")),
]


def suite_smoke(cases, label):
    npass = 0
    for name, args, marker in cases:
        r = run("train_next.py", args)
        rec = r["rec"]
        ok = r["rc"] == 0 and finite(rec)
        if ok and marker:
            kind, key = marker
            if kind == "mf":
                ok = key in (rec.get("mill_flags") or {})
            elif kind == "corpus":
                ok = rec.get("corpus") == key
            elif kind == "rec":
                ok = rec.get(key) is not None
        npass += ok
        print(f"{'PASS' if ok else 'FAIL'} smoke {name} held={rec and rec.get('held_final')}", flush=True)
        if not ok:
            print("  tail:", r["tail"], flush=True)
    print(f"{label}: {npass}/{len(cases)}", flush=True)
    return npass, len(cases)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    tot_p = tot_n = 0
    if which in ("base", "all"):
        p, n = suite_base(); tot_p += p; tot_n += n
    if which in ("neutral", "all"):
        p, n = suite_neutral(); tot_p += p; tot_n += n
    if which in ("pairs", "all"):
        p, n = suite_pairs(); tot_p += p; tot_n += n
    if which in ("smoke1", "all"):
        p, n = suite_smoke(SMOKE1, "SMOKE1"); tot_p += p; tot_n += n
    if which in ("smoke2", "all"):
        p, n = suite_smoke(SMOKE2, "SMOKE2"); tot_p += p; tot_n += n
    print(f"TOTAL: {tot_p}/{tot_n}", flush=True)


if __name__ == "__main__":
    main()
