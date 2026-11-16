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
import http.client
import json
import os
import signal
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
    "t80": ("prism-ml/Ternary-Bonsai-8B-gguf", "Ternary-Bonsai-8B-PQ2_0.gguf"),  # 8B (from Qwen3-8B), 2.2 GB packed; trainable with --int8-base
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
    for wait in (10, 30, 60, None):  # g35: one slice was lost to a single failed fetch; the network comes back
        if subprocess.run(["git", "-C", str(src), "fetch", "-q", "--depth", "1", "origin", PIN]).returncode == 0:
            break
        if wait is None:
            raise RuntimeError(f"ternary: could not fetch the runtime source at {PIN} after 4 tries")
        time.sleep(wait)
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
    # "no slot available" is a server at work on a request (one a task cut off by its time limit left; the server
    # drops it once it sees the asker gone): it answered, so it is alive, and the next request waits its turn
    alive = (_get(at + "/health") or {}).get("status") in ("ok", "no slot available")
    if alive and set(cells_here(base)) <= set(_loaded(at)):  # every edit on the machine is in the server (a new engram starts it again)
        return at
    if not binary().exists():
        raise RuntimeError("the ternary runtime is not built on this machine: python -m team.ternary install")
    if edit and not adapter(member).exists():
        raise RuntimeError(f"no weight edit {adapter(member)}: python training/grow.py fetch")
    if not alive and _RESTARTED[0] >= RESTARTS:
        raise Silent(f"the server of {base} is dead or silent; it was started again {RESTARTS} times in this process already, so not again")
    # ended also when it does not answer at all: a server that is there but silent still holds the port, and a new one
    # started beside it cannot take the port and ends at once (before, this waited out the 600 s for nothing)
    _kill(port(member))
    _ON.pop(at, None)
    return _start(base, wait)


_PROC = {}  # port -> the server this process started there, so that its end is seen without asking it


def _start(base, wait=600):
    """Start the server of a base, every edit of it on this machine loaded and none applied, and wait until it answers.
    Started again after a death, it gets the same arguments (the same base, the same edits on disk)."""
    n = port(base)
    at = f"http://127.0.0.1:{n}"
    cmd = [str(binary()), "-m", weights(base), "-t", str(os.environ.get("AGENT_TEAM_THREADS", os.cpu_count() or 4)), "-c", str(CTX),
           "--port", str(n), "--host", "127.0.0.1", "-rtr", "--parallel", "1", "--special" if base == "bitnet" else "--jinja"]
    cells = edits_here(base)
    for c in cells:
        cmd += ["--lora", str(cells[c])]
    if cells:
        cmd.append("--lora-init-without-apply")
    HOME.mkdir(parents=True, exist_ok=True)
    path = HOME / f"{base}.log"
    since = path.stat().st_size if path.exists() else 0  # this start's own lines begin here
    with open(path, "ab") as log:
        _PROC[n] = subprocess.Popen(cmd, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < wait:
        if (_get(at + "/health") or {}).get("status") == "ok":
            return at
        if _PROC[n].poll() is not None:  # it ended (no memory for it, the port still taken): waiting longer brings nothing
            # Seen on g35's seed 4 (job 133386038675): every start ended at once and was reported as "did not come up in
            # 600 s", the server's own words were in a log no artifact kept. Now its end and its last words are said.
            raise RuntimeError(f"the server of {base} ended {time.time() - t0:.0f} s after it was started, exit code "
                               f"{_PROC[n].returncode}; its last lines: {_tail(path, since)}")
        time.sleep(1)
    raise RuntimeError(f"the server of {base} did not answer in {wait} s; its last lines: {_tail(path, since)}")


def _tail(path, since=0, lines=6):
    """The last lines a server wrote to its log since it was started, joined on one line (an error message's width)."""
    try:
        with open(path, "rb") as f:
            f.seek(since)
            text = f.read()[-20000:].decode("utf-8", "replace")
    except OSError:
        return "(no log)"
    got = [x.strip() for x in text.splitlines() if x.strip()][-lines:]
    return " | ".join(got)[-1200:] or "(nothing written)"


def _kill(n):
    """End the server on port n, whoever started it, with its process group (it runs in a session of its own), and wait
    until it is gone so that the port is free for the next one."""
    pids = {_PROC[n].pid} if n in _PROC else set()
    found = subprocess.run(["pgrep", "-f", f"llama-server.*--port {n}( |$)"], capture_output=True, text=True, check=False).stdout
    pids |= {int(x) for x in found.split() if x.isdigit() and int(x) != os.getpid()}
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:  # not the leader of a group of its own (started by hand): itself alone
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    if n in _PROC:
        try:
            _PROC.pop(n).wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
    t0 = time.time()
    while time.time() - t0 < 30 and any(_running(pid) for pid in pids):
        time.sleep(0.2)


def _running(pid):
    try:
        os.kill(pid, 0)
        # one that is dead but not yet reaped by whoever started it holds no port and no memory
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        return False


def _free():
    """Memory free on this machine, in GB, as the kernel counts what a new program could have ("?" off Linux)."""
    try:
        kb = next(int(line.split()[1]) for line in open("/proc/meminfo") if line.startswith("MemAvailable:"))
        return f"{kb / 2**20:.1f} GB"
    except (OSError, StopIteration, ValueError):
        return "?"


def _post(url, body, timeout=1800):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


_ON = {}  # server address -> the cell this process last switched on there


class Silent(RuntimeError):
    """The server is dead or does not answer."""


def _switch(at, scales):
    """Tell the server which cell is on. Its answer to this request is sometimes never sent (seen 2026-11-14: the
    server sits idle with the request unanswered until any other request arrives), so it is asked again after a few
    seconds; the second asking wakes it and both are answered."""
    for _ in range(6):
        try:
            return _post(at + "/lora-adapters", scales, timeout=6)
        except OSError:
            continue
    raise Silent("the server does not answer when told which cell is on")


def _on(at, base, cell):
    """Put the cell on (its edit, and the engrams recalled for this task) if this process has not already; True when
    it switched."""
    have = _loaded(at)
    if not have and edits_here(base):  # it holds every edit on disk, so an empty list is a server that did not answer
        raise Silent("the server does not say which cells it holds")
    if not have or _ON.get(at) == cell:
        return False
    # What the server reports cannot be trusted for this: one just started says a cell is on (scale 1.0) that it has
    # not applied. So this process switches the first time it speaks, and afterwards whenever the cell changes.
    # Which cell answers: its edit on, every other off (the base itself: all off).
    edit, also = cell
    _switch(at, [{"id": i, "scale": 1.0 if name == edit or name in also else 0.0} for name, i in have.items()])
    _ON[at] = cell
    return True


# How long one request may take. Measured on 4 cores (above) the 9B reads 76 pieces/s and writes 7/s; a runner
# without AVX-512, its memory short, is slower. At a third of that pace a request still finishes: the whole window
# read and the whole answer written. One that takes longer is not slow but stuck (trial run 32's exam: a request
# waited out the 1800 s there were before, unanswered, and the task after it too).
READS, WRITES = 25, 2.5
RESTARTS = int(os.environ.get("HIVE_TERNARY_RESTARTS", 3))  # in one process: a machine that kills every server it starts is not mended by more
_RESTARTED = [0]


def _patience(n):
    """Seconds a request writing at most n pieces may take."""
    return 60 + CTX / READS + n / WRITES


def _why(e, waited):
    r = getattr(e, "reason", e)  # urllib wraps what failed while connecting
    if isinstance(r, TimeoutError) or "timed out" in str(r):
        return f"did not answer in {waited:.0f} s"
    if isinstance(r, ConnectionRefusedError):
        return "is not there (its port refuses)"
    return f"stopped answering ({type(r).__name__}: {r})" if not isinstance(e, Silent) else str(e).replace("the server ", "", 1)


def _restart(member, why):
    """End the member's server (dead, or alive and silent), start it again with the same arguments, and forget which
    cell was on, so the next request puts it back on: a server started again has every cell loaded and none applied."""
    base = split(member)[0]
    if _RESTARTED[0] >= RESTARTS:
        raise Silent(f"the server of {base} {why}; it was started again {RESTARTS} times in this process already, so not again")
    _RESTARTED[0] += 1
    n, before = port(member), _free()
    _kill(n)
    _ON.pop(f"http://127.0.0.1:{n}", None)
    print(f"ternary: the server of {base} {why}; ended and started again ({_RESTARTED[0]} of at most {RESTARTS} in this process), "
          f"memory free {before} before ending it, {_free()} after", file=sys.stderr, flush=True)
    _start(base)


def _ask(member, at, cell, path, body, n):
    """The server's answer to one request, with the cell on. A server that has died or stops answering is ended,
    started again, the cell put back on, and asked once more: before, it stayed dead or silent and every later task
    failed on it (trial run 32's exam, 2026-11-15: "the server does not answer when told which cell is on", then a
    request unanswered for 1800 s)."""
    for last in (False, True):
        waited = _patience(n)
        try:
            p = _PROC.get(port(member))
            if p is not None and p.poll() is not None:
                raise Silent(f"has ended (its process exited with {p.returncode})")
            if _on(at, split(member)[0], cell):
                body = dict(body, cache_prompt=False)  # what it remembers was worked out by the other cell (a cell answered in the other's voice when it was reused)
            return _post(at + path, body, timeout=waited)
        except urllib.error.HTTPError:
            raise  # it answered: what it refused is the request (chat makes it shorter)
        except (OSError, http.client.HTTPException, Silent) as e:
            if last:
                raise Silent(f"the server of {split(member)[0]} {_why(e, waited)}, also after it was started again") from e
            _restart(member, _why(e, waited))


def chat(member, messages, max_new_tokens=700, temperature=0.0, also=()):
    """The member's reply to a conversation. When the conversation no longer fits its window, the oldest program and
    what it printed go first; the orders and the task stay."""
    at, messages = up(member), list(messages)
    base, edit = split(member)
    cell, fresh = (edit, tuple(sorted(also))), True
    for _ in range(8):
        try:
            if base == "bitnet":
                text = "".join(f"{m['role'].capitalize()}: {m['content']}{END}" for m in messages) + "Assistant: "
                out = _ask(member, at, cell, "/completion", {"prompt": text, "n_predict": max_new_tokens, "temperature": temperature,
                                                             "stop": [END, "\nUser:", "<|end_of_text|>"], "cache_prompt": fresh}, max_new_tokens)
                return out.get("content", "").split(END)[0].strip()
            out = _ask(member, at, cell, "/v1/chat/completions", {"messages": messages, "max_tokens": max_new_tokens, "temperature": temperature,
                                                                  "top_p": 0.8 if temperature else 1.0, "top_k": 20 if temperature else 0, "cache_prompt": fresh,
                                                                  "chat_template_kwargs": {"enable_thinking": False}}, max_new_tokens)
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
    edit = member.partition("+")[2].rstrip("0123456789")  # a body that multiplies has 'g24code2', a second child of code
    return next((o for o in ORGANS if edit.endswith(o)), "")


def roster():
    """Who the members are. HIVE_MEMBERS=t17+g3code,t17+g3data says it for one run ('coder' is the old 7B coder at 4
    bits through llama.cpp). Without it: the hive's body (cells/body.json, written by each generation's record,
    training/grow_record.py), its trunk and its cells, where the ternary runtime is built and their files are on
    the machine; a body with no cells yet is its DNA alone; otherwise 'coder'."""
    who = [w.strip() for w in os.environ.get("HIVE_MEMBERS", "").split(",") if w.strip()]
    if not who and binary().exists():
        try:
            body = json.loads(BODY.read_text())
            names = ([body["trunk"]] if isinstance(body.get("trunk"), str) and body["trunk"] else []) + list(body.get("cells", []))
            who = [f"{body['dna']}+{c}" for c in names if (ADAPTERS / f"{body['dna']}+{c}.gguf").exists()]
            if not who and body.get("dna") in MODELS and os.environ.get("HIVE_DNA_ALONE", "1") == "1":
                from huggingface_hub import try_to_load_from_cache
                if isinstance(try_to_load_from_cache(*MODELS[body["dna"]]), str):  # the DNA is on this machine
                    who = [body["dna"]]
        except (OSError, ValueError, KeyError):
            who = []
    return who


def is_trunk(member):
    """Whether a member is the body's trunk (training/merge.py): the edit all its cells are averaged into."""
    import re
    return re.fullmatch(r"g\d+trunk", member.partition("+")[2]) is not None


STRENGTHS = Path(__file__).resolve().parent.parent / "cells" / "strengths.json"


def strengths():
    """{lean: {"kind": {kind: [right, tries]}, "organ": {organ: [right, tries]}}}: how often each cell of the body,
    named by the organ it leans to, was right by itself, from the exact records of its last gate
    (training/grow_record.py). Empty when there are none. Read only with HIVE_SEATING=strength (a trial)."""
    try:
        d = json.loads(STRENGTHS.read_text())
        return d.get("by_lean", {}) if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def strength(member, task, kind="", table=None):
    """How likely this cell is right on this task, from what it did on the nearest things it has met: the same kind
    of task if it has met it, pulled toward its record on the task's organ (the nearer degree), pulled toward one
    half when it has met neither. A kind never met is a weakness of every cell; it goes to the cell strongest on
    what lies nearest."""
    rec = (strengths() if table is None else table).get(leans(member), {})
    r_o, n_o = rec.get("organ", {}).get(organ(task), [0, 0])
    p_o = (r_o + 1) / (n_o + 2)
    r_k, n_k = rec.get("kind", {}).get(kind, [0, 0]) if kind else (0, 0)
    return (r_k + 2 * p_o) / (n_k + 2)


def _parents():
    """{cell: its parent} of the body (cells/body.json): the body's lines of descent."""
    try:
        body = json.loads(BODY.read_text())
        return body.get("parents", {}) if isinstance(body.get("parents"), dict) else {}
    except (OSError, ValueError):
        return {}


def _born(member):
    import re
    m = re.match(r"g(\d+)", member.partition("+")[2])
    return int(m.group(1)) if m else 0


def _line(member, parents):
    out, c = set(), member.partition("+")[2]
    while c and c not in out:
        out.add(c)
        c = parents.get(c, "")
    return out


def _kin(a, b, parents):
    """Whether one cell descends from the other (a child is its parent and a degree more)."""
    x, y = a.partition("+")[2], b.partition("+")[2]
    return x in _line(b, parents) or y in _line(a, parents)


def seating(task, kind=None):
    """The members in the order they take this task: the first two work it out, the next decides a difference.
    The cells that lean to the task's organ first (the sort is stable, so a roster without organs keeps its order).

    The trunk (the average of the body's newest cells, training/merge.py) sits first where the body has one.
    A body that has multiplied has lines of descent (cells/body.json "parents"). Of one organ the newest cell sits
    first: it is its parent and more. The second seat goes to the newest cell of another line: a child and its own
    parent are nearly one mind, and two copies agreeing on a wrong answer is the false memory that agreement cannot
    catch. Nothing is counted to seat them.

    HIVE_SEATING=strength (a trial): by each organ's record of being right, cells/strengths.json, as before."""
    who = roster() or ["coder"]
    o = organ(task)
    kind = os.environ.get("HIVE_KIND", "") if kind is None else kind
    table = strengths() if os.environ.get("HIVE_SEATING") == "strength" else {}
    if table:
        return sorted(who, key=lambda m: (-strength(m, task, kind, table), leans(m) != o))
    # the trunk, the whole body's learning as one edit, takes every task first; the cells are its second opinions
    trunk = sorted((m for m in who if is_trunk(m)), key=_born)[-1:]
    order = sorted((m for m in who if not is_trunk(m)), key=lambda m: (leans(m) != o, -_born(m)))
    turn = os.environ.get("HIVE_ROTATE", "")
    if turn.isdigit() and len(order) > 1:
        # practice: every cell takes its turn as the first of the cells, whatever its organ, so each one's mistakes
        # show and its children can be taught them (HIVE_ROTATE is the practice runner's number)
        import zlib
        order.insert(0, order.pop((zlib.crc32(task.encode()) + int(turn)) % len(order)))
    parents = _parents()
    if len(order) > 2 and parents:
        first = order[0]
        other = next((m for m in order[1:] if not _kin(first, m, parents)), None)
        if other:
            order.remove(other)
            order.insert(1, other)
    return trunk + order


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
