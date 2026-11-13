"""E-001 parallel driver (Muse's work, Muse's side).

Same experiment as factory/e001_waking_fit.py — same cache, same
simulator, same ascent, same gates; this driver only parallelizes
the two CPU-bound phases (verifier cache build, real-path evals)
across a fork pool, because the lab box is shared with the whole
sprint (load > 25 on 1.5 cores) and the serial driver was getting
a single-digit CPU share. All logic lives in e001_waking_fit.py;
this file imports it. Writes only factory/learned_say_waking.json.
"""
from __future__ import annotations

import json
import time
from multiprocessing import Pool
from pathlib import Path

import factory.e001_waking_fit as E
from factory import learned_say as say_mod
from factory import say_dev

wd = E.wd
C = E.C
CLASSES = E.CLASSES

_REG = None
_SEATS = None
_WD = None


def _cache_row(item):
    code = item["text"]
    row = say_mod.seat_margins(_REG, code, _SEATS)
    ctx_raw = wd.gen_probes(code)
    ctx = {"probes": ctx_raw["probes"], "kinds": ctx_raw["kinds"]}
    ver = {}
    for cls in CLASSES:
        try:
            r = wd.VERIFIERS[cls](code, ctx)
            ver[cls] = (float(r.get("score", 0.0)),
                        bool(r.get("verified", False)))
        except Exception:  # noqa: BLE001
            ver[cls] = (0.0, False)
    try:
        clean_ok = bool(wd.v_clean(code, ctx, []).get("verified"))
    except Exception:  # noqa: BLE001
        clean_ok = False
    return {"label": item["label"], "margins": row, "ver": ver,
            "clean_ok": clean_ok}


def _init_eval(cfg):
    global _WD
    _WD = wd.WakingDream(registry=_REG, config=cfg)


def _answer(item):
    return _WD.answer(item["text"])["answer"]


def pool_eval(pool, reg, cfg, items):
    global _REG
    _REG = reg
    # fresh pool per config: initializer binds the config
    with Pool(4, initializer=_init_eval, initargs=(cfg,)) as p:
        return p.map(_answer, items, chunksize=4)


def main() -> None:
    global _REG, _SEATS
    from factory.run_battery import _bug_reg, _eval_bug_path
    from factory.serve import ServingHive
    from factory.bug_heldout_v2 import load_sealed

    t0 = time.time()
    hive = ServingHive.load()
    reg = _bug_reg(hive)
    _REG = reg
    member_names = list(reg)
    base_cfg = C.load_config()
    base_thresholds = {c: float(base_cfg.get("thresholds", {}).get(c, 0.0))
                       for c in CLASSES}
    seats = say_mod.seats_of(member_names)
    _SEATS = seats
    dev_items = say_dev.load_dev_pool()["items"]
    old_state = say_mod.load_state()
    old_say = old_state["say"]
    out = {"base_thresholds": base_thresholds,
           "clean_guard_in_config": bool(base_cfg.get("clean_guard")),
           "guard_in_reg": "bug-clean-guard-model" in reg,
           "n_dev": len(dev_items)}

    cache_path = Path("/tmp/e001_cache.json")
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())
        print(f"[e001] cache loaded from disk: {len(cache)} rows",
              flush=True)
    else:
        with Pool(4) as p:
            cache = p.map(_cache_row, dev_items, chunksize=4)
        cache_path.write_text(json.dumps(cache))
        print(f"[e001] cache built + persisted: {len(cache)} rows",
              flush=True)
    out["cache_wall_s"] = round(time.time() - t0, 1)

    uniform_w = {c: {n: 1.0 for n in seats[c]} for c in CLASSES}
    uniform_say = {"weights": E.shares_of(uniform_w),
                   "thresholds": dict(base_thresholds)}
    validations = {}
    real_by_name = {}
    for name, say_payload, raw_w in (
            ("uniform", uniform_say, uniform_w),
            ("old_say", old_say, old_say["weights"])):
        cfg = say_mod.merged_config(base_cfg, say_payload)
        real = pool_eval(None, reg, cfg, dev_items)
        real_by_name[name] = real
        sim = [E.sim_answer(it, raw_w, say_payload["thresholds"])[0]
               for it in cache]
        mism = sum(1 for a, b in zip(real, sim) if a != b)
        acc, rec = E.acc_recalls(real, dev_items)
        validations[name] = {"mismatches": mism, "n": len(dev_items),
                             "real_acc": round(acc, 4), "recalls": rec}
    out["sim_validation"] = validations
    print(f"[e001] sim validation: {validations}", flush=True)
    if any(v["mismatches"] for v in validations.values()):
        out["verdict"] = "SIMULATOR INVALID — fitting aborted"
        print(json.dumps(out, indent=1))
        return

    acc_inc, rec_inc = E.acc_recalls(
        pool_eval(None, reg, base_cfg, dev_items), dev_items)
    out["dev_path"] = {
        "incumbent": {"acc": round(acc_inc, 4), "recalls": rec_inc},
        "old_say": {"acc": validations["old_say"]["real_acc"],
                    "recalls": validations["old_say"]["recalls"],
                    "raw_fit_acc": old_say["fit"]["dev_acc_say"]},
        "uniform_say": {"acc": validations["uniform"]["real_acc"],
                        "recalls": validations["uniform"]["recalls"]}}
    out["dev_path"]["old_say_sim"] = E.sim_eval(
        cache, old_say["weights"], old_say["thresholds"])

    starts = {"uniform": (uniform_w, dict(base_thresholds)),
              "old_say": ({c: dict(old_say["weights"][c])
                           for c in old_say["weights"]},
                          dict(old_say["thresholds"]))}
    finals = {}
    for sname, (w0, tt) in starts.items():
        for obj in ("pure", "lex"):
            w, t, m = E.ascend(cache, seats, w0, tt, base_thresholds, obj)
            finals[f"{sname}/{obj}"] = (w, t, m)
    out["ascent_finals_sim"] = {
        k: {"acc": round(m["acc"], 4), "clean_recall": m["clean_recall"],
            "recalls": m["recalls"], "clean_blocks": m["clean_blocks"]}
        for k, (w, t, m) in finals.items()}
    print(f"[e001] ascent finals (sim): "
          f"{out['ascent_finals_sim']}", flush=True)
    champ_key = max(finals, key=lambda k: (finals[k][2]["right"],
                                           finals[k][2]["clean_right"]))
    cw, ct, cm = finals[champ_key]
    out["champion_lane"] = champ_key

    new_say = {"weights": E.shares_of(cw),
               "thresholds": {c: round(float(ct[c]), 6) for c in CLASSES},
               "seats": seats,
               "fitted_on": "factory/say_dev.json (dev pool) — "
                            "E-001 waking-in-the-loop"}
    beta = min((0.5, 0.75, 1.0, 1.5, 2.0, 3.0),
               key=lambda b: say_mod._cache_ce(cache, cw, ct, b))
    new_say["sharpness_beta"] = beta
    real_new = pool_eval(
        None, reg, say_mod.merged_config(base_cfg, new_say), dev_items)
    sim_new = [E.sim_answer(it, cw, ct)[0] for it in cache]
    acc_new, rec_new = E.acc_recalls(real_new, dev_items)
    out["dev_path"]["new_fit"] = {
        "acc": round(acc_new, 4), "recalls": rec_new,
        "sim_acc": round(cm["acc"], 4),
        "sim_real_mismatches": sum(1 for a, b in zip(real_new, sim_new)
                                   if a != b),
        "clean_blocks_sim": cm["clean_blocks"],
        "thresholds": new_say["thresholds"],
        "weights": new_say["weights"]}

    earned = acc_new > validations["old_say"]["real_acc"]
    evidence = {"dev_gate": {
        "new_fit_dev_path_acc": round(acc_new, 4),
        "old_fit_dev_path_acc": validations["old_say"]["real_acc"],
        "earned_sealed_eval": earned}}
    if earned:
        sealed_items = load_sealed()["items"]
        s_inc, s_rec_inc = _eval_bug_path(reg, base_cfg, sealed_items)
        s_new, s_rec_new = _eval_bug_path(
            reg, say_mod.merged_config(base_cfg, new_say), sealed_items)
        evidence["sealed"] = {
            "n": len(sealed_items),
            "incumbent_acc": round(s_inc, 4),
            "incumbent_recalls": s_rec_inc,
            "new_fit_acc": round(s_new, 4),
            "new_fit_recalls": s_rec_new,
            "beats_incumbent": s_new > s_inc}
    out["evidence"] = evidence

    doc = {"status": "shadow",
           "fitted_at": time.strftime("%Y-%m-%d %H:%M %Z"),
           "rule": ("E-001 candidate state. factory.serve reads "
                    "factory/learned_say.json ONLY; this file never "
                    "serves. Promotion is the standard battery "
                    "adoption step, not this file."),
           "method": ("waking-in-the-loop: coordinate ascent on "
                      "full dev serving-path accuracy, simulated "
                      "exactly from cached margins + verifier "
                      "outcomes and validated answer-for-answer "
                      "against the real WakingDream path"),
           "say": new_say,
           "fit": out["dev_path"],
           "evidence": evidence}
    tmp = E.STATE_OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    tmp.replace(E.STATE_OUT)
    out["wall_s"] = round(time.time() - t0, 1)
    out["state_file"] = str(E.STATE_OUT)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
