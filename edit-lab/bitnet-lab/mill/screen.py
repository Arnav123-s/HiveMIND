#!/usr/bin/env python3
"""screen.py — the mill's screening driver (Muse's work, Muse's side).

Invoked by mill/run-forever.sh as plain `python3 mill/screen.py` — NO required
arguments. Each invocation is one PASS:

  1. If a heavier lab process owns the lab (scale ladder, growth cycle, another
     experiment driver, a non-mill train.py), print one line and exit 0 — the
     supervisor loop retries later. The mill always yields.
  2. For a gen >= 1 champion, run its one-time CONFIRMATION first (coordinator,
     solo): champion and predecessor configs each get one 8-min seed-0 run on
     the offset confirmation windows (mill/sweep_probe.py kind "confirm"). An
     unconfirmed — or confirmation-failed — reference judges nothing.
  3. Measure the probe-scale baseline (job zero, MILL-000) FRESH at the start
     of every pass (coordinator, solo). A pass's probes are judged against
     that pass's measurement, never a stale one.
  4. Work the queue in pool order: entries not yet ledgered for this generation
     and whose flags train.py actually has. Sweep-mode entries (same-chassis
     config variants) run batched inside ONE shared-data sweep process
     (mill/sweep_probe.py — corpus loaded once); process-mode entries run as
     isolated train.py subprocesses. Each finished probe appends ONE JSON line
     to mill/ledger.jsonl with its verdict vs job zero. Deferrals (ids +
     reasons) are ledgered once per pass per generation.
  5. A probe that beats the promotion bar queues its full trial INLINE
     (mill/trials.jsonl). Trial seeds (3 x 8 min) and adoption judging run in
     the COORDINATOR, solo — never inside the probe lanes. Judging first
     applies the stale-reference guard (code/corpus fingerprint moved -> the
     champion config is re-run as a control and the reference refreshed),
     then the lab's adoption bar (>2sd AND >0.01) plus the per-seed guard
     (>= 2 of 3 seeds individually beat the reference mean). A trial that
     adopts installs a new champion (mill/champion.json, generation + 1;
     load + generation check + write inside one flock'd section) and the
     pool re-opens under the new generation next pass.
  6. Stop cleanly at the pass wall cap, when the queue drains, or when the lab
     gets busy — and exit 0. The supervisor restarts the pass; nothing is lost
     because claims and ledger lines are written as work completes.

Concurrency: mill/concurrency.json (written ONLY by mill/bench_concurrency.py
after a completed, honesty-checked study) may set {"workers": N, "omp_threads":
T}. With N > 1 the coordinator spawns N lane subprocesses of itself that claim
disjoint work through the shared claims file. Default (no file): 1 worker,
OMP/MKL = 2, matching the lab's pinning. Concurrency governs PROBES ONLY:
verdict-bearing runs (job zero, trial seeds, confirmation, control re-runs)
always run solo in the coordinator at OMP/MKL = 2.

screen.py itself imports no torch — it is safe under the system python3 the
supervisor uses; all training runs under the lab venv python.
"""
import argparse, fcntl, hashlib, json, os, re, shlex, subprocess, sys, threading, time
from pathlib import Path

MILL = Path(__file__).resolve().parent
LAB = MILL.parent
POOL = MILL / "IDEA-POOL.md"
LEDGER = MILL / "ledger.jsonl"
TRIALS = MILL / "trials.jsonl"
CHAMPION = MILL / "champion.json"
CONCURRENCY = MILL / "concurrency.json"
LOCKFILE = MILL / "mill.lock"
CLAIMS = MILL / "claims.jsonl"
VENV_PY = Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python"
PY = str(VENV_PY) if VENV_PY.exists() else sys.executable

DEFAULT_CHAMPION = {"gen": 0, "run": "--arm layered_half --rope",
                    "ref_mean": 2.8580, "ref_sd": 0.0161, "from_idea": "chassis (RESULTS-ROPE-2026-11-11)"}
PROMOTE_DELTA = 0.05      # probe must beat job zero by >= this to queue a full trial (PROMOTE.md)
NEAR_DELTA = 0.02         # within this of job zero = "flat"; between = "near"
SWEEP_BATCH = 8           # sweep jobs per shared-data process
SOLO_OMP = 2              # verdict-bearing runs (job zero, trials, confirmation, controls) always run solo at the lab's standard pinning
CONFIRM_MINUTES = 8.0     # confirmation runs use the full-trial budget, seed 0
CLAIM_STALE_S = 1800      # claims older than this are stale regardless of pid liveness (audit 6c residual)
ERROR_BENCH_AFTER = 3     # error-verdict probes re-queue; benched (ledgered) after this many errors in a generation
EXCEPTION_IDS = {"MILL-111", "MILL-112", "MILL-118", "MILL-120", "MILL-121",
                 "MILL-122", "MILL-129", "MILL-137", "MILL-138"}  # PROMOTE.md exception list: a flat probe does not kill these
HEAVY_PATTERNS = ("run_scale_ladder", "growth_cycle", "run_jepa", "run_round2",
                  "run_sweep", "scale_ladder", "python -m team")


def log(msg):
    print(f"[mill] {msg}", flush=True)


# ---------------------------------------------------------------- state files
class Locked:
    """Short flock critical sections around every shared-file mutation."""
    def __enter__(self):
        self.f = open(LOCKFILE, "a+")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self
    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def append_jsonl_locked(path, rec):
    """Append one JSON line; the caller must already hold Locked()."""
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
        f.flush()
        os.fsync(f.fileno())


def append_jsonl(path, rec):
    with Locked():
        append_jsonl_locked(path, rec)


# ---------------------------------------------------------------- fingerprints
_fp_cache = {}


def code_fingerprint():
    """sha256 over the three files whose code produces every mill number
    (train.py + screen.py + sweep_probe.py). Stamped on every ledger/trial
    line so two runs of the same idea under different code are never
    indistinguishable (audit section 4.1)."""
    if "code" not in _fp_cache:
        h = hashlib.sha256()
        for p in (LAB / "train.py", MILL / "screen.py", MILL / "sweep_probe.py"):
            h.update(p.name.encode())
            h.update(p.read_bytes())
        _fp_cache["code"] = h.hexdigest()
    return _fp_cache["code"]


def corpus_fingerprint():
    if "corpus" not in _fp_cache:
        cp = LAB / "corpus.u16"
        h = hashlib.sha256()
        with open(cp, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        size = cp.stat().st_size
        _fp_cache["corpus"] = {"corpus_sha": h.hexdigest(), "corpus_bytes": size,
                               "corpus_pieces": size // 2}
    return _fp_cache["corpus"]


def stamp(rec, workers=None, omp=None):
    """Every ledger/trial line carries the code fingerprint; run lines also
    carry the worker count and omp they were actually measured under."""
    rec["code_sha"] = code_fingerprint()
    if workers is not None:
        rec["workers"] = workers
    if omp is not None:
        rec["omp"] = omp
    return rec


def sample_sd(vals):
    """The lab's spread convention: sample sd (divide by n-1), verified
    against the RESULTS records — never population sd (audit section 3b)."""
    n = len(vals)
    if n < 2:
        return 0.0
    mean = sum(vals) / n
    return (sum((v - mean) ** 2 for v in vals) / (n - 1)) ** 0.5


def load_champion():
    if CHAMPION.exists():
        return json.loads(CHAMPION.read_text())
    return dict(DEFAULT_CHAMPION)


def load_concurrency():
    if CONCURRENCY.exists():
        c = json.loads(CONCURRENCY.read_text())
        return int(c.get("workers", 1)), int(c.get("omp_threads", 2))
    return 1, 2


# ---------------------------------------------------------------- busy check
def _pgrep(pat):
    out = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if p.isdigit()]


def _ancestors(pid):
    chain = []
    for _ in range(8):
        try:
            st = Path(f"/proc/{pid}/status").read_text()
            ppid = int(re.search(r"PPid:\s*(\d+)", st).group(1))
        except Exception:
            break
        if ppid <= 1:
            break
        chain.append(ppid)
        pid = ppid
    return chain


def _cmdline(pid):
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except Exception:
        return ""


def lab_busy():
    """Heavy non-mill lab work running? Mill-owned processes (lanes, sweep,
    bench) never count — concurrency among mill workers is governed separately."""
    if (MILL / ".bench-running").exists():
        return "concurrency bench (mill-owned, still yields)"
    for pat in HEAVY_PATTERNS:
        if _pgrep(pat):
            return pat
    for pid in _pgrep("train.py --arm"):
        if pid == os.getpid():
            continue
        chain = [pid] + _ancestors(pid)
        if any(("screen.py" in _cmdline(p) or "sweep_probe" in _cmdline(p)
                or "bench_concurrency" in _cmdline(p)) for p in chain):
            continue  # mill-owned training child
        return "train.py (non-mill)"
    return None


# ---------------------------------------------------------------- pool
def parse_pool():
    text = POOL.read_text()
    entries = []
    for block in re.findall(r"```mill\n(.*?)```", text, re.S):
        d = {}
        for line in block.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                d[k.strip()] = v.strip()
        if "id" in d and "run" in d:
            d.setdefault("mode", "process")
            entries.append(d)
    if not entries:
        raise ValueError("pool parse found no mill blocks")
    return entries


def valid_flags_and_arms():
    r = subprocess.run([PY, str(LAB / "train.py"), "--help"], capture_output=True, text=True)
    helptext = r.stdout + r.stderr
    flags = set(re.findall(r"--[a-z0-9][a-z0-9\-]*", helptext))
    m = re.search(r"\{([^}]*)\}", helptext)
    arms = set(x.strip() for x in m.group(1).split(",")) if m else set()
    return flags, arms


def validate(entry, flags, arms):
    """Return None if the entry can run today, else the deferral reason."""
    toks = shlex.split(entry["run"])
    for i, t in enumerate(toks):
        if t.startswith("--"):
            if t not in flags:
                return f"flag {t} not in train.py"
            if t == "--arm" and i + 1 < len(toks) and arms and toks[i + 1] not in arms:
                return f"arm {toks[i + 1]} not in train.py"
    return None


def ledger_state(gen):
    """Fold the ledger for one generation. Error-verdict probes are NOT done —
    they re-queue next pass — until they are explicitly benched (a `benched`
    line after ERROR_BENCH_AFTER errors). The baseline is the LAST baseline
    line for the generation (job zero is re-measured every pass)."""
    lines = read_jsonl(LEDGER)
    done, errors, benched = set(), {}, set()
    baseline = None
    for l in lines:
        if l.get("gen") != gen:
            continue
        if l.get("kind") == "baseline":
            baseline = l
        elif l.get("kind") == "probe":
            if l.get("verdict") == "error":
                errors[l["id"]] = errors.get(l["id"], 0) + 1
            else:
                done.add(l["id"])
        elif l.get("kind") == "benched":
            benched.add(l["id"])
    done |= benched
    return {"done": done, "baseline": baseline, "errors": errors, "benched": benched}


# ---------------------------------------------------------------- claims
def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def claim(key):
    """Atomically claim a work key; stale claims (dead pid, or older than
    CLAIM_STALE_S regardless of pid — a recycled pid must not make a stale
    claim look live) are reclaimable."""
    with Locked():
        claims = read_jsonl(CLAIMS) if CLAIMS.exists() else []
        now = time.time()
        live = {c["key"] for c in claims
                if pid_alive(int(c["pid"])) and now - float(c.get("ts", 0)) < CLAIM_STALE_S}
        if key in live:
            return False
        with open(CLAIMS, "a") as f:
            f.write(json.dumps({"key": key, "pid": os.getpid(), "ts": time.time()}) + "\n")
        return True


def unclaim(key):
    with Locked():
        if not CLAIMS.exists():
            return
        claims = [c for c in read_jsonl(CLAIMS)
                  if not (c["key"] == key and int(c["pid"]) == os.getpid())]
        CLAIMS.write_text("".join(json.dumps(c) + "\n" for c in claims))


# ---------------------------------------------------------------- verdicts
def verdict_for(held, baseline_held):
    if held is None:
        return "error", None
    delta = baseline_held - held
    if delta >= PROMOTE_DELTA:
        return "promote", round(delta, 4)
    if delta >= NEAR_DELTA:
        return "near", round(delta, 4)
    if delta > -NEAR_DELTA:
        return "flat", round(delta, 4)
    return "below", round(delta, 4)


def queue_trial(idea_id, run, gen):
    events = read_jsonl(TRIALS)
    for e in events:
        if e.get("idea") == idea_id and e.get("gen") == gen and e.get("event") == "queued":
            return False
    append_jsonl(TRIALS, stamp({"event": "queued", "idea": idea_id, "run": run, "gen": gen,
                                "ts": time.time()}))
    return True


def trial_state():
    """Fold the trials event log into per-(idea,gen) state."""
    state = {}
    for e in read_jsonl(TRIALS):
        k = (e.get("idea"), e.get("gen"))
        s = state.setdefault(k, {"idea": e.get("idea"), "gen": e.get("gen"), "run": e.get("run"),
                                 "seeds": {}, "status": "queued"})
        if e.get("event") == "seed":
            s["seeds"][str(e["seed"])] = e["held"]
        elif e.get("event") == "done":
            s["status"] = "done"
            s["verdict"] = e.get("verdict")
    return state


# ---------------------------------------------------------------- execution
def child_env(omp):
    return {"OMP_NUM_THREADS": str(omp), "MKL_NUM_THREADS": str(omp),
            "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": os.environ.get("HOME", "/home/hatch"),
            "LANG": "C.UTF-8"}


def tag_for(idea_id):
    return "mill" + idea_id.replace("MILL-", "").lower()


def run_sweep_batch(jobs, omp, deadline):
    """Run a batch of sweep-mode jobs in ONE shared-data process; ledger each
    RESULT as it streams back. Returns {id: record} for completed jobs."""
    jobs_file = MILL / f".sweep-jobs-{os.getpid()}-{time.time_ns()}.jsonl"
    with open(jobs_file, "w") as f:
        for j in jobs:
            f.write(json.dumps(j) + "\n")
    results = {}
    killer = None
    try:
        p = subprocess.Popen([PY, str(MILL / "sweep_probe.py"), str(jobs_file)],
                             stdout=subprocess.PIPE, text=True, env=child_env(omp), cwd=LAB)
        # the deadline is real: a hung sweep batch is killed at it, not believed in
        killer = threading.Timer(max(1.0, deadline - time.time()), p.kill)
        killer.daemon = True
        killer.start()
        current = None
        for line in p.stdout:
            if line.startswith("MILLJOB "):
                current = line.split()[1]
            elif line.startswith("RESULT ") and current:
                results[current] = json.loads(line[len("RESULT "):])
                current = None
            elif line.startswith("MILLERR ") and current:
                results[current] = {"error": line.strip()}
                current = None
            elif line.startswith("MILLSTOP"):
                break
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
    finally:
        if killer is not None:
            killer.cancel()
        jobs_file.unlink(missing_ok=True)
    return results


def run_subprocess_probe(entry, minutes, omp):
    argv = [PY, str(LAB / "train.py")] + shlex.split(entry["run"]) + \
           ["--seed", "0", "--minutes", str(minutes), "--tag", tag_for(entry["id"])]
    t0 = time.time()
    r = subprocess.run(argv, capture_output=True, text=True, env=child_env(omp), cwd=LAB,
                       timeout=int(minutes * 60) + 600)
    for line in r.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):])
    return {"error": (r.stderr or r.stdout)[-300:], "wall_s": round(time.time() - t0, 1)}


def ledger_probe(entry, rec, gen, baseline_held, minutes, workers, omp):
    held = rec.get("held_final") if rec else None
    verdict, delta = verdict_for(held, baseline_held) if baseline_held is not None else ("error", None)
    line = {"id": entry["id"], "gen": gen, "kind": "probe", "run": entry["run"],
            "mode": entry["mode"], "seed": (rec or {}).get("seed", 0), "held": held,
            "steps": rec.get("steps") if rec else None,
            "wall_s": rec.get("wall_s") if rec else None, "probe_minutes": minutes,
            "delta_vs_baseline": delta, "verdict": verdict, "ts": time.time()}
    if entry["id"] in EXCEPTION_IDS:
        line["exception"] = True  # PROMOTE.md exception list: flat does not kill these
    append_jsonl(LEDGER, stamp(line, workers, omp))
    if verdict == "error":
        # error probes are NOT done — they re-queue. After ERROR_BENCH_AFTER
        # error verdicts in one generation, bench the idea explicitly instead
        # of letting it retry forever (audit section 4.4).
        lines = read_jsonl(LEDGER)
        attempts = sum(1 for l in lines if l.get("kind") == "probe"
                       and l.get("verdict") == "error" and l.get("id") == entry["id"]
                       and l.get("gen") == gen)
        already = any(l.get("kind") == "benched" and l.get("id") == entry["id"]
                      and l.get("gen") == gen for l in lines)
        if attempts >= ERROR_BENCH_AFTER and not already:
            append_jsonl(LEDGER, stamp({"id": entry["id"], "gen": gen, "kind": "benched",
                                        "attempts": attempts,
                                        "reason": f"{attempts} error verdicts this generation — benched until a human looks",
                                        "ts": time.time()}, workers, omp))
            log(f"{entry['id']}: BENCHED after {attempts} error verdicts (gen {gen})")
    return line


def measure_baseline(champ, omp, probe_minutes):
    """Job zero: the champion config at probe budget, via the sweep runner."""
    job = {"id": "MILL-000", "run": champ["run"], "minutes": probe_minutes,
           "seed": 0, "tag": "mill000"}
    res = run_sweep_batch([job], omp, time.time() + probe_minutes * 60 + 300)
    rec = res.get("MILL-000")
    if not rec or "held_final" not in rec:
        return None
    line = {"id": "MILL-000", "gen": champ["gen"], "kind": "baseline", "run": champ["run"],
            "mode": "sweep", "seed": 0, "held": rec["held_final"], "steps": rec.get("steps"),
            "wall_s": rec.get("wall_s"), "probe_minutes": probe_minutes,
            "verdict": "baseline", "ts": time.time()}
    line.update(corpus_fingerprint())
    append_jsonl(LEDGER, stamp(line, workers=1, omp=omp))
    return line


# ---------------------------------------------------------------- lanes (PROBES ONLY — verdict-bearing runs live in the coordinator)
def lane_work(lane_id, omp, probe_minutes, deadline, flags, arms, workers):
    champ = load_champion()
    gen = champ["gen"]
    entries = parse_pool()
    st = ledger_state(gen)
    done, baseline = st["done"], st["baseline"]
    if baseline is None:
        log(f"lane {lane_id}: no baseline for gen {gen}; coordinator measures it — waiting")
        for _ in range(120):
            time.sleep(5)
            st = ledger_state(gen)
            baseline = st["baseline"]
            if baseline is not None:
                break
        if baseline is None:
            return {"probes": 0, "note": "baseline never landed"}
        done = st["done"]
    baseline_held = baseline["held"]
    runnable, deferred = [], 0
    for e in entries:
        if e["id"] == "MILL-000" or e["id"] in done:
            continue
        if validate(e, flags, arms) is not None:
            deferred += 1
            continue
        runnable.append(e)
    probes = 0
    # sweep-mode entries first (batched, shared data), then process-mode entries
    sweep_q = [e for e in runnable if e["mode"] == "sweep"]
    while sweep_q and time.time() < deadline:
        if lab_busy():
            log(f"lane {lane_id}: lab busy — stopping pass early")
            break
        batch = []
        for e in list(sweep_q):
            if len(batch) >= SWEEP_BATCH:
                break
            if claim(f"probe:{e['id']}:g{gen}"):
                batch.append(e)
                sweep_q.remove(e)
        if not batch:
            break
        jobs = [{"id": e["id"], "run": e["run"], "minutes": probe_minutes, "seed": 0,
                 "tag": tag_for(e["id"])} for e in batch]
        results = run_sweep_batch(jobs, omp, deadline)
        for e in batch:
            rec = results.get(e["id"])
            line = ledger_probe(e, rec, gen, baseline_held, probe_minutes, workers, omp) if rec else \
                {"id": e["id"], "verdict": "error"}
            if rec:
                probes += 1
                log(f"lane {lane_id}: {e['id']} held={line['held']} verdict={line['verdict']}")
                if line["verdict"] == "promote" and queue_trial(e["id"], e["run"], gen):
                    log(f"lane {lane_id}: {e['id']} PROMOTED — full trial queued inline")
            unclaim(f"probe:{e['id']}:g{gen}")
    proc_q = [e for e in runnable if e["mode"] != "sweep"]
    for e in proc_q:
        if time.time() >= deadline:
            break
        if lab_busy():
            log(f"lane {lane_id}: lab busy — stopping pass early")
            break
        if not claim(f"probe:{e['id']}:g{gen}"):
            continue
        try:
            rec = run_subprocess_probe(e, probe_minutes, omp)
            line = ledger_probe(e, rec, gen, baseline_held, probe_minutes, workers, omp)
            probes += 1
            log(f"lane {lane_id}: {e['id']} held={line['held']} verdict={line['verdict']}")
            if line["verdict"] == "promote" and queue_trial(e["id"], e["run"], gen):
                log(f"lane {lane_id}: {e['id']} PROMOTED — full trial queued inline")
        finally:
            unclaim(f"probe:{e['id']}:g{gen}")
    # Trial seeds and adoption judging are verdict-bearing: they run solo in
    # the coordinator (run_trial_seeds / judge_trials below), never in a lane.
    return {"probes": probes, "deferred": deferred}


# ---------------------------------------------------------------- coordinator-only verdict-bearing work (always solo)
def run_confirmation(champ, deadline):
    """Fix for audit 1b: one confirmation evaluation per gen >= 1 champion,
    on the confirmation windows (every-40th blocks offset by 20 — disjoint
    from the held set, never used for probes or verdicts). Champion and
    predecessor configs each get one 8-min seed-0 run whose training excludes
    BOTH window sets (sweep kind "confirm"); the champion's reference may not
    judge further work until its config does not lose to the predecessor
    there. Returns True when the gate is satisfied or not applicable."""
    gen = champ["gen"]
    conf = champ.get("confirmation") or {}
    if conf.get("gen") == gen and conf.get("status") == "confirmed":
        return True
    if conf.get("gen") == gen and conf.get("status") == "failed":
        log(f"gen {gen} champion FAILED its confirmation earlier — its reference "
            f"may not judge further work; stopping pass (see ledger kind=confirmation)")
        return False
    prev_run = champ.get("prev_run")
    if not prev_run:
        log(f"gen {gen} champion has no predecessor config recorded — confirmation not applicable")
        return True
    if time.time() + 2 * CONFIRM_MINUTES * 60 + 120 > deadline:
        log("not enough pass budget for the confirmation runs — deferring to next pass")
        return False
    log(f"confirmation for gen {gen}: champion vs predecessor on the offset window set "
        f"(2 x {CONFIRM_MINUTES:.0f} min, solo)")
    jobs = [{"id": "MILL-000C", "run": champ["run"], "minutes": CONFIRM_MINUTES, "seed": 0,
             "tag": "millconfirm", "kind": "confirm"},
            {"id": "MILL-000P", "run": prev_run, "minutes": CONFIRM_MINUTES, "seed": 0,
             "tag": "millconfirmp", "kind": "confirm"}]
    res = run_sweep_batch(jobs, SOLO_OMP, deadline)
    got = {}
    for jid, role, run in (("MILL-000C", "champion", champ["run"]),
                           ("MILL-000P", "predecessor", prev_run)):
        rec = res.get(jid) or {}
        append_jsonl(LEDGER, stamp({"id": jid, "gen": gen, "kind": "confirmation",
                                    "role": role, "run": run, "seed": 0,
                                    "confirm_held": rec.get("confirm_final"),
                                    "held": rec.get("held_final"),
                                    "steps": rec.get("steps"), "wall_s": rec.get("wall_s"),
                                    "ts": time.time()}, workers=1, omp=SOLO_OMP))
        got[role] = rec.get("confirm_final")
    if got.get("champion") is None or got.get("predecessor") is None:
        log("confirmation runs did not both complete (preempted?) — will retry next pass")
        return False
    ok = got["champion"] <= got["predecessor"]
    status = "confirmed" if ok else "failed"
    with Locked():
        cur = load_champion()
        if cur.get("gen") == gen:
            cur["confirmation"] = {"gen": gen, "status": status,
                                   "champion_confirm": got["champion"],
                                   "predecessor_confirm": got["predecessor"],
                                   "ts": time.time()}
            CHAMPION.write_text(json.dumps(cur, indent=2))
    log(f"confirmation gen {gen}: champion {got['champion']} vs predecessor "
        f"{got['predecessor']} on offset windows -> {status.upper()}"
        + ("" if ok else " — selection-overfitting signature; reference frozen, reported in the ledger"))
    return ok


def ledger_deferrals(gen, entries, done, flags, arms, workers):
    """One kind="deferrals" ledger line per pass per generation (ids +
    reasons) — the ledger is the complete record, skips included (audit
    section 4.3). Re-ledgers only when the deferral set changes."""
    items = []
    for e in entries:
        if e["id"] == "MILL-000" or e["id"] in done:
            continue
        why = validate(e, flags, arms)
        if why is not None:
            items.append({"id": e["id"], "reason": why})
    prev = None
    for l in read_jsonl(LEDGER):
        if l.get("kind") == "deferrals" and l.get("gen") == gen:
            prev = l
    if prev is not None and prev.get("items") == items:
        return 0
    append_jsonl(LEDGER, stamp({"kind": "deferrals", "gen": gen, "count": len(items),
                                "items": items, "ts": time.time()}, workers=workers))
    return len(items)


def _train_py_result(argv, omp, timeout):
    r = subprocess.run(argv, capture_output=True, text=True, env=child_env(omp),
                       cwd=LAB, timeout=timeout)
    for ln in r.stdout.splitlines():
        if ln.startswith("RESULT "):
            return json.loads(ln[len("RESULT "):])
    return None


def run_trial_seeds(gen, deadline):
    """Trial seeds are verdict-bearing: they run here, in the coordinator,
    one at a time (solo, OMP/MKL = SOLO_OMP), never inside the probe lanes
    (audit sections 2c/6b, fix option 1)."""
    trials = trial_state()
    for (idea, tgen), s in sorted(trials.items()):
        if s["status"] == "done" or tgen != gen:
            continue
        for seed in (0, 1, 2):
            if str(seed) in s["seeds"]:
                continue
            if time.time() + 9 * 60 > deadline:
                log(f"trial {idea}: wall cap before seed {seed} — remaining seeds next pass")
                return
            if lab_busy():
                log(f"trial {idea}: lab busy before seed {seed} — remaining seeds next pass")
                return
            key = f"trial:{idea}:g{tgen}:s{seed}"
            if not claim(key):
                continue
            try:
                argv = [PY, str(LAB / "train.py")] + shlex.split(s["run"]) + \
                       ["--seed", str(seed), "--minutes", "8", "--tag", tag_for(idea) + "trial"]
                rec = _train_py_result(argv, SOLO_OMP, 8 * 60 + 600)
                if rec is None:
                    log(f"trial seed failed for {idea} s{seed} — will retry next pass")
                    continue
                append_jsonl(TRIALS, stamp({"event": "seed", "idea": idea, "gen": tgen,
                                            "run": s["run"], "seed": seed,
                                            "held": rec["held_final"],
                                            "steps": rec.get("steps"),
                                            "wall_s": rec.get("wall_s"),
                                            "ts": time.time()}, workers=1, omp=SOLO_OMP))
                s["seeds"][str(seed)] = rec["held_final"]
                log(f"trial {idea} seed {seed} held={rec['held_final']} (solo)")
            finally:
                unclaim(key)


def judge_trials(gen, deadline):
    """Adoption judging, coordinator-only. Stale-reference guard first: if
    the code or corpus fingerprint moved since the champion's reference was
    established, the champion config is re-run as a control (same 3 seeds,
    solo) and the reference refreshed before judging (PROMOTE.md). Then the
    lab's bar (>2sd AND >0.01, sample sd) plus the per-seed guard (>= 2 of
    3 seeds individually beat the reference mean). The install — load +
    generation check + write — happens inside ONE Locked section; a trial
    whose generation has moved is ledgered `superseded`, never silently
    overwritten (audit section 6c)."""
    trials = trial_state()
    for (idea, tgen), s in sorted(trials.items()):
        if s["status"] == "done" or tgen != gen or len(s.get("seeds", {})) < 3:
            continue
        champ = load_champion()
        if champ["gen"] != gen:
            log(f"trial {idea}: champion is gen {champ['gen']}, trial is gen {tgen} — judging deferred")
            return
        cur_code = code_fingerprint()
        cur_corpus = corpus_fingerprint()
        stale = (champ.get("code_sha") is not None and champ["code_sha"] != cur_code) or \
                (champ.get("corpus_sha") is not None
                 and champ["corpus_sha"] != cur_corpus["corpus_sha"])
        if stale:
            if time.time() + 3 * 8 * 60 + 120 > deadline:
                log(f"trial {idea}: reference stale but no budget for the control re-run — deferring")
                return
            log(f"trial {idea}: champion reference is stale (code/corpus fingerprint moved) "
                f"— control re-run of '{champ['run']}' (3 seeds, solo)")
            vals = []
            for seed in (0, 1, 2):
                argv = [PY, str(LAB / "train.py")] + shlex.split(champ["run"]) + \
                       ["--seed", str(seed), "--minutes", "8", "--tag", "millctrl"]
                rec = _train_py_result(argv, SOLO_OMP, 8 * 60 + 600)
                if rec is None:
                    log(f"trial {idea}: control re-run seed {seed} failed — deferring judging")
                    return
                vals.append(rec["held_final"])
            cmean = sum(vals) / 3
            csd = sample_sd(vals)
            with Locked():
                cur = load_champion()
                if cur.get("gen") == gen:
                    cur["ref_mean"] = round(cmean, 4)
                    cur["ref_sd"] = round(csd, 4)
                    cur["code_sha"] = cur_code
                    cur["corpus_sha"] = cur_corpus["corpus_sha"]
                    cur["corpus_pieces"] = cur_corpus["corpus_pieces"]
                    CHAMPION.write_text(json.dumps(cur, indent=2))
            append_jsonl(LEDGER, stamp({"id": "MILL-000", "gen": gen, "kind": "control",
                                        "reason": "stale champion reference (fingerprint mismatch)",
                                        "run": champ["run"], "seed": [0, 1, 2], "helds": vals,
                                        "ref_mean": round(cmean, 4), "ref_sd": round(csd, 4),
                                        "ts": time.time()}, workers=1, omp=SOLO_OMP))
            log(f"trial {idea}: control re-run -> reference now {cmean:.4f} ± {csd:.4f} (sample sd)")
            champ = load_champion()
        vals = [s["seeds"][str(i)] for i in (0, 1, 2)]
        mean = sum(vals) / 3
        sd = sample_sd(vals)
        ref_mean, ref_sd = champ["ref_mean"], champ["ref_sd"]
        wins = sum(1 for v in vals if v < ref_mean)
        adopt = (mean < ref_mean - 2 * ref_sd and mean < ref_mean - 0.01 and wins >= 2)
        verdict = "adopt" if adopt else "reject"
        with Locked():
            champ_now = load_champion()
            if champ_now["gen"] != tgen:
                append_jsonl_locked(TRIALS, stamp({"event": "done", "idea": idea, "gen": tgen,
                                                   "run": s["run"], "held_mean": round(mean, 4),
                                                   "held_sd": round(sd, 4), "seed_wins": wins,
                                                   "verdict": "superseded", "ts": time.time()}))
                append_jsonl_locked(LEDGER, stamp({"id": idea, "gen": tgen, "kind": "trial",
                                                   "run": s["run"], "held_mean": round(mean, 4),
                                                   "held_sd": round(sd, 4), "seed_wins": wins,
                                                   "verdict": "superseded", "ts": time.time()}))
                log(f"trial {idea}: champion generation moved during judging — ledgered as superseded")
                return
            append_jsonl_locked(TRIALS, stamp({"event": "done", "idea": idea, "gen": tgen,
                                               "run": s["run"], "held_mean": round(mean, 4),
                                               "held_sd": round(sd, 4), "seed_wins": wins,
                                               "ref_mean": ref_mean, "ref_sd": ref_sd,
                                               "verdict": verdict, "ts": time.time()}))
            append_jsonl_locked(LEDGER, stamp({"id": idea, "gen": tgen, "kind": "trial",
                                               "run": s["run"], "held_mean": round(mean, 4),
                                               "held_sd": round(sd, 4), "seed_wins": wins,
                                               "ref_mean": ref_mean, "verdict": verdict,
                                               "ts": time.time()}))
            if adopt:
                new = {"gen": tgen + 1, "run": s["run"], "ref_mean": round(mean, 4),
                       "ref_sd": round(sd, 4), "from_idea": idea,
                       "prev_run": champ_now["run"],
                       "code_sha": cur_code, "corpus_sha": cur_corpus["corpus_sha"],
                       "corpus_pieces": cur_corpus["corpus_pieces"],
                       "confirmation": {"gen": tgen + 1, "status": "pending"}}
                CHAMPION.write_text(json.dumps(new, indent=2))
        log(f"trial {idea} DONE mean={mean:.4f} sd={sd:.4f} (sample) seed_wins={wins}/3 "
            f"vs ref {ref_mean:.4f} -> {verdict.upper()}")
        if adopt:
            log(f"NEW CHAMPION gen {tgen + 1} from {idea} ({mean:.4f} ± {sd:.4f}); "
                f"its confirmation runs next pass, before its reference judges anything")
            return


# ---------------------------------------------------------------- coordinator
def dry_run():
    champ = load_champion()
    entries = parse_pool()
    flags, arms = valid_flags_and_arms()
    st = ledger_state(champ["gen"])
    done, baseline = st["done"], st["baseline"]
    runnable, deferred = [], {}
    for e in entries:
        if e["id"] == "MILL-000":
            continue
        why = validate(e, flags, arms)
        if why is None:
            runnable.append(e)
        else:
            deferred.setdefault(why.split(" not in")[0], 0)
            deferred[why.split(" not in")[0]] += 1
    workers, omp = load_concurrency()
    print(f"[mill] DRY RUN — no writes, no training")
    print(f"[mill] champion: gen {champ['gen']} run='{champ['run']}' ref {champ['ref_mean']} ± {champ['ref_sd']}")
    conf = champ.get("confirmation") or {}
    print(f"[mill] confirmation (gen >= 1 gate): "
          + (f"status={conf.get('status')}" if champ["gen"] >= 1 else "not applicable at gen 0"))
    print(f"[mill] pool: {len(entries)} entries; screened this gen: {len(done)} "
          f"(+{len(st['benched'])} benched, {sum(st['errors'].values())} error lines pending re-queue); "
          f"runnable now: {len(runnable)}; deferred: {sum(deferred.values())}")
    for why, n in sorted(deferred.items()):
        print(f"[mill]   deferred x{n}: {why} not in train.py")
    print(f"[mill] baseline for gen {champ['gen']}: "
          + (f"last pass held {baseline['held']} (ledgered) — every pass re-measures job zero fresh"
             if baseline else "none yet — every pass starts by measuring job zero fresh"))
    print(f"[mill] job zero dry check: sweep batch of 1 -> {PY} mill/sweep_probe.py "
          f"(job: id=MILL-000 run='{champ['run']}' minutes=1.25 seed=0 tag=mill000)")
    print(f"[mill] first runnable: {[e['id'] for e in runnable[:10]]}")
    print(f"[mill] concurrency setting: workers={workers} omp={omp} "
          f"({'from concurrency.json' if CONCURRENCY.exists() else 'default — no completed concurrency study'})"
          f" — probes only; job zero / trials / confirmation / controls always solo at omp={SOLO_OMP}")
    b = lab_busy()
    print(f"[mill] lab: {'BUSY (' + b + ') — a real pass would yield and exit 0' if b else 'free'}")
    trials = trial_state()
    open_trials = [k for k, s in trials.items() if s["status"] != "done"]
    print(f"[mill] trials: {len(trials)} total, {len(open_trials)} open")
    return 0


def main():
    ap = argparse.ArgumentParser(description="the mill's screening driver (no required args)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lane", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--probe-minutes", type=float, default=1.25)
    ap.add_argument("--max-wall-min", type=float, default=45.0)
    a = ap.parse_args()
    if a.dry_run:
        return dry_run()
    if a.lane is not None:  # lane mode: env carries flags/arms + deadline
        flags = set(json.loads(os.environ["MILL_FLAGS"]))
        arms = set(json.loads(os.environ["MILL_ARMS"]))
        deadline = float(os.environ["MILL_DEADLINE"])
        workers, omp = load_concurrency()
        res = lane_work(a.lane, omp, a.probe_minutes, deadline, flags, arms, workers)
        log(f"lane {a.lane} done: {res}")
        return 0
    # coordinator
    b = lab_busy()
    if b:
        log(f"lab busy ({b}) — yielding, exit 0")
        return 0
    champ = load_champion()
    gen = champ["gen"]
    workers, omp = load_concurrency()
    deadline = time.time() + a.max_wall_min * 60
    # confirmation gate: a gen >= 1 champion's reference judges nothing until
    # its one confirmation evaluation on the offset windows has run and passed
    if gen >= 1 and not run_confirmation(champ, deadline):
        return 0
    champ = load_champion()
    gen = champ["gen"]
    # job zero: re-measured FRESH at the start of every pass (solo), and this
    # pass's probes are judged against this measurement only
    log(f"measuring job zero for champion gen {gen} ({champ['run']}) — fresh every pass")
    line = measure_baseline(champ, SOLO_OMP, a.probe_minutes)
    if line is None:
        log("job zero failed or was preempted — ending pass, exit 0")
        return 0
    log(f"job zero: held {line['held']} in {line['steps']} steps — this pass's verdicts vs this")
    flags, arms = valid_flags_and_arms()
    entries = parse_pool()
    st = ledger_state(gen)
    nd = ledger_deferrals(gen, entries, st["done"], flags, arms, workers)
    if nd:
        log(f"deferrals ledgered: {nd} entries cannot run yet (flags/arms not in train.py)")
    # verdict-bearing trial work runs BEFORE probes, solo, in the coordinator
    run_trial_seeds(gen, deadline)
    judge_trials(gen, deadline)
    if load_champion()["gen"] != gen:
        log("champion changed this pass — the pool re-opens under the new generation next pass")
        return 0
    if workers <= 1:
        res = lane_work(0, omp, a.probe_minutes, deadline, flags, arms, workers)
        log(f"pass done: {res}")
        return 0
    env = dict(os.environ)
    env["MILL_FLAGS"] = json.dumps(sorted(flags))
    env["MILL_ARMS"] = json.dumps(sorted(arms))
    env["MILL_DEADLINE"] = str(deadline)
    lanes = [subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--lane", str(k),
                               "--probe-minutes", str(a.probe_minutes)],
                              env=env) for k in range(workers)]
    for p in lanes:
        p.wait()
    log(f"pass done: {workers} lanes finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
