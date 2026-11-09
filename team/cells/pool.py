"""Many cells at once: a pool of worker processes, each running the cell runtime on one CPU thread.

The cells' base model file is memory-mapped, so the workers share its pages: N workers cost N small working sets
(context and the deltas they load), not N models. A batch of cell questions (every search result of a search, every
pair of claims, every element of a page, every fact against its sub-question) is spread over the workers and
answered in parallel. The main process holds the CPU lock meanwhile, so the bigger members never compete with the
pool for the cores. AGENT_TEAM_CELL_WORKERS sets the number of workers (1 = no pool: the cells answer in turn).
"""
import atexit
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

MIN_BATCH = 4  # fewer questions than this are answered in the main process (starting work costs more than it saves)
_POOL = {"ex": None, "n": 0}
STATS = {"batches": 0, "questions": 0}


def workers():
    return max(1, int(os.environ.get("AGENT_TEAM_CELL_WORKERS", min(4, os.cpu_count() or 1))))


def _init():
    os.environ["AGENT_TEAM_THREADS"] = "1"


def _one(job):
    kind, skill, text = job
    from . import runtime
    return runtime.label_probs(skill, text) if kind == "probs" else runtime.run(skill, text)


def _executor():
    n = workers()
    if _POOL["ex"] is None or _POOL["n"] != n:
        shutdown()
        # spawn, not fork: a forked copy of a process that already holds a llama.cpp model and its threads can hang
        _POOL["ex"] = ProcessPoolExecutor(max_workers=n, mp_context=multiprocessing.get_context("spawn"), initializer=_init)
        _POOL["n"] = n
    return _POOL["ex"]


def shutdown():
    if _POOL["ex"] is not None:
        _POOL["ex"].shutdown(wait=True, cancel_futures=True)
        _POOL["ex"], _POOL["n"] = None, 0


atexit.register(shutdown)


def map(skill, texts, probs=False):  # noqa: A001 - the pool's map
    """The cell's answer (or label probabilities) for every text, in order, answered in parallel when worth it."""
    from . import runtime
    texts = list(texts)
    if len(texts) < MIN_BATCH or workers() <= 1:
        return [runtime.label_probs(skill, t) if probs else runtime.run(skill, t) for t in texts]
    from ..cpu import LOCK
    kind = "probs" if probs else "run"
    n = workers()
    with LOCK:  # the pool has the cores: no member generates meanwhile
        out = list(_executor().map(_one, [(kind, skill, t) for t in texts], chunksize=max(1, len(texts) // (n * 4))))
    STATS["batches"] += 1
    STATS["questions"] += len(texts)
    return out
