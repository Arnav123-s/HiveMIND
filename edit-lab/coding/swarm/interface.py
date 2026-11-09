"""Model interface layer: one contract, any brain.

Every model-backed specialist talks through chat() with OpenAI-style
messages, whatever actually answers:

    chat(messages, model_ref, max_new_tokens=..., temperature=0.0, stop=None)
      -> {"text", "backend", "model_ref",
          "usage": {"prompt_tokens", "completion_tokens"}, "latency_s"}

model_ref forms:
    local:<specialist-name>          a constructed specialist in the registry
    local-hf:<hf-model-id>           local HF model (transformers+PEFT)
    local-hf:<hf-model-id>@<adapter-dir>   ... with a LoRA adapter attached
    local-gguf:<gguf-name>           llama.cpp model (HiveMIND production path)
    api:openai:<model>               OpenAI chat completions
    api:anthropic:<model>            Claude messages API

A role binds to an ordered chain of refs (BINDINGS). chat_for_role tries
them in order: local first, frontier API as the escalation path. API keys
live ONLY in the credentials vault outside the repo
(~/.agent-team/credentials.json, the HiveMIND pattern) or the environment —
never in this tree, never on the board, never in a log.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

VAULT = Path.home() / ".agent-team" / "credentials.json"


class BackendUnavailable(Exception):
    """The backend exists in the design but cannot answer right now."""


class MissingKey(BackendUnavailable):
    """An API backend has no key in the vault."""


def vault_key(service):
    """key-keeper: read one service's key from the vault, or None."""
    env = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(service)
    if env and os.environ.get(env):
        return os.environ[env]
    try:
        data = json.loads(VAULT.read_text())
        return data.get(service) or data.get(f"{service}_api_key")
    except Exception:
        return None


def _approx_tokens(text):
    return max(1, len(text) // 4)


# ---------------------------------------------------------------- backends
class ConstructedBackend:
    """local:<name> — answers by running a constructed specialist."""
    name = "local-constructed"

    def __init__(self, registry):
        self.registry = registry

    def chat(self, messages, ref, **kw):
        spec = self.registry.get(ref.split(":", 1)[1])
        if spec is None or spec.fn is None:
            raise BackendUnavailable(f"no constructed specialist named {ref}")
        task = messages[-1]["content"] if messages else ""
        res = spec.run(task)
        return res.get("output") if isinstance(res.get("output"), str) else json.dumps(res.get("output"))


class HFLocalBackend:
    """local-hf:<id>[@<adapter>] — transformers+PEFT on this machine.

    The binding is real; loading is deferred while the machine is busy
    (LM-heavy work is queued behind the edit-repair job). When loaded, this
    wraps the tree's team/llm.py HF path, which shares one resident base
    and attaches adapters/<role> per specialist.
    """
    name = "local-hf"
    loaded = None  # (model_id, adapter_dir) once loaded

    def chat(self, messages, ref, **kw):
        if self.loaded is None:
            raise BackendUnavailable(
                f"{ref}: local HF backend not loaded (queued — machine busy; "
                "loads when the edit-repair job frees the machine)")
        raise BackendUnavailable("local HF backend load path not wired in the skeleton")


class GGUFBackend:
    """local-gguf:<name> — llama.cpp, HiveMIND's production engine."""
    name = "local-gguf"

    def chat(self, messages, ref, **kw):
        raise BackendUnavailable(f"{ref}: llama.cpp engine not started in the skeleton")


class APIBackend:
    """api:openai:<model> / api:anthropic:<model> — frontier escalation."""
    name = "api"

    def __init__(self, service):
        self.service = service

    def _payload(self, messages, model, max_new_tokens, temperature):
        if self.service == "openai":
            return "https://api.openai.com/v1/chat/completions", {
                "model": model, "messages": messages,
                "max_tokens": max_new_tokens, "temperature": temperature}
        if self.service == "anthropic":
            system = "\n".join(m["content"] for m in messages if m["role"] == "system")
            msgs = [m for m in messages if m["role"] != "system"]
            body = {"model": model, "messages": msgs,
                    "max_tokens": max_new_tokens, "temperature": temperature}
            if system:
                body["system"] = system
            return "https://api.anthropic.com/v1/messages", body
        raise BackendUnavailable(f"unknown api service {self.service}")

    def chat(self, messages, ref, **kw):
        model = ref.split(":", 2)[2]
        key = vault_key(self.service)
        if not key:
            raise MissingKey(f"api:{self.service}: no key in vault ({VAULT}) "
                             f"or ${'OPENAI_API_KEY' if self.service == 'openai' else 'ANTHROPIC_API_KEY'}")
        url, body = self._payload(messages, model,
                                  kw.get("max_new_tokens", 512), kw.get("temperature", 0.0))
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
            "content-type": "application/json",
            "authorization": f"Bearer {key}" if self.service == "openai" else f"x-api-key: {key}",
            **({"anthropic-version": "2023-06-01"} if self.service == "anthropic" else {})})
        with urllib.request.urlopen(req, timeout=120) as r:  # pragma: no cover - needs a key
            data = json.loads(r.read())
        if self.service == "openai":
            return data["choices"][0]["message"]["content"]
        return "".join(b.get("text", "") for b in data.get("content", []))


# ---------------------------------------------------------------- routing
def backend_for(ref, registry=None):
    if ref.startswith("local:"):
        return ConstructedBackend(registry)
    if ref.startswith("local-hf:"):
        return HFLocalBackend()
    if ref.startswith("local-gguf:"):
        return GGUFBackend()
    if ref.startswith("api:"):
        return APIBackend(ref.split(":")[1])
    raise BackendUnavailable(f"unparsable model_ref {ref}")


def chat(messages, model_ref, registry=None, max_new_tokens=512, temperature=0.0, stop=None):
    t0 = time.time()
    backend = backend_for(model_ref, registry)
    text = backend.chat(messages, model_ref, max_new_tokens=max_new_tokens,
                        temperature=temperature, stop=stop)
    prompt = "".join(m["content"] for m in messages)
    return {"text": text, "backend": backend.name, "model_ref": model_ref,
            "usage": {"prompt_tokens": _approx_tokens(prompt),
                      "completion_tokens": _approx_tokens(text or "")},
            "latency_s": round(time.time() - t0, 3)}


# Role -> ordered model_ref chain. Local first; API is the escalation path.
# The coder's local brain is the specialization target of PLAN.md section 6.
BINDINGS = {
    "coder":        ["local-hf:Qwen/Qwen2.5-Coder-1.5B-Instruct", "api:anthropic:claude-sonnet-5"],
    "fixer":        ["local-hf:Qwen/Qwen2.5-Coder-1.5B-Instruct", "api:anthropic:claude-sonnet-5"],
    "test-writer":  ["local-hf:Qwen/Qwen2.5-Coder-1.5B-Instruct", "api:openai:gpt-5.1-codex"],
    "diagnostician": ["local-hf:Qwen/Qwen3-1.7B", "api:anthropic:claude-sonnet-5"],
    "api-shape-planner": ["local-hf:Qwen/Qwen3-1.7B", "api:openai:gpt-5.1"],
    "semantic-reviewer": ["local-hf:Qwen/Qwen3-1.7B", "api:anthropic:claude-sonnet-5"],
    "semantic-checker":  ["local-hf:Qwen/Qwen3-1.7B", "api:anthropic:claude-sonnet-5"],
    # phase 2 (field coverage, PLAN.md section 15): model-bound roles of
    # the expansion niches. Registered now; loading queued per PLAN §14.
    "code-explainer":    ["local-hf:Qwen/Qwen3-1.7B", "api:anthropic:claude-sonnet-5"],
    "docstring-writer":  ["local-hf:Qwen/Qwen2.5-Coder-1.5B-Instruct", "api:anthropic:claude-sonnet-5"],
    "refactor-suggester": ["local-hf:Qwen/Qwen3-1.7B", "api:anthropic:claude-sonnet-5"],
    "sql-writer":        ["local-hf:Qwen/Qwen2.5-Coder-1.5B-Instruct", "api:openai:gpt-5.1-codex"],
    "shell-writer":      ["local-hf:Qwen/Qwen2.5-Coder-1.5B-Instruct", "api:anthropic:claude-sonnet-5"],
    "commit-message-writer": ["local-hf:Qwen/Qwen3-1.7B", "api:openai:gpt-5.1"],
    "code-translator":   ["local-hf:Qwen/Qwen2.5-Coder-1.5B-Instruct", "api:anthropic:claude-sonnet-5"],
    "api-usage-advisor": ["local-hf:Qwen/Qwen3-1.7B", "api:anthropic:claude-sonnet-5"],
}


def chat_for_role(role, messages, registry=None, board=None, **kw):
    """Try the role's binding chain in order; record escalations on the board."""
    last = None
    for i, ref in enumerate(BINDINGS.get(role, [])):
        try:
            out = chat(messages, ref, registry=registry, **kw)
            if board is not None:
                board.event("interface", "answer", f"{role} via {ref}")
            return out
        except BackendUnavailable as e:
            last = e
            if board is not None:
                board.event("interface", "escalate" if i else "miss", f"{role}: {ref} -> {e}")
    raise BackendUnavailable(f"role {role}: every binding unavailable (last: {last})")


def chat_or_queue(role, messages, registry=None, board=None, **kw):
    """Order-facing variant of chat_for_role (phase 4 audit): total
    unavailability never raises into the caller. The job is posted to
    the board as a queued job and a gap envelope is returned —
    queueing and growth are the only failure modes an order can meet;
    refusal is not one of them. chat_for_role keeps its raise for
    callers (the demo) that assert the escalation signal itself."""
    try:
        out = chat_for_role(role, messages, registry=registry,
                            board=board, **kw)
        return {"ok": True, "output": out, "gap": None,
                "evidence": f"role {role} answered"}
    except BackendUnavailable as e:
        jid = None
        if board is not None:
            jid = board.post("interface", f"queued role job: {role}",
                             {"role": role, "reason": str(e)})
            board.event("interface", "queued", f"job {jid}: {role}")
        return {"ok": False, "output": None, "gap": "backend-unloaded",
                "queued_job": jid,
                "evidence": f"every binding unavailable; job queued "
                            f"(id {jid}), no human asked: {e}"}
