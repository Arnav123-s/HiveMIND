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
GGUF_ROSTER = {
    "coordinator": BRAIN, "researcher": BRAIN, "verifier": BRAIN, "writer": BRAIN, "browser": BRAIN,
    "coder": os.environ.get("AGENT_TEAM_GGUF_CODER", "coder7b"),
}
if os.environ.get("AGENT_TEAM_ROSTER"):  # e.g. '{"browser": "fast+browser"}' = 1.7B + the browser's own weight edit
    import json as _json
    GGUF_ROSTER.update(_json.loads(os.environ["AGENT_TEAM_ROSTER"]))
GGUF_CTX = int(os.environ.get("AGENT_TEAM_CTX", 6144))

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
