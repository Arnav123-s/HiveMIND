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
    "t40": ("prism-ml/Ternary-Bonsai-4B-gguf", "Ternary-Bonsai-4B-PQ2_0.gguf"),  # a bigger DNA that can be trained too (1.0 GB packed)
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


def source():
    """The runtime's source at the pinned commit (the build needs it, and so does turning a trained edit into a file
    the runtime reads: convert_lora_to_gguf.py)."""
    src = HOME / "ik_llama.cpp"
    if (src / "convert_lora_to_gguf.py").exists():
        return src
    HOME.mkdir(parents=True, exist_ok=True)
    if not (src / ".git").exists():
        subprocess.run(["git", "init", "-q", str(src)], check=True)
        subprocess.run(["git", "-C", str(src), "remote", "add", "origin", RUNTIME], check=True)
    subprocess.run(["git", "-C", str(src), "fetch", "-q", "--depth", "1", "origin", PIN], check=True)
    subprocess.run(["git", "-C", str(src), "checkout", "-q", "FETCH_HEAD"], check=True)
    return src


def install(log=print):
    """Build the runtime for this machine's CPU. Skipped when the binary is there."""
    if binary().exists():
        return binary()
    src = source()
    log("ternary: building the runtime (about 25 minutes on 4 cores)")
    subprocess.run(["cmake", "-S", str(src), "-B", str(src / "build"), "-DCMAKE_BUILD_TYPE=Release", "-DGGML_NATIVE=ON", "-DLLAMA_CURL=OFF",
                    "-DBUILD_SHARED_LIBS=OFF"], check=True, stdout=subprocess.DEVNULL)
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
    """One server for each base model, the same port in every process (so the next task finds it running). All the
    cells of a body share their base's server: the base is in memory once, the cells are its weight edits."""
    return 8090 + sorted(MODELS).index(split(member)[0])


def _get(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except (OSError, ValueError):
        return None


ENGRAMS = Path(os.environ.get("HIVE_ENGRAMS_HOME", Path(__file__).resolve().parent.parent / "cells" / "engrams"))


def edits_here(base):
    """{name: file} of every weight edit of this base on this machine: its cells (cells/members/<base>+<name>.gguf) and
    its engrams (cells/engrams/, team/engram.py; their names begin with e)."""
    return {p.stem.split("+", 1)[1]: p for d in (ADAPTERS, ENGRAMS) if d.exists() for p in sorted(d.glob(f"{base}+*.gguf"))}


def cells_here(base):
    return sorted(edits_here(base))


def _loaded(at, scales=False):
    """{cell name: its number in the running server} (scales: {cell name: how much of it is switched on})."""
    return {Path(a.get("path", "")).stem.split("+", 1)[-1]: (a.get("scale", 0.0) if scales else a["id"]) for a in (_get(at + "/lora-adapters") or [])}


def up(member, wait=600):
    """The address of the server that holds the member's base (and every cell of it), started if it is not running,
    started again if the cell asked for arrived after it was started."""
    base, edit = split(member)
    at = f"http://127.0.0.1:{port(member)}"
    alive = (_get(at + "/health") or {}).get("status") == "ok"
    if alive and set(cells_here(base)) <= set(_loaded(at)):  # every edit on the machine is in the server (a new engram starts it again)
        return at
    if not binary().exists():
        raise RuntimeError("the ternary runtime is not built on this machine: python -m team.ternary install")
    if edit and not adapter(member).exists():
        raise RuntimeError(f"no weight edit {adapter(member)}: python training/grow.py fetch")
    if alive:
        subprocess.run(["pkill", "-f", f"llama-server.*--port {port(member)}( |$)"], check=False)
        time.sleep(2)
    cmd = [str(binary()), "-m", weights(base), "-t", str(os.environ.get("AGENT_TEAM_THREADS", os.cpu_count() or 4)), "-c", str(CTX),
           "--port", str(port(member)), "--host", "127.0.0.1", "-rtr", "--parallel", "1", "--special" if base == "bitnet" else "--jinja"]
    cells = edits_here(base)
    for c in cells:
        cmd += ["--lora", str(cells[c])]
    if cells:
        cmd.append("--lora-init-without-apply")
    HOME.mkdir(parents=True, exist_ok=True)
    log = open(HOME / f"{base}.log", "ab")
    subprocess.Popen(cmd, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < wait:
        if (_get(at + "/health") or {}).get("status") == "ok":
            return at
        time.sleep(1)
    raise RuntimeError(f"the server of {base} did not come up in {wait} s; see {HOME / (base + '.log')}")


def _post(url, body, timeout=1800):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


_ON = {}  # server address -> the cell this process last switched on there


def _switch(at, scales):
    """Tell the server which cell is on. Its answer to this request is sometimes never sent (seen 2026-11-14: the
    server sits idle with the request unanswered until any other request arrives), so it is asked again after a few
    seconds; the second asking wakes it and both are answered."""
    for _ in range(6):
        try:
            return _post(at + "/lora-adapters", scales, timeout=6)
        except OSError:
            continue
    raise RuntimeError("the server does not answer when told which cell is on")


def chat(member, messages, max_new_tokens=700, temperature=0.0, also=()):
    """The member's reply to a conversation. When the conversation no longer fits its window, the oldest program and
    what it printed go first; the orders and the task stay."""
    at, messages = up(member), list(messages)
    base, edit = split(member)
    have, fresh = _loaded(at), True
    want = {name: 1.0 if name == edit or name in also else 0.0 for name in have}  # the cell, and the engrams recalled for this task
    # What the server reports cannot be trusted for this: one just started says a cell is on (scale 1.0) that it has
    # not applied. So this process switches the first time it speaks, and afterwards whenever the cell changes.
    if have and _ON.get(at) != (edit, tuple(sorted(also))):
        _ON[at] = (edit, tuple(sorted(also)))
        # which cell answers: its edit on, every other off (the base itself: all off). What the server remembers of
        # the conversation was worked out by the cell before: it must not be reused (a cell answered in the other's
        # voice when it was).
        _switch(at, [{"id": i, "scale": want[name]} for name, i in have.items()])
        fresh = False
    for _ in range(8):
        try:
            if base == "bitnet":
                text = "".join(f"{m['role'].capitalize()}: {m['content']}{END}" for m in messages) + "Assistant: "
                out = _post(at + "/completion", {"prompt": text, "n_predict": max_new_tokens, "temperature": temperature,
                                                 "stop": [END, "\nUser:", "<|end_of_text|>"], "cache_prompt": fresh})
                return out.get("content", "").split(END)[0].strip()
            out = _post(at + "/v1/chat/completions", {"messages": messages, "max_tokens": max_new_tokens, "temperature": temperature,
                                                      "top_p": 0.8 if temperature else 1.0, "top_k": 20 if temperature else 0, "cache_prompt": fresh,
                                                      "chat_template_kwargs": {"enable_thinking": False}})
            return (out["choices"][0]["message"].get("content") or "").strip()
        except urllib.error.HTTPError as e:
            fresh = True
            if e.code not in (400, 413, 500) or len(messages) <= 3:
                raise
            del messages[2:4]
    raise RuntimeError(f"{member}: the conversation does not fit its window even with only the task left")


def stop():
    subprocess.run(["pkill", "-f", str(binary())], check=False)


BODY = Path(__file__).resolve().parent.parent / "cells" / "body.json"
# The organs of the body: the domains its cells lean to. Every cell is trained on all of the hive's checked work and
# on its own organ's part of it more often (training/grow.py), so any two cells can check each other and each is
# strongest somewhere. A cell's name ends in its organ ("g3code").
ORGANS = {
    "sources": r"https?://|\bwww\.|\.com\b|\.org\b|\bwebsite\b|\bweb ?page\b|\bsite\b|\bpypi\b|hugging ?face|wikipedia|\blatest\b|\bcurrent version\b|\bdownload\b|\bonline\b",
    "data": r"\bcsv\b|\bjson\b|\blog\b|\btable\b|\bfile\b|here is |\bcolumn|\brows?\b|\borders?\b|\blist of\b|\bspreadsheet\b",
    "words": r"\btranslate|\bsummar|\bexplain\b|\bcapital of\b|\bsentence|\bessay\b|\bopposite\b|\bwrite a (?:poem|letter|story|note)|\bin (?:german|french|spanish|italian)\b",
    "code": r"\bpython\b|\bfunction\b|\bprogram\b|\bmodule\b|\bprime|\bdivisible\b|\bhow many\b|\bcalculate\b|\bsum\b|\bdays\b|\d\s*[-+*/%]\s*\d",
}


def organ(task):
    """The organ a task belongs to most: the one whose words it uses most (code when none)."""
    import re
    low = task.lower()
    hits = {name: len(re.findall(rx, low)) for name, rx in ORGANS.items()}
    return max(hits, key=lambda k: (hits[k], k == "code")) if any(hits.values()) else "code"


def leans(member):
    """The organ a cell leans to, read from its name ('t17+g3code' -> 'code'), or ''."""
    edit = member.partition("+")[2]
    return next((o for o in ORGANS if edit.endswith(o)), "")


def roster():
    """Who the members are. HIVE_MEMBERS=t17+g3code,t17+g3data says it for one run ('coder' is the old 7B coder at 4
    bits through llama.cpp). Without it: the cells of the hive's body (cells/body.json, changed only by the nightly
    gate, training/grow.py) where the ternary runtime is built and the cells are on the machine; otherwise 'coder'."""
    who = [w.strip() for w in os.environ.get("HIVE_MEMBERS", "").split(",") if w.strip()]
    if not who and binary().exists():
        try:
            body = json.loads(BODY.read_text())
            who = [f"{body['dna']}+{c}" for c in body.get("cells", []) if (ADAPTERS / f"{body['dna']}+{c}.gguf").exists()]
        except (OSError, ValueError, KeyError):
            who = []
    return who


def seating(task):
    """The members in the order they take this task: the cells that lean to the task's organ first (the sort is
    stable, so a roster without organs keeps its order). The first two work it out, the next decides a difference."""
    who = roster() or ["coder"]
    o = organ(task)
    return sorted(who, key=lambda m: leans(m) != o)


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
