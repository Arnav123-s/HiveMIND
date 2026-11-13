# COMPUTE-ASHP — can ashp usefully run Muse's side's BitNet lab jobs?

> Muse's work — written by Muse, on Muse's side. Measured on ashp 2026-11-12, ~20:08–20:29 PT.
> Scratch + raw logs on ashp: `D:\muse\compute-bench\` (train.py copy, corpus.u16, bench_*.ps1 / bench_*.log, timings.txt, runs.jsonl, train_gpu_bench.py).
> Fable's side was not touched.

## Verdict (one line)

**GO for offloading MILL PROBES to ashp's CPU — measured ~3× the VM's speed (75 steps inside the 75s probe budget vs ~24–26 for the VM), temps nowhere near limits, zero installs needed. Ladder-class long runs: NO-GO for now (sustained thermals untested). GPU: much faster again (~8 steps/s), but needs a code change to train.py first.**

## 1. Inventory (as found, nothing installed)

| Item | Found |
|---|---|
| Machine | HP laptop "ashp" (100.66.2.3), Win11, i7-10870H (8 cores / 16 threads), 31.8 GB RAM |
| GPU | GeForce GTX 1650 Ti, 4 GB, driver 592.82 / CUDA 13.1. **Power cap: min = default = max = 50 W** — `nvidia-smi -pl 60` was attempted and rejected ("valid range 1.00–50.00 W"). This mobile part cannot exceed 50 W, so the house 60 W limit target is already satisfied by hardware. |
| System python | Python 3.12.7 (muse profile) — **no torch** |
| `D:\muse\tools\agentenv` | numpy 2.5.4 — **no torch** |
| `D:\muse\work\edit-lab\venv` (pre-existing) | **torch 2.15.0+cpu**, numpy 2.5.4 — used for all CPU benches |
| `D:\muse\work\edit-lab\venv-gpu` (pre-existing) | **torch 2.14.1+cu130**, `torch.cuda.is_available() = True`, device = GTX 1650 Ti — used for the GPU burst |
| Box state on arrival | CPU ~4.5% idle, **no python/heavy jobs running**, GPU 42–43 °C idle, 9 MiB GPU mem (a desktop app only). Nothing had to be waited for or avoided; Grok's house work was not running heavy during the window. One heavy job at a time was kept throughout. |

No downloads, no installs: both torches already existed in Muse's own area.

## 2. CPU training throughput (lab's real shapes, lab's train.py unmodified)

Steps-based micro-runs, `--steps 12`, seed 0. "Loop" = train.py's own `wall_s` (training loop only); "total" = full process (torch import + held-out eval before and after ≈ 10–12 s fixed overhead).

| Shape | Threads (OMP/MKL) | Loop s / 12 steps | steps/s | s/step | Total process |
|---|---|---|---|---|---|
| Champion (`--arm layered_half --rope`, dim 192, 2 layers, 884,736 ternary wts) | 4 | 16.5 | **0.73** | 1.38 | 28.3 s |
| Champion | **8** | 12.7 | **0.94** | **1.06** | 23.4 s |
| 2M ladder (`--arm layered --rope --dim 288 --layers-n 2`, 1,990,656 ternary wts) | 4 | 27.1 | **0.44** | 2.26 | 42.0 s |
| 2M ladder | **8** | 19.6 | **0.61** | **1.63** | 32.1 s |

**Full probe check** (the real mill configuration, champion shape, 8 threads, `--minutes 1.25`): **75 steps completed inside the 75 s budget** (loop wall 75.9 s), **86.6 s end-to-end**, held loss 8.3138 → 3.3491, sustained rate ≈ 0.99 steps/s — no slowdown over the full probe vs the 12-step micro-runs (no throttling signature).

Sanity: seed-0 runs at 4 threads, 8 threads, and on GPU produced identical held losses (8.3138 → 5.7617 at 12 steps) — same math on every path.

### vs the VM

- 2M shape, VM solo (recorded, given): 5.14 s/step → **ashp is 2.3× (4 thr) / 3.1× (8 thr) faster per step**.
- Champion shape, VM (lab `runs.jsonl`, three 8-min `layered_half_rope` runs): 2.84–3.13 s/step → the VM fits roughly **24–26 steps** in a 75 s probe; ashp fits **75**. Ratio ≈ **2.7–3.0×**, consistent with the clean 2M anchor. (Caveat: those VM records may themselves have run contended; if anything that makes the true ratio larger, and the direction is not in doubt.)

## 3. GPU

Stock `train.py` has **no device handling** (everything is constructed on CPU), so the GPU numbers come from a bench-only copy (`train_gpu_bench.py` in the scratch dir) with exactly three `.cuda()` moves (model, held windows, batches). Champion shape, `venv-gpu` torch:

| Run | Loop s | steps/s | s/step |
|---|---|---|---|
| 12 steps | 1.9 | **6.3** | 0.16 |
| 48 steps | 5.8 | **8.3** | 0.12 |

≈ **7–9× ashp's own CPU rate**, ~20×+ the VM's champion rate. Live mid-burst reading: **57 °C, 43.4 W, 74% util, 925 MiB of 4096 MiB** — the champion shape fits in 4 GB with huge headroom; the 2M shape at batch 32 / CTX 256 should also fit, larger ladder rungs are unchecked.

**GPU verdict: viable and the fastest option here, but it is a code change, not a config change.** What would be needed: a real `--device` path in train.py (upstreamed and re-verified against CPU records the way this probe verified seed-0 equality), plus FP32-trainer memory checks per rung. Until that exists, GPU is not a drop-in for mill jobs. Nothing about the 1650 Ti itself (4 GB, 50 W cap) blocks the probe/champion class.

## 4. Thermals (house law followed)

- tempwatch logging was ON for every run: the house `D:\muse\tools\tempwatch.ps1` was already running at 60 s cadence into `D:\muse\logs\temps.log` before I arrived and logged throughout; I additionally polled `nvidia-smi` every few seconds during each burst and between bursts.
- Start gate: every burst started at GPU ≤ 51 °C (idle 42–43 °C). Power-limit step: attempted, hardware-capped at 50 W (see §1).
- **Peak temps observed: 51 °C during the longest CPU burst (75 s probe, shared-heatpipe soak), 57 °C during the GPU burst.** tempwatch's 60 s samples peaked at 53 °C in the window. Peaks are 30+ °C below the 88–90 °C abort line; every burst cooled back to ≤ 50 °C within about a minute. Abort was never approached.
- **Honest gap — no true CPU temperature sensor is available on this box.** The WMI ACPI thermal zones return nonsense (27.9 °C / 10.1 °C). CPU heat is therefore inferred from the GPU sensor (shared heatpipe), CPU load % (tempwatch), and the absence of any rate fall-off across runs. A second, faster tempwatch could not be detached from the SSH session (Start-Process died with the session; WMI process-create returned access-denied in the non-elevated shell). This inference is good enough for 90-second probes; it is **not** good enough to clear sustained multi-hour loads on a laptop with physically broken heat fins.

## 5. Verdict & caveats

**Mill probes → GO (CPU, 8 threads).** A probe is a 75 s-budget champion-shape run: ashp does 75 steps per probe where the VM does ~24–26, end-to-end 86.6 s including all overhead, at ~3× the VM's per-step speed on the cross-checked 2M shape too. Every probe moved to ashp is VM time handed back to the contended work (including the serving hive's growth, which stays on the VM by settled rule and is out of scope here).

Operational caveats:

- **Duty cycle supported by evidence:** back-to-back ~90 s probes with tempwatch gating — start a probe only if the GPU sensor reads ≤ 65 °C, hold/abort at 80 °C on that sensor (a deliberately stricter line than the house 88–90 °C, because the sensor is a proxy for the un-sensed CPU). Nine minutes of bursts inside ~20 minutes never pushed past 57 °C. **Sustained ladder-class runs (25 min+) are NOT cleared**: run one monitored 30-min trial before any ladder offload decision.
- **Shared box:** ashp also carries Grok's house work and dot's app processes. It was quiet this evening; a runner must check for a busy box (CPU load / a running python) and defer rather than stack a second heavy job.
- **SSH quirk that shapes any runner:** sessions through the proxy forwarder drop at ~23 s, but detached remote processes survive the drop. So jobs must be launched fire-and-forget (a .ps1 that writes its own log/timing/result files) and completion detected by polling for those files — never by holding a session open.
- 8 threads beat 4 by ~30–40% on both shapes; 16 (all logical) was not tried — 8 physical cores is the sensible setting and leaves the box responsive for house work.

**What a runner would look like (paragraph, not built):** the VM-side mill drops a job file (arm/args/seed, probe-class only) into the lab's `compute/queue/`; a small scheduled task in the muse account on ashp polls a synced copy of that queue, claims a job by renaming it, checks the gates (tempwatch sensor ≤ 65 °C, no other python running, one-job lock file), runs it with the CPU venv at OMP/MKL = 8 via a fire-and-forget script, and writes the RESULT JSON plus the runs.jsonl line back to a results folder; the VM mill collects results by pulling those files over the same SSH/scp path and merges them into its own records, with the job's origin marked as ashp so VM/ashp numbers never mix silently. Estimated build: small — the bench scripts in `D:\muse\compute-bench\` are already 80% of the ashp half.
