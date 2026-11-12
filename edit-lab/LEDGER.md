# Rejected-edit repair — optimizer ledger

Machine: 7 GB RAM, 4 cores, CPU only. Base model Qwen/Qwen3-1.7B (bf16).
Harness: training/observe.py, unmodified, run in a copied tree
(~/workspace/edit-lab/tree) so the repo tree stays byte-identical.
Greedy decoding (temperature 0) — scores reproducible.

Published anchors (training/reports/base.json / trained.json):
- coordinator: base 0.942 (n=14), rejected edit 0.791
- researcher_plan: base 0.950 (n=10), rejected edit 0.975
- researcher_extract: base 0.767 (n=5), rejected edit 0.567

Selection rule: a candidate WINS only if it beats the *reproduced* base on
the same eval; for researcher, extract must beat base extract AND plan must
not fall below base plan.

Setup note: the original setup process died mid-install (venv left bare,
huggingface_hub missing). Reinstalled manually: torch (CPU index),
transformers, peft, safetensors, huggingface_hub, accelerate.

## Runs

(each run appended below: date, config, adapter source, scores, decision)

### 2026-11-08 anchors (this machine; harness unmodified, copied tree)
- base coordinator (--no-adapters): **0.930** (n=14, 3208 s)
  vs published 0.942 → harness validated; operative bar = 0.930.
  Per-case: 0.50 1.00 1.00 1.00 0.83 1.00 1.00 1.00 (first 8; full set in
  results JSON) — the 0.50 case is the HF-models task.
- rejected coordinator, original adapter at full strength (s=1.0):
  **0.791** (n=14, 2276 s) — EXACT match with the published 0.791.
  Per-case: 0.83 0.83 0.67 0.83 0.67 0.83 0.83 0.67 0.57 0.83 ...
  Pattern: the edit never reaches 1.00; it drops ~0.17 (one of six
  checks) on nearly every case — a single systematic defect signature,
  consistent with the plan-size check failing on 2-step plans.
  Operative anchors: base 0.930, rejected 0.791 (gap = 0.139).
- base researcher (--no-adapters, suites researcher_plan+researcher_extract):
  plan **1.000** (n=10, 441 s) vs published 0.950 — base is perfect at
  planning here; researcher candidates must not fall below 1.000 plan.
  extract **0.733** (n=5, 2794 s) vs published 0.767.
  Per-case extract: 0.67 1.00 1.00 0.17 0.83 (case 4, HN/Rust list, is
  the base model's weak case).
  Operative researcher bars: extract > 0.733 AND plan >= 1.000.

### 2026-11-08 steering (Arnav via parent): specialize the fix
- The coordinator defect is ONE systematic signature (plan-size), so
  whole-adapter scaling trades good behaviour away with the defect.
  Remaining sweep strengths (s25/s75) demoted to fallback only.
- SPECIALIZED datasets built (edit-lab/build_specialized.py):
  - data/coordinator_specialized.jsonl (56 rows): all >=3-step
    originals x2 (38) + 14 composed 4-5-step expansions of original
    2-step tasks in the data's own step style (split compound steps
    into atomic ones; gold-style needs/done_when) + the 2 genuinely
    2-step guard examples x2 as regulariser (newsletter refusal,
    delete-files ask-first). Step dist {2:4, 3:32, 4:16, 5:4} -
    93% inside the 3-7 band the eval's size check requires.
  - data/researcher_specialized.jsonl (114 rows): all 43 extract rows
    x2 (every output verified valid JSON; median 469 chars - the data
    was already clean, the dose was the problem) + all 28 plan rows x1
    to protect the perfect plan score. To be trained 1 epoch at
    lr 1e-4 vs the original 3 epochs at 2e-4 (loss 0.87 -> 0.06).
- NOTE: a service restart killed the first coord_s50 run at 3 cases
  (0.83 1.00 1.00); anchors were already saved and copied to
  edit-lab/results/. s50 restarted detached; first cases reproduce
  identically (greedy decoding).

### 2026-11-08 sweep result: coordinator s=0.5
- coord s=0.5 (lora_B halved): **0.894** (n=14, 1803 s).
  Per-case: 0.83 1.00 1.00 1.00 0.83 0.83 1.00 0.67 0.86 0.83 ...
- Dose-response on this machine: s=1.0 -> 0.791, s=0.5 -> 0.894,
  s=0 (base) -> 0.930. Scaling interpolates toward base but does not
  cross it: the edit's direction carries the defect with the benefit,
  exactly the limitation Arnav predicted. Scaling alone cannot win;
  the specialized retrain is the main path (running).

### 2026-11-08 INCIDENT: coordinator training OOM-killed
- First specialized coordinator train (56 rows, 2 epochs, lr 2e-4)
  was SIGKILLed (exit 137) after step 10/28 (loss 1.14 -> 0.74).
  This cell is shared (1.5 vCPU); other tenants held ~3.7 GB while
  no edit-lab process ran, and the training was the largest process
  on the box. No adapter was saved.
- The phase script rolled into an eval against the missing adapter;
  the HF engine silently fell back to the BASE model (first cases
  0.50 1.00 = the base anchor's). That eval was killed and its
  partial output discarded as invalid.
- Recovery (run_phase3r.sh): coordinator specialized at 1 epoch
  (14 steps - a coherent targeted dose, half the exposure window);
  researcher trimmed to data/researcher_gentle.jsonl (71 rows:
  extract x1 + plan x1) at 1 epoch, lr 1e-4 - one sixth of the
  original failing dose (71 samples x 3 epochs x 2e-4), with train
  and eval processes run unbuffered (-u) for live progress.

### 2026-11-08 INCIDENT 2: coordinator 1-epoch train OOM-killed at ~step 12/14
- The 1-epoch retry was also SIGKILLed (exit 137), after step 10
  (loss 1.11 -> 0.75), minutes before it would have saved. Training
  RSS is flat ~5.5 GB; the kills track other tenants' spikes on this
  shared cell, not growth in the training process. Its chained eval
  again fell back to base (1 case, 0.50) and was discarded.
- Structural fix (method latitude): edit-lab/train_ckpt.py - a
  verbatim copy of training/train_lora.py (repo original untouched)
  with ONLY these additions: --save-every/--ckpt/--resume
  checkpointing (adapter + optimizer + scheduler + loop state every
  2 optimizer steps), and ROOT pointed at the copied tree. A wrapper
  (run_coord_redo.sh) waits for a free machine, trains, and
  auto-resumes after any kill (up to 8 attempts), then evals.
- Meanwhile the researcher gentle train (original script, started by
  the phase-3R chain) survived and is stepping; sequencing from here
  is manual: researcher train -> coordinator redo (train+eval) ->
  researcher eval. One heavy process at a time throughout.

### 2026-11-08 INCIDENT 3: full VM restart (21:40) killed everything
- The researcher gentle train and the first checkpointed redo both
  vanished silently: the VM itself restarted (systemd up since
  21:40). Detached processes do not survive this environment's
  restarts; some earlier "silent deaths" were this, not OOM.
- Response: edit-lab/run_all.sh - one idempotent supervisor for all
  remaining legs (coord train -> coord eval -> researcher train ->
  researcher eval), skipping legs whose outputs exist, training via
  train_ckpt.py with auto-resume (10 attempts). If the VM restarts
  again, the supervisor itself is relaunched by the agent; per-step
  checkpoints bound the loss to ~2 steps (~8 min).
- OUTCOME: the checkpointed coordinator run completed without needing
  a resume (checkpoints at steps 2,4,6,8,10,12; losses 2.35 -> ~0.75).
  training_meta.json saved; coordinator specialized eval running.

### 2026-11-08 RESULT: coordinator specialized retrain (1 epoch) = 0.849
- coord_spec1 (56-row specialized set, 1 epoch, lr 2e-4, checkpointed
  trainer): **0.849** (n=14) - BELOW base 0.930 and below s50 0.894.
  Per-case vs base: case 1 fixed (+0.33: 0.50 -> 0.83, the size defect
  on the HF task), but case 5 -0.16 (right_agents + size), case 6
  -0.17 (size), case 9 -0.14 (right_agents + for_each), and case 14
  (SmolLM2 single-model page) **0.00 vs base 1.00** - failed 'valid':
  no parseable plan at all. The targeted data fixed the headline
  defect on some tasks but the 1-epoch dose left format fragility.
- Combination phase (method latitude): exact LoRA soup built -
  edit-lab/soup.py merges spec + rejected into one rank-32 adapter
  whose delta is EXACTLY 0.5*dW_spec + 0.5*dW_rejected (block
  construction; B blocks scaled 2w). The rejected adapter never
  produced an invalid plan (min case 0.57), so the merge may keep
  spec's case-1 fix while restoring format stability. Soup eval
  running as coord_soup50. Researcher legs paused (trainer killed
  pre-checkpoint; train_ckpt makes the restart cheap) and resume
  after.

### 2026-11-08 DIRECTIVE: decompose the coordinator (Arnav: "make more
### specialists", refined: "more smaller tasks for each specialist")
Split derived from the eval itself (training/observe.py
eval_coordinator + team/specialists/coordinator.py normalize). The six
checks decompose into micro-behaviours: valid (parseable plan),
clean (no normalize problems: no verifier steps, no unknown agents,
for_each only over earlier steps, non-empty tasks, ends-with-writer so
normalize need not append one), right_agents (per-agent presence),
size (3-7 AFTER normalize's drops/appends), done_when (every step),
ends_writer (raw last step), for_each (fan-out steps on 'each' tasks).
Cells reference (origin/make-it-work, studied via git show): one
shared base, per-skill thin LoRAs on locator-picked modules, per-cell
dev/test (split_orders 0.90 test, route_step, next_move, json_repair).
Adaptation here: micro-LoRAs (rank 4, alpha 8, same 7 projections,
layers 14-27 - the trainer's defaults, so tensor key sets match)
trained on contrast-filtered plan data (build_micro.py), composed by
EXACT block-merge (merge_n.py: merged delta = sum of weighted deltas)
into ONE adapter, because the unmodified harness loads one adapter
per role. Six micro-specialists:
  size_band (17 rows: 4-7 step plans), pick_researcher (19),
  pick_browser (15), pick_coder (22), for_each (11: 5 pool rows with
  fan-out steps + 6 composed fan-out rows in domains disjoint from
  the eval tasks), style_anchor = the existing specialized adapter
  merged at weight 0.25 (house style: valid/clean/done_when/
  ends_writer) instead of a seventh training run.
Composite v1 = 5 micro cells @ 1.0 + spec @ 0.25 (merged rank 36).
Granularity note: agent-picking is split per-agent (3 specialists),
size owns only the 4-7 band, for_each owns only fan-out marking,
style owns only format discipline - each is the smallest completable
piece its check measures.
- Soup eval (coord_soup50) DIED silently after 2 cases (0.83, 1.00 -
  tracking spec) - OOM-kill signature, no report. Not re-run: the
  N-way composite supersedes the 2-way soup; merge_n.py generalises
  soup.py. Micro datasets built (build_micro.py): size_band 17,
  pick_researcher 19, pick_browser 15, pick_coder 22, for_each 11.
  run_micro.sh trains the 5 cells (rank 4, alpha 8, lr 5e-4, 2
  epochs, checkpointed), merges composite v1, evals it.
- Researcher gentle train relaunched via run_all.sh (legs 1-2
  skipped on existing outputs).
- COMPUTE REALITY CHECK (~27 min in): the cell is delivering ~1
  effective core (neighbours contending); researcher examples (mean
  645, max 1581 tokens) were running >3 min/example - the full
  71-row gentle train projected ~4 h. Dose adjusted, direction
  unchanged (gentler still): stratified HALF set
  data/researcher_gentle_half.jsonl (36 rows = 22 extract + 14 plan,
  seed 7) at the same 1 epoch / lr 1e-4, fresh out dir res-spec2.
  Micro cells likewise trimmed 2 epochs -> 1 (rank 4, lr 5e-4);
  each cell still gets 3-6 optimizer steps.

### 2026-11-09 BLOCKER: host compute collapse after VM reboot
- The VM rebooted ~23:58 (uptime evidence). Since the reboot every
  heavy run crawls: soup eval 2 cases in ~35 min then lost in the
  reboot; researcher train (full and half set) produced NO step-2
  checkpoint in 27-43 min windows; instrumented restart
  (train_ckpt.py now prints per-example timings) still had not
  finished example 0 (234 tokens) after 17 min.
- Diagnosis evidence: cell itself near-idle (load ~1.7, trainer the
  only heavy process at ~101% of one core); main thread R, intraop
  workers idle (batch-1 ops run single-threaded in this build);
  raw torch bf16 2048^3 matmul benchmark ~1-3 GFLOPS vs the
  ~100 GFLOPS implied by the coordinator training earlier the same
  evening (steps of 180-210 s). Conclusion: host-level CPU
  throttling since the reboot, invisible from inside the cell.
  Nothing in the trainer/eval code or data explains it (first 8
  half-set examples total only 4,532 tokens).
- State left running: run_all.sh (attempt log run_all_main4.log)
  with the instrumented researcher train; checkpointing +
  auto-resume mean a throttle lift lets the whole queue (researcher
  train -> researcher eval -> then run_micro.sh by hand) proceed
  without loss. Escalated to parent as genuinely blocked on host
  compute; all coordinator results and the decomposition design
  above stand as delivered-to-date.
- NOTE: `--only researcher` matches no suite (keys are researcher_plan /
  researcher_extract) and silently reports {}. The first base-researcher
  run no-op'd for this reason; rerun with both suite names.
- Machine speed: coordinator eval took 3208 s here vs 576 s on the
  original machine (~5.6x slower; decode is memory-bandwidth-bound on
  this VM). All runs below are correspondingly slow.

### 2026-11-08 branch mining (Arnav's permission to use other branches)
Fetched origin/results-and-demo, final-product, make-it-work, micro-cells
and compared blob hashes against this tree (8a1e306):
- adapters/.rejected/coordinator/adapter_model.safetensors: identical
  blob 4df0a66 on ALL branches.
- adapters/researcher/adapter_model.safetensors: identical blob e2b4b47
  on ALL branches.
- training/data/{coordinator,researcher_extract,researcher_plan}.jsonl:
  identical blobs on ALL branches; no extra/self-distilled data files
  for these roles anywhere.
- training/reports/kept.json identical everywhere ("coordinator: no -
  scored 0.79 vs 0.94 base; overfit to 2-step plans").
Conclusion: no branch holds a better coordinator or researcher edit,
better data, or a relevant win for these two roles. The other branches'
successes are the cells feature and writer/browser fixes. Nothing to
incorporate; the repair must be made here (scaling / retraining).

### 2026-11-09 ASHP re-home (Arnav authorized; job stays open)
- Lab extracted on ashp to D:\muse\work\edit-lab from the verified
  backup tarball; dedicated venv built with VM-matching versions
  (torch 2.15.0+cpu, transformers 5.22.2, peft 0.21.2, accelerate
  1.15.0); Qwen/Qwen3-1.7B fetched fresh into D:\muse\cache\hf.
  train_ckpt.py kept byte-identical: a junction
  C:\Users\muse\workspace -> D:\muse\work satisfies its hardcoded
  ROOT. Detached launches must use WMI Win32_Process.Create
  (Start-Process children die with the SSH session).
- Laptop benchmarks (i7-10870H, 16 threads, 32 GB): fp32 matmul
  213 GFLOPS, bf16 90 GFLOPS, model load 6 s, plain bf16 decode
  24.4 tok/s. BUT the trainer's autocast("cpu", bf16) train step is
  pathological on this Windows torch build: main thread ~100%,
  intraop pool idle (~1.1 cores total), ZERO examples completed in
  ~25 min across two launch contexts (WMI and SSH-foreground) -
  vs ~50 s/example at the VM's good pace. Diagnosis: CPU autocast
  bf16 dispatch falls back to a near-single-threaded path on this
  build; bare GEMMs outside autocast are fast, so it is not the
  silicon and not the launch context (affinity verified all-16).
- Decision: port TRAINING ONLY to the GTX 1650 Ti -
  edit-lab/train_gpu.py = train_ckpt.py with device-only edits
  (model/batches/autocast on CUDA; data, seed, lr, loss masking,
  checkpointing identical). The eval instrument is untouched:
  observe.py still runs the standard CPU hf path, so scores remain
  comparable to every anchor above. CUDA torch install in flight;
  tunnel connectivity to ashp then dropped (no SSH banner via the
  proxy) - waiting on the path, no state lost (no leg had produced
  checkpoints; trainings restart cleanly).
- UPDATE (later 2026-11-09): the outage persisted ~40+ min of
  retries; the CUDA install session died with the connection ~4 min
  in, so the venv's torch state must be verified first on reconnect.
  GPU pipeline fully staged (train_gpu.py, gpu_smoke.py,
  master_gpu_worker.ps1 in ~/workspace on the VM). Full status and
  resume procedure: results/ashp_run_summary.md. No scores produced
  on ashp yet; no git operations performed.
- Late-arriving replica datapoint (same evening): one forward pass
  on the longest researcher example (len 1581, k 703) under
  autocast("cpu", bf16) took 242.7 s while sharing the box with the
  trainer (~18 GFLOPS effective for ~4.4 TFLOP) and never reached
  its backward print before being stopped - quantitative
  corroboration of the autocast-CPU pathology above. The trainer
  process showed 65 threads, Normal priority, affinity all-16,
  closing out the launch-context theories.
- Second late datapoint: the plain-vs-PEFT experiment's
  parallel_info showed a healthy backend config (ATen 8 threads,
  OpenMP, MKL-DNN 3.13, hardware_concurrency 16), yet even the
  PLAIN (non-PEFT) autocast arm never printed a timing for a small
  median example (len 370, k 127) in ~8 min before being stopped -
  the pathology is in the autocast CPU dispatch itself, not PEFT,
  not thread configuration.

### 2026-11-09 VM RUN (this worker): speed myth resolved; kills root-caused
- The "host throttle" was a benchmarking error: system numpy BLAS is
  broken (2-3.5 GFLOPS) while the lab venv's torch measures fp32 68 /
  bf16 154 GFLOPS at 2 threads on this same box. With ONE heavy process
  at a time and OMP/MKL = 2, training runs at the evening's original
  pace (~90-190 s/step).
- The repeated exit-137 kills were MEMORY: trainer VmHWM 5.74 GB vs
  the cell's 6 GB cap. Fix (applied by main chat to train_ckpt.py):
  gradient checkpointing (use_reentrant=False) +
  enable_input_require_grads - memory-only, same recipe/order.
  Patched researcher trainer VmHWM peaked 5.12 GB (incl. checkpoint
  saves) and completed. MALLOC_ARENA_MAX=2 + MALLOC_TRIM_THRESHOLD_=0
  on all relaunches.
- Incident log: TWO run_all supervisors ran concurrently for part of
  the evening (dual-supervisor checkpoint race on ckpts/res-spec2:
  state regressed 16 -> 6; several "kills" were the two trainers
  OOM-ing each other). This worker wiped the contaminated lineage and
  re-ran leg 3 in ONE clean pass under ONE supervisor. An early
  progress note from this worker claimed leg 3 complete from a
  transient state read - that was wrong; the verified completion is
  the run below. A VM restart also killed run_micro.sh mid-size_band
  (step-2 checkpoint survives).

### 2026-11-09 RESULT: researcher gentle retrain (res-spec2) - NO WIN
### under the anchor protocol (env-sensitive; see below)
- Dose as encoded in run_all.sh: researcher_gentle_half.jsonl
  (36 rows), 1 epoch, lr 1e-4, rank 16 alpha 32. Clean single-
  supervisor completion after the checkpointing patch; final losses
  ~0.34-0.49. Adapter: candsets/res-spec2/researcher.
- OPERATIVE scores (default thread env = the anchor protocol of
  run_anchors.sh; two independent runs agree):
  researcher_plan **0.975** (n=10) - toscrape case 0.75 (right_source
  flip), all others 1.00. Base = 1.000 -> plan gate (>= 1.000) FAILS
  by one check on one case.
  researcher_extract **0.767** (n=5), per-case [0.17 1.00 1.00 0.83
  0.83] vs base [0.67 1.00 1.00 0.17 0.83] (0.733): fixed base's weak
  case 4, broke case 1. Extract bar (> 0.733) passes by +0.034.
- ENV SENSITIVITY (measurement-integrity finding): the SAME adapter
  under OMP_NUM_THREADS=2 scored plan 1.000 / extract 1.000
  (all 15 cases perfect). Greedy bf16 CPU generation flips borderline
  generations with thread count; margins here (n=10, n=5) are
  one-case scale = noise band. Verdict stands on the anchor protocol:
  NO WIN. The 2-thread file (results/res_spec.json from that run) was
  later removed from results/ by a concurrent process; its content is
  preserved in this worker's session record and superseded by
  results/res_spec_verify.json (operative, default env).
- Default-env extract evals are also fragile operationally: two runs
  were OOM-killed entering the extract suite before this verification
  run completed it (2754 s).

## 2026-11-09 ~12:23 PT — drop14 DEAD BY CEILING; soup50 test relaunched alone
- VM restarted ~20:14 UTC mid-drop14-test (case 4). Partial scores [0.50, 1.00, 0.00] cap the run at 0.893 < 0.930 even with a perfect remainder -> DEAD BY CEILING, remaining 11 cases not run (same standard as the micro composite). Verdict in lineage.jsonl.
- soup50 pristine test relaunched alone (saves ~1.5 h of doomed drop14 cases). If the ~2 h VM restart cadence kills it mid-run, the same ceiling logic will be applied to its partials.

## 2026-11-09 ~13:12 PT — soup50 DEAD BY CEILING; coordinator test queue CLOSED
- soup50 pristine test stopped at 9/14: partials [0.83, 1.00, 1.00, 0.83, 0.67, 0.83, 0.83, 0.67, 0.71] sum 7.37, ceiling 0.884 < 0.930. Souping averaged the parents' failure modes (running mean 0.819 vs parents 0.791/0.849).
- ALL coordinator candidates ever pristine-tested are below base 0.930: rejected 0.791, s50 0.894, coord-spec 0.849, drop14 <=0.893, soup50 <=0.884. Surgery/scaling/souping on the original adapter family is exhausted. The only remaining coordinator path is the WAYS-OVER synth-data retrain (data generation running on ashp), then router/jury composition, then the pinned-protocol 45-case final measurement.

## 2026-11-09 ~14:05 PT — burst 2 launched; start-gate note
- Idle cooling asymptote: after ~35 min idle the GPU sat at 56C with the curve flat (~1C per 8 min) — that is this heat-soaked box's practical idle floor today (true cold idle was 45C). The <=55C start gate was adjusted to <=56C on that evidence (documented, not drift): the gate's purpose is a cooled box, and 56C idle-flat is cooled. Tripwire unchanged: pause at 82C, mid-burst check enforced.
- Burst 2 launched: run_synth145.bat (--limit 145; skips 111 done, ~34 new attempts, ~21 min).

## 2026-11-09 ~14:12 PT — JOB EXPANDED (Arnav): NO-GRADIENT-EDITING Phases 0-4 + factory unification
- Directive: finish current queue first (synthesis bursts -> dataset -> retrains -> dev gates -> pristine tests -> composition -> 45-case final measurement), THEN execute NO-GRADIENT-EDITING.md on Qwen3-4B, THEN unify all stages into ONE automated factory loop (diagnose -> map/indict -> edit -> train-indicted-only -> chain/compose -> grow; coding/swarm/factory.py + lab surgery protocol unified, not rebuilt). Coordinator/researcher anchors remain the regression pack. One heavy job at a time across VM+ashp; ashp also has a storage compression job running today — check tempwatch + processes before heavy legs.
- Doc's pre-registered win for the 4B line: sealed test math >= +3 pts over base AND no IF regression beyond noise, sign-test positive on paired deltas, all lab gates unbroken, replicates under alternate thread env, gain decomposition (defect-fixed vs capability-flipped) mandatory.
- Phase 0 decides the branch: classify base 4B dev failures D (defect, shared mechanism) vs C (capability). D >= ~15% -> Phase 2 directional ablation (steer first, bake second, bit-diffed checkpoint, test once). Phase 3 scalar search (<=50 scalars, 300 dev-eval budget cap, confirm split) runs regardless. Phase 4: <=2 finalists, one test run each + full regression pack + alt-env re-run.
- Diagnosis doctrine updated per directive: classify from raw OUTPUTS first (the WSP lesson); loss/gradient maps are supporting evidence, not the lead.

## 2026-11-09 ~14:15 PT — burst 2 paused early (co-run heat); micro-burst regime while compression runs
- Burst 2 stopped at 127/145 attempts (56 kept): with the storage compression co-running, GPU climbed 73->76C in 3 min (~2.3C/min). Synth-only legs plateau; co-run legs do not. Remaining bank: 215 attempts.
- Micro-burst regime until compression finishes: 10 attempts per burst, start <=60C, pause at 80C, checks every ~4 min. Revert to 35-attempt bursts when tempwatch CPU load shows the compression is done.

## 2026-11-09 ~14:25 PT — FACTORY-ARCHITECTURE.md written (design phase, per Arnav's directive)
- New file: FACTORY-ARCHITECTURE.md — compute-adapted factory design against the measured envelope (VM 1.5 vCPU/6 GB/~2 h reboots; ashp 4 GB VRAM + thermal ceiling + co-run regime). Five pillars developed with exists/missing/changes for each: tiered specialists T0 constructed nets (default) -> T1 quantized small LMs -> T2 4B/7B bursts-only (4-bit only: bf16 4B fits neither machine) -> T3 frontier as tool; composition over escalation; eval economy (funnel + per-stage budget caps + codified ceiling-kill); restart-native (lineage is the state, <=20-min chunks, no irreplaceable RAM state); thermal-aware scheduling as a layer (tempwatch-gated queue, burst budgets by regime, cross-machine single-heavy-job lock).
- Includes: the unified loop's stage map priced per stage, a build list for the unification phase (7 items), and the final-report contract (measured compute profile alongside the whole-hive benchmark). Unification is built TO this architecture after the test queue + defect hunt.

## 2026-11-09 ~14:24 PT — FACTORY-ARCHITECTURE.md REVISED per Arnav (machine-agnostic, low-stress)
- Revision (14:19 PT) superseded the 14:14 framing: the doc was rewritten portable-first. Host numbers now appear ONLY as two labeled example profiles ("small cloud cell", "older gaming laptop") — evidence, never assumptions. Normative content is formulas and rules: startup host probe (cores/RAM/accelerator/thermals/power/storage/restart cadence) -> profile -> tier availability, batch/chunk sizes, budgets.
- Low-stress is design rule 3: utilization caps, duty-cycling, automatic backoff (hot / owner-busy / battery), heavy legs opt-in per-host (default gentle), Tier-0 dominance as the stress strategy. Eval economy budgets re-expressed machine-free: count caps where statistical (300 search evals), probe-derived wall-clock caps where mechanical (chunk ceiling = shortest interruption horizon / safety factor). Restart-native strengthened for uncontrolled hosts (no irreplaceable state outside the run directory by construction). Final report gains a portability line (results restated per host profile).

## 2026-11-09 ~14:35 PT — BitNet ternary specialists added to FACTORY-ARCHITECTURE.md (Arnav's addition)
- Tier 0 now has two first-class substrates: (a) full-precision tiny nets, (b) ternary BitNet-style specialists {-1,0,+1} (~1.58 bits/weight, ~10x smaller than fp16, addition-dominated inference). Born trained (QAT/straight-through estimator) or constructed — both first-class, verified the same way.
- Ternary-aware surgery section added: edits are discrete flips; per-weight flip-ablation maps are cheap and near-exact at specialist scale (indictment stops being an estimate — the deliberate contrast with the diffuse LM-tier maps); frontier repair-by-reasoning gets 2 alternative states per indicted weight (Nov 7 pattern).
- Honest constraint handled by protocol, not dogma: bit-width is per-niche, decided by a head-to-head (same niche, ternary vs fp: held-out score + footprint + latency) recorded in the registry. Build list gained item 3b (ternary trainer/constructor, flip mapper, ternary persistence, head-to-head harness); report contract gained the substrate line. Defect-hunt and test-queue order unchanged.
- Note: during this edit pass the doc was found truncated at section 5 (a write artifact from the revision pass); it was repaired and verified complete (355 lines, sections 1-9).

## 2026-11-09 ~15:40 PT — TOOLING CATCH: trainer checkpoints need explicit --ckpt (two bursts lost)
- train_gpu.py code sets ckpt_dir=None unless --ckpt is passed, despite --help claiming a default. Bursts 1-2 of the r4 smoke train therefore wrote no checkpoints and the --resume was a silent no-op (burst 2 restarted from base). No durable adapter exists yet.
- Fix in force: always pass --ckpt explicitly + --save-every 2, and verify state.json + the 'resuming from checkpoint at step N' print before trusting any resume. Smoke epoch relaunches clean with checkpoints.

## 2026-11-09 ~18:00 PT — SMOKE DEV SCREEN: synth-r4 0.8511 vs base 0.7479 (+0.103), zero regressions
- multi_eval (OMP=2, adapter-load verified): per-case 10/12 identical to base; case 9 (toscrape count+average) 0.333->1.000, case 11 (HF GGUF + Q4 size) 0.286->0.857. Regression gate clean.
- Contamination: 8-gram overlap dev tasks vs all 65 synth rows = 0.00 everywhere. The fixed cases sit in the mix's two biggest families (hf_models 16, toscrape_browse 14) — family-level generalization from checker-verified self-distilled data, exactly the WAYS-OVER thesis.
- NOT a win: dev ranks only, n=12. Path forward unchanged: bank to >=100 kept -> full v1 mix -> r2/r4/r16 family -> dev-select -> one pristine test.

## 2026-11-09 ~18:46 PT — BINDING DECISION (Arnav): v1 sequence, then the coordinator contest CLOSES
- Execute exactly: bank to >=100 kept -> full-mix family r2/r4/r16 -> dev-select ONE finalist -> ONE pristine test vs 0.930. Win or lose, NO further candidates/doses/soups/surgery against that gate afterward. Verdict to lineage + REPORT.md either way.
- After the test: defect hunt (Phases 0-1) -> factory architecture implementation (BitNet Tier-0 + head-to-head) -> unification under win-gates. Final factory report owes whole-hive benchmark + compute profile.

## 2026-11-09 ~19:52 PT — note: family train outputs land in runssynthv1_* (missing backslash)
- The generated family bats expanded `runs\$name` to `runssynthv1_r2` etc. (PowerShell here-string ate the backslash). Training itself is correct (117 rows, right rank/alpha/layers/lr) and checkpoints ARE being written to runssynthv1_r2.ckpt; resume bats derived from the same text use the same paths, so pause/resume is consistent. Final adapters will be copied from edit-lab\runssynthv1_<r> (lab root on ashp), NOT runs\.

## 2026-11-09 ~22:32 PT — screen launches MUST set HF_HOME=~/workspace/edit-lab/hf
- The VM default HF cache (~/.cache/huggingface) holds only a partial Qwen3-1.7B download (4.3 MB, .incomplete blob) — a screen launched without HF_HOME crashes at model load with a misleading "no model.safetensors" OSError. The lab's canonical env (dev_run.sh etc.) sets HF_HOME=$EL/hf. Adapter guard (--expect-adapter) still verified correctly before the crash.

## 2026-11-10 ~03:26 PT — THERMAL LESSON: llama-server is a continuous-load regime
- The Qwen3-4B llama-server run climbed steadily 68C -> 93C over ~50 min at 94-97% GPU util with NO plateau (unlike trainer bursts, which plateau at 78-80C — the server keeps the GPU saturated between requests too). Killed runner+server at 93C; box safe. Remaining defect cases run in ~45-case chunks with full server kill + cool to <=60C between chunks. 188/200 math_dev cases were banked before the kill.

## 2026-11-10 ~13:10 PT — FACTORY PHASE C: dream cycle clears the bug-pattern bar; ternary measured; growth gated
- Per Arnav's directive (~12:54 PT: add the dreaming part "in your part with increasing number of specialists and all other ideas"). Design: FACTORY-ARCHITECTURE.md §10; full record: factory/FACTORY-LOOP.md (Phase C section).
- DREAM CYCLE (factory/dream.py + dream_gen.py): subjects generate their own practice — parameterized bug families in 3 difficulty bands, labels PROVED by execution (correct code runs; mutations observably differ; unverifiable dreams discarded), difficulty thermostat (per-class edge band from fresh-probe positive recall; persisted in factory/dream_state.json), s1 difficulty filter + slice diversity quota, good views (every kept case in 2 execution-verified surface forms), contamination filter vs train ∪ held ∪ phase-4 dream corpus. First cycle (dream-phaseC-001) REVERTED at the screen — the screen shared skeletons with training, the filter zeroed it (238→0), confirm never spent; fixed with screen-only skeletons + recall thermostat.
- WIN (dream-phaseC-002): harness re-measured the incumbent composition at the recorded 0.7931 plateau before judging; composed screen 0.4221→0.4610; confirm spent ONCE on phase-4 held: 0.8276 ≥ 0.80 bar, every per-class recall ≥ its phase-4 recorded value. Adopted: bug-wrong-operator-model retrained on dreams (binary held 0.862→0.897, binary screen 0.578→0.779; phase-4 record backed up in the run dir). Honest size: net +1 case (23→24/29) via the clean class; the weak classes' composed recalls are unchanged — their binding constraint is margin competition, not binary accuracy. Consequence: phase-4 held set is now spent as a confirm; future bug-pattern verdicts need a fresh held-out set.
- TERNARY (factory/ternary.py; runs phaseC-ternary-001/002): PTQ + born-ternary QAT (STE) + per-weight flip-ablation mapper + head-to-head on all 5 adopted specialists. Gate (ternary ≥ fp) passed NOWHERE — fp keeps all five niches (error 0.958 vs 0.950; contract 1.0 vs 0.938; gap 0.933 vs 0.867 QAT — PTQ had collapsed it to 0.267; secret 1.0 vs 0.992; commit 0.963 vs 0.763). Footprint wins are 100–500× (252 B–4.9 KB packed) but do not compensate any accuracy loss at Tier-0 scale. Flip-map surgery DID work: secret-line PTQ pack, 114 improving flips indicted on training probes, applied subset judged once on held-out 0.9154→0.9385, adopted as coexisting secret-line-model-ternary.json (fp remains default).
- GROWTH (factory/growth.py; phaseC-growth-001): intake scan + split-birth protocol live. Two births attempted with dream-augmented slice data — wrong-operator/expression (child 0.85 = parent 0.85, n=20) and off-by-one/index (0.95 = 0.95, n=20): both TIED, both rejected (a tie is not a birth), no files changed. Slice training teaches children to match parents including the same hard cases.
- ALSO: intake fix (subjects.py diagnoses the adopted v2s; load_incumbent starts from v2; wins over v2 save as v3 — dry-phaseC-check: gap-move and secret-line now HOLD, contract/commit show preventive drift); scheduler.py (cross-process heavy-leg lock + persistent cycle queue); reporter.py (§9 contract → factory/reports/factory-report.md: 12 cycles, 5 adoptions, substrate line, stress ledger — 0 heavy legs, 0 backoffs, no thermal sensor on this host). Consultation composition designed (arch. §10.4), not built — follows the internals Phase 5 verdict, still pending. Tests: 31/31 (17 new Phase C tests). Boundary held: Fable's side untouched; coordinator untouched.

## 2026-11-10 ~18:40 PT — FACTORY PHASE D: final product built; battery run; both red flags attacked
- Per Arnav's standing direction (main line first, side labs separate, no merging) + the 13:51 PT addendum ("this isn't about optimism, it's about making it work" — convert the battery's red flags into fixes in-pass).
- WI-1 SEALED SET: coding/swarm/bug_heldout_v2.json — 15 new families, n=36, sha256 cd17c922…, decontaminated vs train/held/dream corpora. Baseline (one measurement): composed 0.4444 vs bar 0.80. Binaries decent (0.69–1.0); composition falls on novel structures.
- WI-2 NICHE DREAMS: dream_gen_niches.py + dream_niches.py (contract labels execution-proved; commit labels checker-proved; disjoint pools; thermostat). Contract cycle WIN → contract-judgment-model-v3 adopted (paired confirm 0.9048 vs 0.7619). Commit cycle (via daemon) REVERT — candidates under the held floor, confirm unspent. gap-move/secret-line HOLD respected.
- WI-3 REGISTRY + AUDIT + SERVE: factory/registry.json is the single book (5 jobs, 14 composition members, Tier-1 provenance); ServingHive.load() verifies hashes + the serving rule and fails closed; full audit re-measures every serving score — all reproduce exactly.
- WI-4 TIER-3: TIER3-CONTRACT.md + tier3.py stub — allowlist, never-delegate list, budget caps, verbatim audit log, fail-closed. No keys, no calls.
- WI-5 DAEMON: factory/daemon.py consumes the queue under the governor; proof = 2 queued cycles end-to-end (real commit cycle + dry sweep), §9 reports filed, queue_history.jsonl written.
- BUG-PATTERN FIX (13:51 direction): diagnosis corrected the Phase C inference — on novel structures the losses are BINARY MISSES (competition losses = 0; weak-class own-margin medians −9.96/−6.44/−4.20), not margin competition. Four attempts (bugfix-…-001..004), spent-set gates only, sealed set never trained on: 001 instrument faults (screen seeds are normalized-identical; band starvation), 002 dream-swamped mix (screen up, held cratered), 003 per-class floors vetoed all recall gains, 004 composition gates alone: screen 0.5649 vs 0.461 (+0.104), held 0.7586 vs 0.8276 (−0.069) → held gate refused. NOTHING adopted. Post-fix sealed judge (once): 0.4444, delta +0.0 per class — UNMOVED, recorded as the result.
- ADOPTION RULE (13:51 direction): the v3 catch is now the standing serving rule in registry/audit code — battery slice (factory/battery_evidence.json) >= incumbent's or the artifact is SHADOW (audited, never served, never fallback). Contract serves v2 (0.9167 promoted over 0.5833); v3 (measured 0.4167) is shadow. Audit fails closed on a forged book (tested). Note: v3's model record carries an inherited battery_reference_acc 0.9167 — the rule uses measured values only.
- WI-6 BATTERY (results/hive_battery_acceptance.json): specialists ALL MET (secret 10/12, error 12/12, commit 12/12, contract-v2 11/12, gap 8/10; ternary 11/12 informational); tiny-hive 21/21 + 3/3 OOD refused; bug composition MISSED 0.4444. Composites: b1 FAILED environmental (arXiv API dead for the full 5400s; passed 3/3 in the prior battery), b2 FAILED (VM-restart kill, then a 3600s no-deliverable re-run), b3 FAILED on substance (1608s, report missed the required year), b4 FAILED (VM-restart kill; also failed in the prior battery), b5/b6 running at entry time (chain3) — outcomes in the acceptance JSON. Guard integrity held throughout: killed/crashed runs score 0 with causes, never passes.
- WAKING DREAM (side lab, recorded not adopted): answer-time verification over the untouched serving binaries measured 0.8333 (30/36) on the sealed set — first clear of the 0.80 bar on a fresh set; verified answers 0.933 acc, defect verifications 21/21, fallback 0.333, +16.5 ms/case. Recorded in FINAL-PRODUCT.md as a PENDING ADOPTION CANDIDATE under the serving rule. Adoption is Arnav's call; the product does not change.
- Docs: FINAL-PRODUCT.md (broken → fixed → still broken), factory/FACTORY-LOOP.md Phase D section. Tests 50/50. Boundary held: nothing written to Fable's side; coordinator winner untouched.
