"""Model pool: loads each base model once (CPU, bf16) and switches the
specialist's own trained weights (LoRA delta) in and out per call."""
import atexit
import json
import os
import re
import threading
import time

from transformers import AutoTokenizer

from . import config

# torch is imported only on the PyTorch path, so the llama.cpp engine does not pay for it in RAM.

from .cpu import LOCK as _lock  # noqa: E402 - one CPU lock for members and cells
_bases = {}  # model_id -> {"tok", "model", "adapters": set()}
STATS = {"calls": 0, "tokens_out": 0, "seconds": 0.0}
RECORDER = None  # callable(specialist, messages, output, **info) for every thread (set_recorder: this thread only)
_local = threading.local()


def set_recorder(fn):
    """Record this thread's model calls (each swarm job runs in its own thread and keeps its own calls.jsonl)."""
    _local.recorder = fn


def _recorder():
    return getattr(_local, "recorder", None) or RECORDER


class _PerThread:
    """A dict per thread: concurrent swarm jobs route their own steps."""

    def _d(self):
        if not hasattr(_local, "route"):
            _local.route = {}
        return _local.route

    def get(self, k, default=None):
        return self._d().get(k, default)

    def __setitem__(self, k, v):
        self._d()[k] = v

    def __getitem__(self, k):
        return self._d()[k]

    def __contains__(self, k):
        return k in self._d()

    def pop(self, k, default=None):
        return self._d().pop(k, default)


ROUTE = _PerThread()  # role -> specialised member the router picked for the current step (e.g. browser -> browser_hf)


def _load(model_id):
    import torch
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(config.THREADS)
    if model_id not in _bases:
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16)
        model.eval()
        _bases[model_id] = {"tok": tok, "model": model, "adapters": set()}
    return _bases[model_id]


def _attach_adapter(entry, name):
    """Attach adapters/<name> to the base if it exists. Returns adapter name or None."""
    path = config.ADAPTERS / name
    if not config.USE_ADAPTERS or not (path / "adapter_config.json").exists():
        return None
    if name not in entry["adapters"]:
        from peft import PeftModel
        if not entry["adapters"]:
            entry["model"] = PeftModel.from_pretrained(entry["model"], str(path), adapter_name=name)
        else:
            entry["model"].load_adapter(str(path), adapter_name=name)
        entry["model"].eval()
        entry["adapters"].add(name)
    return name


def _stop_criteria(tok, start, mode, prefix=""):
    """Stop as soon as the reply is complete: a JSON object closed, or a code block closed."""
    from transformers import StoppingCriteria, StoppingCriteriaList

    class StopWhenDone(StoppingCriteria):
        def __call__(self, input_ids, scores, **kw):
            return _done(tok, input_ids, start, mode, prefix)

    return StoppingCriteriaList([StopWhenDone()])


def _done(tok, input_ids, start, mode, prefix):
    from . import stop as _stop
    if _stop.requested():  # kill switch, per token
        return True
    if True:
        n = input_ids.shape[1] - start
        if n < 2 or n % 4:
            return False
        text = prefix + tok.decode(input_ids[0, start:], skip_special_tokens=True)
        if mode == "json":
            return _closes_from_start(text)
        if mode == "code":
            return text.count("```") >= 2
        return False


# ---------------------------------------------------------------- engine v2: llama.cpp
_gguf = {}      # (model, lora) -> Llama
_gguf_tok = {}  # tokenizer repo -> HF tokenizer (only for building the exact chat prompt)
_grammar = None


def gguf_available():
    if config.ENGINE == "hf":
        return False
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        if config.ENGINE == "gguf":
            raise
        return False
    from huggingface_hub import try_to_load_from_cache
    for spec in config.GGUF_ROSTER.values():
        repo, fname, _ = config.GGUF_MODELS[spec.split("+")[0]]
        if not isinstance(try_to_load_from_cache(repo, fname), str):
            if config.ENGINE == "gguf":
                from huggingface_hub import hf_hub_download
                hf_hub_download(repo, fname)
                continue
            return False
    return True


_USE_GGUF = None


def use_gguf():
    global _USE_GGUF
    if _USE_GGUF is None:
        _USE_GGUF = gguf_available()
    return _USE_GGUF


_lru = []  # model names, most recent last
_active_lora = {}  # model name -> lora name currently set on its context
_lora_ptrs = {}  # (model name, lora name) -> adapter pointer


_quiet = None


def _silence_llama_cpp():
    """llama.cpp logs every tensor it touches to stderr; keep the terminal readable."""
    global _quiet
    if _quiet is None:
        import ctypes

        import llama_cpp

        @llama_cpp.llama_log_callback
        def _noop(level, text, user_data):
            pass

        _quiet = _noop  # keep a reference so it is not garbage-collected
        llama_cpp.llama_log_set(_quiet, ctypes.c_void_p(0))


def _cvec_for(specialist):
    """A specialist's internal edit: a direction added to one layer's residual stream (training/steer.py)."""
    raw = os.environ.get(f"AGENT_TEAM_CVEC_{specialist.upper()}")
    if raw:
        return json.loads(raw)
    path = config.ROOT / "adapters_gguf" / f"{specialist}.cvec.json"
    if config.USE_ADAPTERS and path.exists():
        return json.loads(path.read_text())
    return None


def reset_edits():
    """Forget which edits are active (forces re-applying them on the next call)."""
    for k in list(_active_lora):
        _active_lora[k] = "__unknown__"


def _set_cvec(llm_, cvec):
    import ctypes

    import llama_cpp
    model = llm_._model.model
    n_embd, n_layer = llama_cpp.llama_model_n_embd(model), llama_cpp.llama_model_n_layer(model)
    if not cvec:
        llama_cpp.llama_set_adapter_cvec(llm_._ctx.ctx, None, 0, n_embd, -1, -1)
        return
    il = int(cvec["layer"])  # llama.cpp counts layers from 1; the vector is added to that layer's output
    buf = (ctypes.c_float * (n_embd * n_layer))()
    vec = cvec["vector"]
    for i in range(n_embd):  # the stored vector already includes its strength (alpha)
        buf[(il - 1) * n_embd + i] = float(vec[i])
    llama_cpp.llama_set_adapter_cvec(llm_._ctx.ctx, buf, n_embd * n_layer, n_embd, il, il)


def _set_lora(name, llm_, lora, cvec=None):
    """Hot-swap a specialist's edits on the shared base: one copy of the base weights in RAM.
    lora = its weight edit (adapters_gguf/<x>.gguf); cvec = its internal edit (direction at one layer)."""
    import ctypes

    import llama_cpp
    state = (lora, json.dumps(cvec)[:64] + str(len(json.dumps(cvec))) if cvec else None)
    if _active_lora.get(name) == state:
        return
    if lora is None:
        llama_cpp.llama_set_adapters_lora(llm_._ctx.ctx, None, 0, None)
    else:
        key = (name, lora)
        if key not in _lora_ptrs:
            path = config.ROOT / "adapters_gguf" / f"{lora}.gguf"
            ptr = llama_cpp.llama_adapter_lora_init(llm_._model.model, str(path).encode())
            if not ptr:
                raise RuntimeError(f"could not load weight edit {path}")
            _lora_ptrs[key] = ptr
        arr = (llama_cpp.llama_adapter_lora_p_ctypes * 1)(_lora_ptrs[key])
        scales = (ctypes.c_float * 1)(1.0)
        llama_cpp.llama_set_adapters_lora(llm_._ctx.ctx, arr, 1, scales)
    _set_cvec(llm_, cvec)
    llm_.reset()  # cached prompt states were computed with the other weights
    _active_lora[name] = state


def _gguf_model(specialist, adapter):
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama
    spec = config.GGUF_ROSTER[specialist]
    name, _, lora = spec.partition("+")
    repo, fname, tok_repo = config.GGUF_MODELS[name]
    if not (lora and adapter and config.USE_ADAPTERS and (config.ROOT / "adapters_gguf" / f"{lora}.gguf").exists()):
        lora = None
    _silence_llama_cpp()
    if name not in _gguf:
        while len(_gguf) >= config.GGUF_MAX_LOADED:  # keep RAM low: unload the least recently used model
            old = _lru.pop(0)
            _gguf.pop(old).close()
            _active_lora.pop(old, None)
            for k in [k for k in _lora_ptrs if k[0] == old]:
                _lora_ptrs.pop(k)
        # mmap: the weights file is mapped, not copied, and pages are shared with the OS cache
        kv = dict(flash_attn=True, type_k=8, type_v=8) if config.KV_8BIT else {}  # 8 = GGML_TYPE_Q8_0
        _gguf[name] = Llama(model_path=hf_hub_download(repo, fname), n_ctx=config.GGUF_CTX_BY_MODEL.get(name, config.GGUF_CTX),
                            n_threads=config.THREADS, n_batch=512, use_mmap=True, verbose=False, **kv)
        _active_lora[name] = None
    if name in _lru:
        _lru.remove(name)
    _lru.append(name)
    _set_lora(name, _gguf[name], lora, _cvec_for(specialist) if adapter else None)
    if tok_repo not in _gguf_tok:
        _gguf_tok[tok_repo] = AutoTokenizer.from_pretrained(tok_repo)
    return _gguf[name], _gguf_tok[tok_repo]


def unload_all():
    """Free every loaded model (e.g. before handing the CPU and RAM to a subprocess)."""
    for name in list(_gguf):
        _gguf.pop(name).close()
    _lru.clear()
    _active_lora.clear()
    _lora_ptrs.clear()


atexit.register(unload_all)  # close before Python tears down (llama-cpp-python's __del__ fails after)


def _json_grammar():
    global _grammar
    if _grammar is None:
        from llama_cpp.llama_grammar import JSON_GBNF, LlamaGrammar
        _grammar = LlamaGrammar.from_string(JSON_GBNF, verbose=False)
    return _grammar


def _chat_gguf(specialist, messages, max_new_tokens, adapter, temperature, prefix, stop):
    from . import health
    health.cool_down()  # a CPU above 90 C waits until it is under 80 C before the next model call
    llm_, tok = _gguf_model(specialist, adapter)
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    kw = dict(max_tokens=max_new_tokens, temperature=temperature, top_p=0.9 if temperature else 1.0,
              repeat_penalty=1.0)  # a penalty stops the model copying page text verbatim (evidence)
    head = ""
    if stop == "json":
        kw["grammar"] = _json_grammar()  # output is valid JSON by construction
    elif stop == "code":
        head = "```python\n"
        prompt += head
        kw["stop"] = ["```"]
    else:
        prompt += prefix
        head = prefix
    from llama_cpp import StoppingCriteriaList

    from . import stop as _stop
    kw["stopping_criteria"] = StoppingCriteriaList([lambda ids, logits: _stop.requested()])  # kill switch, per token
    t0 = time.time()
    out = llm_.create_completion(prompt, **kw)
    text = out["choices"][0]["text"]
    STATS["calls"] += 1
    STATS["tokens_out"] += out.get("usage", {}).get("completion_tokens", 0)
    STATS["seconds"] += time.time() - t0
    if stop == "code":
        return head + text.rstrip() + "\n```"
    return head + text


def chat(specialist, messages, max_new_tokens=512, adapter=True, temperature=0.0, prefix="", stop=None):
    """Run one chat completion as `specialist`. Greedy by default.
    `prefix` is forced as the start of the reply (e.g. "{" to force a JSON object)."""
    from . import stop as _stop
    _stop.check()
    specialist = ROUTE.get(specialist, specialist)
    if use_gguf():
        with _lock:
            t0 = time.time()
            text = _chat_gguf(specialist, messages, max_new_tokens, adapter, temperature, prefix, stop)
            secs = time.time() - t0
        _stop.check()  # a reply cut off by the kill switch is never used
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        rec = _recorder()
        if rec is not None:
            try:  # time and model per call: what each task costs, by member
                rec(specialist, messages, text, seconds=round(secs, 2), model=config.GGUF_ROSTER.get(specialist))
            except Exception:  # noqa: BLE001
                pass
        return text
    model_id = config.SPECIALISTS[specialist]
    with _lock:
        entry = _load(model_id)
        name = _attach_adapter(entry, specialist) if adapter else None
        tok, model = entry["tok"], entry["model"]
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False) + prefix
        ids = tok(prompt, return_tensors="pt")
        gen_kwargs = dict(max_new_tokens=max_new_tokens, pad_token_id=tok.eos_token_id)
        if stop:
            gen_kwargs["stopping_criteria"] = _stop_criteria(tok, ids["input_ids"].shape[1], stop, prefix)
        if temperature > 0:
            gen_kwargs.update(do_sample=True, temperature=temperature, top_p=0.9)
        else:
            gen_kwargs.update(do_sample=False, temperature=None, top_p=None, top_k=None)
        t0 = time.time()
        import torch
        with torch.inference_mode():
            if entry["adapters"]:
                if name:
                    model.set_adapter(name)
                    out = model.generate(**ids, **gen_kwargs)
                else:
                    with model.disable_adapter():
                        out = model.generate(**ids, **gen_kwargs)
            else:
                out = model.generate(**ids, **gen_kwargs)
        new = out[0, ids["input_ids"].shape[1]:]
        STATS["calls"] += 1
        STATS["tokens_out"] += int(new.shape[0])
        STATS["seconds"] += time.time() - t0
        text = prefix + tok.decode(new, skip_special_tokens=True)
    _stop.check()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    rec = _recorder()
    if rec is not None:
        try:
            rec(specialist, messages, text)
        except Exception:  # noqa: BLE001 - recording must never break a run
            pass
    return text


# ---------- JSON helpers: small models need forgiving parsing ----------

def _balanced(text, open_ch, close_ch):
    start = text.find(open_ch)
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        start = text.find(open_ch, start + 1)
    return None


def _closes_from_start(text):
    """True once the JSON object that starts the text is complete."""
    t = text.lstrip()
    if not t.startswith("{"):
        return False
    depth, in_str, esc = 0, False, False
    for c in t:
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return True
    return False


def parse_json(text):
    """Extract the first JSON object (or array) from model output."""
    text = re.sub(r"```(?:json)?", "", text)
    obj_first = "{" in text and ("[" not in text or text.index("{") < text.index("["))
    for o, c in (("{", "}"), ("[", "]")):
        if o == "[" and obj_first:  # the reply is a broken object: repair it before settling for a list inside it
            fixed = _repair_cell(text)
            if fixed is not None:
                return fixed
        blob = _balanced(text, o, c)
        if blob is None:
            continue
        for attempt in (blob, re.sub(r",\s*([}\]])", r"\1", blob)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError:
                pass
    return None if obj_first else _repair_cell(text)


def _repair_cell(text):
    """Last resort: the json_repair cell rewrites the broken JSON (only if it measured better than the code rules).
    Only for text that holds a broken object ('{' and a key) - the cell turns ANY text into JSON - and every key of
    the repair must be in the original text: a repair may fix syntax, never invent content."""
    if not text.strip() or len(text) > 600 or "{" not in text or ":" not in text:
        return None
    try:
        from .cells import use
        if not use.on("json_repair"):
            return None
        fixed = json.loads(use.ask("json_repair", text.strip()))
        keys = list(fixed) if isinstance(fixed, dict) else []
        if not keys or any(str(k) not in text for k in keys):
            return None
        return fixed
    except Exception:  # noqa: BLE001 - a failed repair is just "no JSON"
        return None


def cut_off(out):
    """The reply stopped at the token limit inside the JSON (it never closed), not a format mistake."""
    t = (out or "").rstrip()
    return bool(t) and t[0] in "{[" and t[-1] not in "}]"


def chat_json(specialist, messages, max_new_tokens=512, adapter=True, retries=1, prefix="{"):
    out = chat(specialist, messages, max_new_tokens, adapter, prefix=prefix, stop="json")
    data = parse_json(out)
    if data is None and cut_off(out) and max_new_tokens < 2048:
        # the browser's answer with three quotes and their evidence passed its 160-token limit; told "not valid
        # JSON" with the same limit it was cut off again, 20 times, until it ran out of actions
        max_new_tokens = min(2048, max_new_tokens * 2)
        out = chat(specialist, messages, max_new_tokens, adapter, prefix=prefix, stop="json")
        data = parse_json(out)
    tries = 0
    while data is None and tries < retries:
        tries += 1
        messages = messages + [{"role": "assistant", "content": out},
                               {"role": "user", "content": "That was not valid JSON. Reply again with only the JSON."}]
        out = chat(specialist, messages, max_new_tokens, adapter, prefix=prefix, stop="json")
        data = parse_json(out)
    return data, out
