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
