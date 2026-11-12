# ASHP run summary — 2026-11-09 (STATUS: BLOCKED on connectivity; job stays open)

## Scores
- Researcher gentle retrain (res-spec2): **not evaluated** — training never
  completed on ashp (see below). Bars: extract > 0.733 AND plan >= 1.000.
- Coordinator micro composite v1: **not evaluated** — cells never trained.
  Bar: > 0.930.
- No candidate beat any bar in this run; no scores were produced on ashp.
  All VM anchors stand unchanged (base 0.930 / rejected 0.791 /
  s50 0.894 / coord-spec 0.849; researcher plan 1.000 / extract 0.733).

## What was accomplished on ashp (D:\muse\work\edit-lab)
- Lab extracted from the verified backup tarball; key paths verified
  (tree, data, micro data, coord-spec style-anchor adapter).
- Dedicated venv with VM-matching versions (torch 2.15.0+cpu,
  transformers 5.22.2, peft 0.21.2, accelerate 1.15.0, numpy 2.5.4,
  safetensors 0.8.0, huggingface_hub 2.4.0); Qwen/Qwen3-1.7B downloaded
  fresh into D:\muse\cache\hf (HF_HOME already routed to D:).
- train_ckpt.py kept byte-identical — a junction
  C:\Users\muse\workspace -> D:\muse\work satisfies its hardcoded ROOT.
- Process-launch lesson: Start-Process children die with the SSH
  session on this box; WMI Win32_Process.Create survives. (Also: long
  SSH foreground sessions work and parallelize the same as WMI.)
- Benchmarks (i7-10870H / 32 GB): fp32 matmul 213 GFLOPS, bf16
  90 GFLOPS, model load 6 s, plain bf16 decode 24.4 tok/s.

## The blocker chain (two layers)
1. **Trainer pathology on the Windows CPU torch build.** The pipeline
   was launched faithfully replicating run_all.sh leg 3 + run_micro.sh.
   The researcher train completed ZERO examples in ~25 min across two
   launch contexts. Forensics: main thread ~100% of one core, intraop
   pool idle (~1.1 cores total), affinity verified all-16, no
   checkpoint written. Bare GEMMs outside autocast are fast
   (90-213 GFLOPS) and plain bf16 generation is fast (24 tok/s), so
   the silicon/BLAS are fine — the autocast("cpu", bf16) training
   dispatch on this build falls back to a near-single-threaded path.
   Root cause isolated to the training step only; eval (generation)
   is unaffected.
2. **Connectivity to ashp dropped mid-recovery.** The chosen fix was a
   GPU port of TRAINING ONLY (train_gpu.py — train_ckpt.py with
   device-only edits; eval stays the unmodified CPU observe.py so
   scores remain comparable to all anchors). During the CUDA torch
   install (~4 min in), the tunnel to ashp died: SSH connections are
   refused/closed ("Connection closed by UNKNOWN port 65535"), no SSH
   banner is returned through the proxy, and tailscale still lists
   ashp as a known device. ~40 min of retries: still down. The laptop
   is unreachable (asleep/off/network) — outside this agent's control.

## State left behind (nothing lost)
- Laptop (when it returns): lab + venv + model cache intact. The CUDA
  torch install was interrupted mid-flight by the outage — the venv's
  torch MUST be verified first (import torch / torch.__version__ /
  cuda.is_available()); if broken, re-run:
  pip install --force-reinstall torch==2.15.0  (launch it DETACHED
  via WMI, not in an SSH foreground session).
- No training checkpoints were ever written on ashp; every leg
  restarts cleanly. No git operations were performed anywhere.
- The VM's own checkpointed run_all.sh was left untouched per
  instructions (ignored; laptop numbers would have governed).

## Resume procedure (minutes, once ashp is reachable)
1. Verify/repair torch in D:\muse\work\edit-lab\venv (see above);
   confirm torch.cuda.is_available() is True.
2. scp from this VM's ~/workspace/: train_gpu.py -> edit-lab\,
   gpu_smoke.py -> edit-lab\ashp_logs\, master_gpu_worker.ps1 ->
   edit-lab\ashp_logs\.
3. Launch master_gpu_worker.ps1 DETACHED via WMI Win32_Process.Create.
   It gates on the GPU smoke test (median + longest example fwd/bwd +
   peak VRAM on the 4 GB card), then runs: researcher train ->
   5 micro trains -> merge composite v1 -> researcher eval ->
   composite coordinator eval, logging to ashp_logs\master_gpu.log
   and writing results\res_spec.json + results\coord_composite_v1.json
   in the VM-identical layout.
4. Sync results/*.json + LEDGER back to ~/workspace/edit-lab and
   update this summary with the three scores vs their bars.

## Note on the researcher dose (flagged for the record)
The task text described the 71-row gentle set, but run_all.sh — which
the task instructed to replicate — encodes the ledger's final,
compute-adjusted dose: data/researcher_gentle_half.jsonl (36 rows),
1 epoch, lr 1e-4, out candsets/res-spec2. The ashp pipeline follows
run_all.sh exactly (same as the still-crawling VM supervisor), so
laptop and VM runs stay the same experiment.

Artifacts: this file; LEDGER.md (VM copy, appended 2026-11-09 entry);
~/workspace/train_gpu.py, ~/workspace/gpu_smoke.py,
~/workspace/master_gpu_worker.ps1 (staged, VM side);
D:\muse\work\edit-lab\ashp_logs\ on ashp (install/bench/master logs).
