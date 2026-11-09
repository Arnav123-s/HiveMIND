"""Team configuration: which small model powers each specialist, paths, limits.

Every specialist is a small open-weight model that runs on CPU (no VRAM) in
bf16. Specialists that share a base model share one copy in RAM and differ
only by their own trained weight delta (a LoRA adapter in adapters/<name>/).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = Path(os.environ.get("AGENT_TEAM_ADAPTERS", ROOT / "adapters"))
RUNS = ROOT / "runs"

# Base models (Apache-2.0, ungated, no account needed to download).
BASE_MODEL = os.environ.get("AGENT_TEAM_BASE", "Qwen/Qwen3-1.7B")
CODER_MODEL = os.environ.get("AGENT_TEAM_CODER", "Qwen/Qwen2.5-Coder-1.5B-Instruct")

SPECIALISTS = {
    "coordinator": BASE_MODEL,  # breaks the task down, assigns, re-plans
    "researcher": BASE_MODEL,   # picks sources + queries, extracts quoted facts
    "browser": BASE_MODEL,      # drives a real Chromium: click, type, navigate
    "verifier": BASE_MODEL,     # judges every result against its evidence
    "writer": BASE_MODEL,       # assembles the finished deliverable
    "coder": CODER_MODEL,       # writes, runs and repairs Python
}
for _role in ("calculator", "editor", "code_reviewer", "order_reader", "plan_reviewer", "condenser", "critic", "juror_brain", "juror_fast", "examiner", "prompt_smith",
              "lesson_writer"):
    SPECIALISTS[_role] = BASE_MODEL  # PyTorch fallback: same base, no edit

# ---- Engine v2: llama.cpp with 4-bit weights (less RAM, faster on CPU, bigger brains) ----
# auto: use llama.cpp when it is installed and the GGUF files are present; hf: PyTorch/transformers path above.
ENGINE = os.environ.get("AGENT_TEAM_ENGINE", "auto")
GGUF_MODELS = {
    # name: (repo, file, tokenizer repo used to build the exact same chat prompt)
    "brain4b": ("Qwen/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf", "Qwen/Qwen3-1.7B"),
    "brain8b": ("Qwen/Qwen3-8B-GGUF", "Qwen3-8B-Q4_K_M.gguf", "Qwen/Qwen3-1.7B"),
    "fast": ("Qwen/Qwen3-1.7B-GGUF", "Qwen3-1.7B-Q8_0.gguf", "Qwen/Qwen3-1.7B"),
    "coder7b": ("Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
}
BRAIN = os.environ.get("AGENT_TEAM_BRAIN", "brain4b")
# Chosen by measurement (training/reports/SUMMARY.md): each role gets the model that scored best on its
# held-out evals; ties go to the smaller, faster model. "fast+X" = Qwen3-1.7B with specialist X's own weight edit.
GGUF_ROSTER = {
    "coordinator": BRAIN,           # 4B: 1.00 vs 0.94 (1.7B)
    "researcher": BRAIN,            # 4B: 1.00 / 0.80 vs 0.95 / 0.77
    "verifier": "fast+verifier",    # 1.7B + edit: 0.89 = 4B, 2.7x faster
    "writer": "fast+writer",        # 1.7B + edit: 1.00 = 4B, 2.2x faster
    "browser": "fast+browser",      # 1.7B + edit: 0.79 vs 0.43 (4B)
    "coder": os.environ.get("AGENT_TEAM_GGUF_CODER", "coder7b"),  # 7B: 0.88 vs 0.50 (1.5B)
    "calculator": "fast",           # writes a few lines of Python; Python does the arithmetic
    # quality-control specialists
    "plan_reviewer": BRAIN,         # second look at every plan before work starts
    "condenser": "fast",            # picks the relevant lines of long sources (extractive: quotes stay exact)
    "critic": BRAIN,                # checks the final report against verified results
    "editor": BRAIN,                # rewrites a report only when the critic still rejects the writer's fix
    "juror_brain": BRAIN,           # jury: step verdicts are a vote of three
    "juror_fast": "fast",
    "order_reader": "fast+order_reader",
    "code_reviewer": os.environ.get("AGENT_TEAM_GGUF_CODER", "coder7b"),  # reads the program against the task  # second, independent reading of what Arnav ordered (with the regex)
    # evolution-harness specialists
    "examiner": BRAIN, "prompt_smith": BRAIN, "lesson_writer": "fast",
}
JURY = [s.strip() for s in os.environ.get("AGENT_TEAM_JURY", "verifier,juror_brain,juror_fast").split(",") if s.strip()]
if os.environ.get("AGENT_TEAM_ROSTER"):  # e.g. '{"browser": "fast+browser"}' = 1.7B + the browser's own weight edit
    import json as _json
    GGUF_ROSTER.update(_json.loads(os.environ["AGENT_TEAM_ROSTER"]))
# ---- RAM budget: the whole swarm must fit (default 10 GB) -------------------------------------------
# Members are cheap (a few-MB weight edit + prompt on a shared base); RAM goes to the base models and their
# attention caches. Under the budget: 8-bit attention cache (half the size), per-model context sizes, and at
# most N base models resident (least recently used is unloaded; reload ~4 s from the OS file cache).
RAM_GB = float(os.environ.get("AGENT_TEAM_RAM_GB", 10))
KV_8BIT = os.environ.get("AGENT_TEAM_KV", "q8" if RAM_GB <= 12 else "f16") == "q8"
# prompt-lookup decoding: next tokens guessed from the prompt itself (quotes, claims, code being fixed), checked in one
# pass. Off: in llama-cpp-python 0.3.36 it crashed on the hive's real prompts (training/reports/arch_bench.json).
LOOKUP = os.environ.get("AGENT_TEAM_LOOKUP", "0") == "1"
# llama.cpp's extra CPU weight buffers keep a second, repacked copy of the weights for faster matrix maths. Off by
# measurement (training/reports/arch_bench.json, five real hive prompts): with it the process peaked at 12.9 GB (the
# 7B coder and a second model each with two copies: over the 10 GB budget and the service's memory cap); without it
# 7.8 GB, in 293 s against 288 s, with the same verdicts, values and conclusions.
REPACK = os.environ.get("AGENT_TEAM_REPACK", "0") == "1"
GGUF_CTX = int(os.environ.get("AGENT_TEAM_CTX", 6144))
GGUF_CTX_BY_MODEL = {"fast": 4096}  # the 1.7B roles (browser, verifier, writer, condenser) need less context
GGUF_MAX_LOADED = int(os.environ.get("AGENT_TEAM_MAX_LOADED", 1 if RAM_GB < 7 else 2))

# Set AGENT_TEAM_NO_ADAPTERS=1 to run the untrained base models (for comparison).
USE_ADAPTERS = os.environ.get("AGENT_TEAM_NO_ADAPTERS", "") != "1"

USER_AGENT = "agent-team/0.1 (personal assistant bot; read-only; no login)"
HTTP_TIMEOUT = 30
THREADS = int(os.environ.get("AGENT_TEAM_THREADS", os.cpu_count() or 4))

# Limits per run.
MAX_STEPS = 10           # plan steps
MAX_FOREACH = 6          # items a for_each step fans out to
MAX_RETRIES = 2          # re-tries of a failed step (with verifier feedback)
BROWSER_MAX_ACTIONS = 14
CODER_MAX_ATTEMPTS = 4
CODE_TIMEOUT = int(os.environ.get("AGENT_TEAM_CODE_TIMEOUT", 1800))
