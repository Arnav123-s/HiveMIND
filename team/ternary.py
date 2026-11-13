"""Members that are ternary models: every weight is -1, 0 or +1 (1.58 bits), the kind of net BitNet b1.58 named.

Found 2026-11-13: the nets this hive grew from nothing on a CPU stay weak, but ternary models of every size have
been published, and a llama.cpp with kernels for them (ik_llama.cpp) runs them fast on a plain CPU. Measured on
4 cores (AVX-512) with the members' own prompt of 608 pieces:

    Ternary-Bonsai-2 2B   0.5 GB file, 1.0 GB in memory   reads 330 pieces/s, writes 27/s
    Ternary-Bonsai-2 4B   1.1 GB file, 1.9 GB             reads 132/s,        writes 12/s
    Ternary-Bonsai-2 9B   2.3 GB file, 3.0 GB             reads 76/s,         writes 7/s
    (the hive's 7B coder at 4 bits: 4.7 GB file, writes 3 to 4/s)

So a member is a name from MODELS, optionally with a weight edit the hive trained itself ("t17+gen3": the 1.7B
with the adapter of generation 3, training/grow.py). HIVE_MEMBERS names who sits where in team/solo.py:

    HIVE_MEMBERS=t9,t9,t4 AGENT_TEAM_SOLO=2 AGENT_TEAM_SOLO_ALONE=1 python -m team "task"

Each model is served by one llama-server on its own port, started the first time a member needs it and left
running for the next task (python -m team.ternary stop ends them). Microsoft's own bitnet-b1.58-2B-4T is "bitnet":
on this runtime it answers properly, where Microsoft's runtime looped (team/bitnet.py, now removed).

    python -m team.ternary install        build the runtime (once, about 25 minutes on 4 cores)
    python -m team.ternary fetch [t9 ...]  download the models of HIVE_MEMBERS (or those named)
    python -m team.ternary ask t9 "..."   one question to one model
    python -m team.ternary stop
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MODELS = {  # name: (repository, file, pieces of context it is served with)
    "t2": ("prism-ml/Ternary-Bonsai-2-2B-gguf", "Ternary-Bonsai-2-2B-PQ2_0.gguf"),
    "t4": ("prism-ml/Ternary-Bonsai-2-4B-gguf", "Ternary-Bonsai-2-4B-PQ2_0.gguf"),
    "t9": ("prism-ml/Ternary-Bonsai-2-9B-gguf", "Ternary-Bonsai-2-9B-PQ2_0.gguf"),
    "t27": ("prism-ml/Ternary-Bonsai-2-27B-gguf", "Ternary-Bonsai-2-27B-PQ2_0.gguf"),
    "t17": ("prism-ml/Ternary-Bonsai-1.7B-gguf", "Ternary-Bonsai-1.7B-PQ2_0.gguf"),  # the one the hive can train (its unpacked weights are published)
    "bitnet": ("tdh111/bitnet-b1.58-2B-4T-GGUF", "bitnet1582b4t-iq2_bn.gguf"),
}
RUNTIME = "https://github.com/ikawrakow/ik_llama.cpp.git"
PIN = "7aa7e01482db892b023bb9aace9a40567ab5297a"  # the commit every number above was measured on
HOME = Path(os.environ.get("HIVE_TERNARY_HOME", Path.home() / ".cache" / "hive" / "ternary"))
ADAPTERS = Path(__file__).resolve().parent.parent / "cells" / "members"  # <name>.gguf: weight edits the hive trained
CTX = int(os.environ.get("HIVE_TERNARY_CTX", 12288))
END = "<|eot_id|>"  # Microsoft's BitNet answers only in its own format, written out by hand


def binary():
    return Path(os.environ.get("HIVE_TERNARY_BIN", HOME / "ik_llama.cpp" / "build" / "bin" / "llama-server"))


def install(log=print):
    """Build the runtime for this machine's CPU. Skipped when the binary is there."""
    if binary().exists():
        return binary()
    src = HOME / "ik_llama.cpp"
    HOME.mkdir(parents=True, exist_ok=True)
    if not (src / ".git").exists():
        subprocess.run(["git", "init", "-q", str(src)], check=True)
        subprocess.run(["git", "-C", str(src), "remote", "add", "origin", RUNTIME], check=True)
    subprocess.run(["git", "-C", str(src), "fetch", "-q", "--depth", "1", "origin", PIN], check=True)
    subprocess.run(["git", "-C", str(src), "checkout", "-q", "FETCH_HEAD"], check=True)
    log("ternary: building the runtime (about 25 minutes on 4 cores)")
    subprocess.run(["cmake", "-S", str(src), "-B", str(src / "build"), "-DCMAKE_BUILD_TYPE=Release", "-DGGML_NATIVE=ON", "-DLLAMA_CURL=OFF",
                    "-DBUILD_SHARED_LIBS=OFF"],
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["cmake", "--build", str(src / "build"), "--config", "Release", "-j", str(os.cpu_count() or 4), "--target", "llama-server"],
                   check=True, stdout=subprocess.DEVNULL)
    return binary()


def split(member):
    """'t17+gen3' -> ('t17', 'gen3'); 't9' -> ('t9', '')."""
    base, _, edit = member.partition("+")
    if base not in MODELS:
        raise ValueError(f"no ternary model named {base!r}; there are {sorted(MODELS)}")
    return base, edit


def weights(base):
    from huggingface_hub import hf_hub_download
    repo, file = MODELS[base]
    return hf_hub_download(repo, file)


def adapter(member):
    base, edit = split(member)
    return ADAPTERS / f"{base}+{edit}.gguf" if edit else None


def port(member):
    """Each member's server has a port of its own, the same in every process (so the next task finds it running)."""
    base, edit = split(member)
    known = sorted(MODELS).index(base)
    return 8090 + known + 10 * (1 + sum(map(ord, edit)) % 80 if edit else 0)


def _get(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except (OSError, ValueError):
        return None


def up(member, wait=600):
    """The address of the member's server, started if it is not running."""
    at = f"http://127.0.0.1:{port(member)}"
    if (_get(at + "/health") or {}).get("status") == "ok":
        return at
    if not binary().exists():
        raise RuntimeError("the ternary runtime is not built on this machine: python -m team.ternary install")
    base, edit = split(member)
    cmd = [str(binary()), "-m", weights(base), "-t", str(os.environ.get("AGENT_TEAM_THREADS", os.cpu_count() or 4)), "-c", str(CTX),
           "--port", str(port(member)), "--host", "127.0.0.1", "-rtr", "--parallel", "1"]
    if base != "bitnet":
        cmd.append("--jinja")
    else:
        cmd.append("--special")
    if edit:
        if not adapter(member).exists():
            raise RuntimeError(f"no weight edit {adapter(member)}: python training/grow.py fetch")
        cmd += ["--lora", str(adapter(member))]
    HOME.mkdir(parents=True, exist_ok=True)
    log = open(HOME / f"{member.replace('+', '_')}.log", "ab")
    subprocess.Popen(cmd, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < wait:
        if (_get(at + "/health") or {}).get("status") == "ok":
            return at
        time.sleep(1)
    raise RuntimeError(f"the server of {member} did not come up in {wait} s; see {HOME / (member.replace('+', '_') + '.log')}")


def _post(url, body, timeout=1800):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def chat(member, messages, max_new_tokens=700, temperature=0.0):
    """The member's reply to a conversation. When the conversation no longer fits its window, the oldest program and
    what it printed go first; the orders and the task stay."""
    at, messages = up(member), list(messages)
    base, _ = split(member)
    for _ in range(8):
        try:
            if base == "bitnet":
                text = "".join(f"{m['role'].capitalize()}: {m['content']}{END}" for m in messages) + "Assistant: "
                out = _post(at + "/completion", {"prompt": text, "n_predict": max_new_tokens, "temperature": temperature,
                                                 "stop": [END, "\nUser:", "<|end_of_text|>"], "cache_prompt": True})
                return out.get("content", "").split(END)[0].strip()
            out = _post(at + "/v1/chat/completions", {"messages": messages, "max_tokens": max_new_tokens, "temperature": temperature,
                                                      "top_p": 0.8 if temperature else 1.0, "top_k": 20 if temperature else 0, "cache_prompt": True,
                                                      "chat_template_kwargs": {"enable_thinking": False}})
            return (out["choices"][0]["message"].get("content") or "").strip()
        except urllib.error.HTTPError as e:
            if e.code not in (400, 413, 500) or len(messages) <= 3:
                raise
            del messages[2:4]
    raise RuntimeError(f"{member}: the conversation does not fit its window even with only the task left")


def stop():
    for name in MODELS:
        subprocess.run(["pkill", "-f", f"llama-server.*--port {port(name)}\\b"], check=False)
    subprocess.run(["pkill", "-f", str(binary())], check=False)


def roster():
    """Who sits where: HIVE_MEMBERS=t9,t9,t4 (the last one named also takes every later seat). 'coder' is the hive's
    7B coder at 4 bits through llama.cpp, as before. Empty: every member is 'coder'."""
    return [w.strip() for w in os.environ.get("HIVE_MEMBERS", "").split(",") if w.strip()]


def seat(n):
    who = roster()
    return (who[n - 1] if n <= len(who) else who[-1]) if who else "coder"


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["install"]:
        print(install())
    elif a[:1] == ["stop"]:
        stop()
    elif a[:1] == ["fetch"]:  # the files of every member named in HIVE_MEMBERS (or given), so that a sitting does not wait for them
        for who in a[1:] or roster():
            if who != "coder":
                print(who, weights(split(who)[0]))
    elif a[:1] == ["ask"] and len(a) >= 3:
        t0 = time.time()
        print(chat(a[1], [{"role": "user", "content": " ".join(a[2:])}]))
        print(f"[{time.time() - t0:.0f} s]", file=sys.stderr)
    else:
        print(__doc__)
