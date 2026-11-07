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
