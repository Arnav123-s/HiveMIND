"""Run cells on llama.cpp: one tiny base in RAM, every cell's weight delta hot-swapped per call.

A label cell answers through a grammar that only allows its labels, so it cannot say anything else.
"""
import atexit
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import skills as S

ROOT = Path(__file__).resolve().parent.parent.parent
CELLS = ROOT / "cells"
GGUF = CELLS / "gguf"
from ..cpu import LOCK as _lock  # noqa: E402 - cells and members take turns on the CPU
_state = {"llm": {}, "tok": {}, "lora": {}, "active": {}}
STATS = {"calls": 0, "seconds": 0.0}


def registry():
    p = CELLS / "registry.json"
    return json.loads(p.read_text()) if p.exists() else {}


def update_registry(skill, fields, replace=False):
    """Write one cell's registry entry under a file lock, re-reading the file inside the lock: two pipelines that
    promote cells at the same time cannot overwrite each other's entries."""
    import fcntl
    CELLS.mkdir(exist_ok=True)
    with open(CELLS / "registry.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        reg = registry()
        reg[skill] = dict(fields) if replace else {**reg.get(skill, {}), **fields}
        tmp = CELLS / "registry.json.tmp"
        tmp.write_text(json.dumps(reg, indent=1))
        tmp.replace(CELLS / "registry.json")
        return reg[skill]


def available(skill):
    c = registry().get(skill)
    return bool(c) and (GGUF / f"{skill}.gguf").exists() and (GGUF / f"{c['base']}.gguf").exists()


def _base(base):
    from llama_cpp import Llama
    from transformers import AutoTokenizer

    from training.cells import BASES
    if base not in _state["llm"]:
        try:  # silence llama.cpp's own logging
            import llama_cpp
            cb = llama_cpp.llama_log_callback(lambda level, text, user_data: None)
            _state["log_cb"] = cb
            llama_cpp.llama_log_set(cb, ctypes.c_void_p(0))
        except Exception:  # noqa: BLE001
            pass
        threads = int(__import__("os").environ.get("AGENT_TEAM_THREADS", 4))
        _state["llm"][base] = Llama(model_path=str(GGUF / f"{base}.gguf"), n_ctx=1024, n_threads=threads, n_batch=512,
                                    use_mmap=True, verbose=False)
        _state["tok"][base] = AutoTokenizer.from_pretrained(BASES[base])
        _state["active"][base] = None
    return _state["llm"][base], _state["tok"][base]


def _use(base, llm_, skill):
    import llama_cpp
    if _state["active"].get(base) == skill:
        return
    if skill is None:
        llama_cpp.llama_set_adapters_lora(llm_._ctx.ctx, None, 0, None)
    else:
        if skill not in _state["lora"]:
            ptr = llama_cpp.llama_adapter_lora_init(llm_._model.model, str(GGUF / f"{skill}.gguf").encode())
            if not ptr:
                raise RuntimeError(f"could not load cell {skill}")
            _state["lora"][skill] = ptr
        arr = (llama_cpp.llama_adapter_lora_p_ctypes * 1)(_state["lora"][skill])
        llama_cpp.llama_set_adapters_lora(llm_._ctx.ctx, arr, 1, (ctypes.c_float * 1)(1.0))
    llm_.reset()
    _state["active"][base] = skill


def _grammar(labels):
    from llama_cpp import LlamaGrammar
    key = "|".join(labels)
    g = _state.setdefault("grammars", {})
    if key not in g:
        g[key] = LlamaGrammar.from_string("root ::= " + " | ".join(json.dumps(x) for x in labels), verbose=False)
    return g[key]


def run(skill, text, edit=True):
    """The cell's answer for one input (a label, or text for text cells)."""
    spec = S.SKILLS[skill]
    reg = registry().get(skill, {})
    base = reg.get("base", "smol135")
    t0 = time.time()
    with _lock:
        llm_, tok = _base(base)
        _use(base, llm_, skill if edit else None)
        msgs = [{"role": "system", "content": spec["instr"]}, {"role": "user", "content": text}]
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        kw = dict(max_tokens=spec.get("max_new", 12), temperature=0.0, stop=["<|im_end|>"])
        if "labels" in spec:
            kw["grammar"] = _grammar(spec["labels"])
        out = llm_.create_completion(prompt, **kw)["choices"][0]["text"].strip()
    STATS["calls"] += 1
    STATS["seconds"] += time.time() - t0
    return out


def label_probs(skill, text, edit=True):
    """The cell's probability for each of its labels, from the logits of each label's first token (the labels of a
    cell that is asked this way must start with different tokens). Reuses the cached prompt prefix: an organizer that
    asks one cell about many elements of the same page only pays for the part that changes."""
    import numpy as np
    spec = S.SKILLS[skill]
    base = registry().get(skill, {}).get("base", "smol135")
    t0 = time.time()
    with _lock:
        llm_, tok = _base(base)
        _use(base, llm_, skill if edit else None)
        msgs = [{"role": "system", "content": spec["instr"]}, {"role": "user", "content": text}]
        ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True)
        if not isinstance(ids, list):
            ids = list(ids["input_ids"])
        n = 0
        for a, b in zip(llm_._input_ids.tolist(), ids):
            if a != b:
                break
            n += 1
        n = min(n, len(ids) - 1)  # always evaluate the last prompt token: its logits are the answer
        llm_.n_tokens = n
        llm_.eval(ids[n:])
        logits = np.ctypeslib.as_array(llm_._ctx.get_logits(), shape=(llm_.n_vocab(),)).astype(np.float64)
        first = [tok.encode(lab, add_special_tokens=False)[0] for lab in spec["labels"]]
        z = logits[first] - logits[first].max()
        p = np.exp(z) / np.exp(z).sum()
    STATS["calls"] += 1
    STATS["seconds"] += time.time() - t0
    return dict(zip(spec["labels"], p.tolist()))


def pick_element(text):
    """Organizer for the page: asks the element_match cell about every element of a pick_element input
    ("GOAL: ...\nELEMENTS:\n[id] kind \"label\"...") and returns the id of the most likely yes."""
    import re
    goal = text.split("\n", 1)[0]
    best, best_p = "", -1.0
    for line in text.split("\n"):
        m = re.match(r"\[(\d+)\]\s+(.*)$", line.strip())
        if not m:
            continue
        p = label_probs("element_match", f"{goal}\nELEMENT: {m.group(2)}")["yes"]
        if p > best_p:
            best, best_p = m.group(1), p
    return best


def orders(text):
    """Organizer for the order cells: which risky kinds the sentence orders (one yes/no cell per kind)."""
    return {k for k in ("spend", "delete", "send", "login", "signup") if run(f"orders_{k}", text) == "yes"}


def unload():
    with _lock:
        for llm_ in _state["llm"].values():
            llm_.close()
        _state.update({"llm": {}, "tok": {}, "lora": {}, "active": {}})


atexit.register(unload)  # close before Python tears down: llama-cpp-python's own cleanup then finds nothing left to free


def missing():
    """Registered cells whose llama.cpp files are not built (git carries only their weight deltas)."""
    return [k for k, c in registry().items() if not (GGUF / f"{k}.gguf").exists() or not (GGUF / f"{c['base']}.gguf").exists()]


def ensure_built(log=print):
    """Build missing cells once (training/cells_build.py, ~2 min), like the members' models download on first use.
    Without them every cell stays off and the bigger members do those jobs. Returns the cells still missing."""
    miss = missing()
    if not miss or os.environ.get("AGENT_TEAM_CELLS", "1") == "0":
        return miss
    log(f"{len(miss)} cells not built yet: building them once (~2 min)")
    try:
        subprocess.run([sys.executable, str(ROOT / "training" / "cells_build.py")], check=True, capture_output=True,
                       text=True, timeout=3600, cwd=ROOT)
    except Exception as e:  # noqa: BLE001 - the team still works without cells
        err = (getattr(e, "stderr", "") or str(e)).strip().splitlines()
        log(f"could not build the cells ({err[-1][:160] if err else type(e).__name__}); their jobs go to the bigger "
            f"members. To build them: python training/cells_build.py")
    return missing()
