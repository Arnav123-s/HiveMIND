"""Model pool: loads each base model once (CPU, bf16) and switches the
specialist's own trained weights (LoRA delta) in and out per call."""
import json
import re
import threading
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList

from . import config

torch.set_num_threads(config.THREADS)

_lock = threading.Lock()
_bases = {}  # model_id -> {"tok", "model", "adapters": set()}
STATS = {"calls": 0, "tokens_out": 0, "seconds": 0.0}
RECORDER = None  # callable(specialist, messages, output) - the hive records every call for self-training


def _load(model_id):
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


class StopWhenDone(StoppingCriteria):
    """Stop as soon as the reply is complete: a JSON object closed, or a code block closed."""

    def __init__(self, tok, start, mode, prefix=""):
        self.tok, self.start, self.mode, self.prefix = tok, start, mode, prefix

    def __call__(self, input_ids, scores, **kw):
        n = input_ids.shape[1] - self.start
        if n < 2 or n % 4:
            return False
        text = self.prefix + self.tok.decode(input_ids[0, self.start:], skip_special_tokens=True)
        if self.mode == "json":
            return _closes_from_start(text)
        if self.mode == "code":
            return text.count("```") >= 2
        return False


def chat(specialist, messages, max_new_tokens=512, adapter=True, temperature=0.0, prefix="", stop=None):
    """Run one chat completion as `specialist`. Greedy by default.
    `prefix` is forced as the start of the reply (e.g. "{" to force a JSON object)."""
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
            gen_kwargs["stopping_criteria"] = StoppingCriteriaList(
                [StopWhenDone(tok, ids["input_ids"].shape[1], stop, prefix)])
        if temperature > 0:
            gen_kwargs.update(do_sample=True, temperature=temperature, top_p=0.9)
        else:
            gen_kwargs.update(do_sample=False, temperature=None, top_p=None, top_k=None)
        t0 = time.time()
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
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if RECORDER is not None:
        try:
            RECORDER(specialist, messages, text)
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
    for o, c in (("{", "}"), ("[", "]")):
        blob = _balanced(text, o, c)
        if blob is None:
            continue
        for attempt in (blob, re.sub(r",\s*([}\]])", r"\1", blob)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError:
                pass
    return None


def chat_json(specialist, messages, max_new_tokens=512, adapter=True, retries=1, prefix="{"):
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
