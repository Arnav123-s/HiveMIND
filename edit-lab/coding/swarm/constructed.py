"""Constructed specialists: the smallest possible kind.

Each function here is ONE tiny job, done deterministically, at zero model
RAM. Several are ports of specialists HiveMIND already keeps as code
(extract_code, the sanity checks, sandbox execution); the rest are split
out of jobs that used to hide inside bigger components.
"""
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# ---------------------------------------------------------------- writing
def extract_code(task):
    """Pull the program out of a model reply (HiveMIND coder.extract_code)."""
    text = task if isinstance(task, str) else task.get("text", "")
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    if blocks:
        return {"ok": True, "output": max(blocks, key=len).strip(),
                "evidence": f"{len(blocks)} code block(s)"}
    if "```" in text:
        return {"ok": True, "output": text.split("```", 1)[1].split("\n", 1)[1].strip(),
                "evidence": "unterminated block"}
    return {"ok": True, "output": text.strip(), "evidence": "no block; raw text"}


# ---------------------------------------------------------------- testing
def run_program(task):
    """Execute a program in a temp dir; report exit/stdout/stderr/seconds."""
    code = task["code"]
    wd = Path(task.get("workdir") or tempfile.mkdtemp(prefix="swarm_run_"))
    wd.mkdir(parents=True, exist_ok=True)
    for name, content in task.get("setup", {}).items():
        (wd / name).write_text(content)
    f = wd / task.get("filename", "program.py")
    f.write_text(code)
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True,
                           timeout=task.get("timeout", 30), cwd=wd)
        out = {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    except subprocess.TimeoutExpired as e:
        out = {"returncode": None, "stdout": e.stdout or "", "stderr": "TIMEOUT",
               "timeout": True}
    out.update({"seconds": round(time.time() - t0, 2), "workdir": str(wd)})
    return {"ok": out["returncode"] == 0, "output": out,
            "evidence": f"exit {out['returncode']} in {out['seconds']}s"}


def exit_checker(task):
    res = task["result"]
    return {"ok": res["returncode"] == 0, "output": res["returncode"],
            "evidence": "exit 0" if res["returncode"] == 0 else f"exit {res['returncode']}: {res['stderr'][-200:]}"}


def output_differ(task):
    """Compare expected vs actual output lines; name the first mismatch."""
    exp = [str(x) for x in task["expected"]]
    got = [l for l in str(task["actual"]).strip().splitlines()]
    for i, (a, b) in enumerate(zip(exp, got)):
        if a != b:
            return {"ok": False, "output": {"line": i, "expected": a, "got": b},
                    "evidence": f"line {i}: expected {a!r}, got {b!r}"}
    if len(exp) != len(got):
        return {"ok": False, "output": {"line": min(len(exp), len(got))},
                "evidence": f"line count: expected {len(exp)}, got {len(got)}"}
    return {"ok": True, "output": None, "evidence": f"all {len(exp)} line(s) match"}


def file_checker(task):
    """Verify a produced file: exact text, or JSON deep-equality."""
    f = Path(task["workdir"]) / task["file"]
    if not f.exists():
        return {"ok": False, "output": None, "evidence": f"{task['file']} not created"}
    text = f.read_text(errors="replace")
    if "json_equals" in task:
        try:
            return {"ok": json.loads(text) == task["json_equals"], "output": text[:500],
                    "evidence": "JSON deep-equality"}
        except json.JSONDecodeError:
            return {"ok": False, "output": text[:500], "evidence": "file is not valid JSON"}
    return {"ok": text == task["text"], "output": text[:500], "evidence": "exact file content"}


def probe_generator(task):
    """Generate probe inputs for a function from a tiny spec (deterministic)."""
    kind = task.get("kind", "ints")
    if kind == "ints":
        vals = [0, 1, -1, 2, 10, -10, 99]
    elif kind == "strings":
        vals = ["", "a", "aa", "ab", "racecar", "hello world"]
    elif kind == "lists":
        vals = [[], [1], [2, 1], [3, 1, 2], [5, 5, 5]]
    else:
        vals = []
    return {"ok": True, "output": vals, "evidence": f"{len(vals)} probes ({kind})"}


# ---------------------------------------------------------------- debugging
ERROR_PATTERNS = [
    ("SyntaxError", r"SyntaxError"), ("IndentationError", r"IndentationError"),
    ("NameError", r"NameError"), ("TypeError", r"TypeError"),
    ("ValueError", r"ValueError"), ("IndexError", r"IndexError"),
    ("KeyError", r"KeyError"), ("ZeroDivisionError", r"ZeroDivisionError"),
    ("FileNotFoundError", r"FileNotFoundError"), ("AttributeError", r"AttributeError"),
    ("ImportError", r"(?:ImportError|ModuleNotFoundError)"),
    ("RecursionError", r"RecursionError"), ("Timeout", r"TIMEOUT"),
]


def traceback_classifier(task):
    """Name the error class in a stderr blob. Trainable: weights can hold
    extra keyword->class votes fitted by the TRAINER (see meta.py)."""
    stderr = task if isinstance(task, str) else task.get("stderr", "")
    weights = task.get("weights", {}) if isinstance(task, dict) else {}
    for cls, pat in ERROR_PATTERNS:
        if re.search(pat, stderr):
            return {"ok": True, "output": cls, "evidence": f"matched {pat}"}
    best, best_score = None, 0
    for kw, cls in weights.get("keywords", {}).items():
        if kw in stderr and weights["keywords"][kw] > best_score:
            best, best_score = cls, weights["keywords"][kw]
    if best:
        return {"ok": True, "output": best, "evidence": "keyword weights vote"}
    return {"ok": False, "output": "unknown", "evidence": "no pattern matched", "gap": "unknown-error-class"}


def error_line_pointer(task):
    """Point at the deepest 'line N' of the program in a traceback."""
    stderr = task.get("stderr", "")
    lines = re.findall(r'File "[^"]*", line (\d+)', stderr)
    if lines:
        return {"ok": True, "output": int(lines[-1]), "evidence": f"traceback line {lines[-1]}"}
    return {"ok": False, "output": None, "evidence": "no line reference in traceback"}


def bug_pattern_matcher(task):
    """Match a known bug signature in code and propose the smallest patch."""
    code = task["code"]
    patterns = [
        (r"range\(1,\s*len\((\w+)\)\s*-\s*1\)",
         lambda m: (m.group(0), f"range(1, len({m.group(1)}))"),
         "loop bound len(x)-1 skips the last element"),
        (r"range\(len\((\w+)\)\)",
         lambda m: (m.group(0), f"range(1, len({m.group(1)}))"),
         "loop starts at 0 where the algorithm needs index 1 (review)"),
    ]
    for pat, fix, why in patterns:
        m = re.search(pat, code)
        if m:
            old, new = fix(m)
            return {"ok": True, "output": {"old": old, "new": new},
                    "evidence": why}
    return {"ok": False, "output": None, "evidence": "no known bug pattern", "gap": "unknown-bug"}


def patch_applier(task):
    """Apply exactly one old->new replacement; fail if it isn't there once."""
    code, old, new = task["code"], task["old"], task["new"]
    if code.count(old) != 1:
        return {"ok": False, "output": None,
                "evidence": f"patch target occurs {code.count(old)} times, need exactly 1"}
    return {"ok": True, "output": code.replace(old, new), "evidence": f"{old!r} -> {new!r}"}


# ---------------------------------------------------------------- review
def syntax_checker(task):
    code = task["code"] if isinstance(task, dict) else task
    try:
        compile(code, "<program>", "exec")
        return {"ok": True, "output": None, "evidence": "compiles"}
    except SyntaxError as e:
        return {"ok": False, "output": {"line": e.lineno, "msg": e.msg},
                "evidence": f"SyntaxError line {e.lineno}: {e.msg}"}


def sanity_checker(task):
    """HiveMIND's measurement sanity: a 0.00 measurement means the code is wrong."""
    stdout = task.get("stdout", "") if isinstance(task, dict) else task
    probs = []
    if re.search(r"\b0\.0+\s*(s|sec|seconds|ms|mb|gb|kb)\b", stdout, re.I):
        probs.append("a time or memory measurement printed as 0.00")
    if re.search(r"\b0\s*/\s*\d+\b", stdout) and re.search(r"correct|accura", stdout, re.I):
        probs.append("0 answers correct")
    return {"ok": not probs, "output": probs, "evidence": "; ".join(probs) or "no sanity problems"}


def contract_checker(task):
    """Every expected output named by the task exists in the workdir."""
    wd = Path(task["workdir"])
    missing = [f for f in task.get("files", []) if not (wd / f).exists()]
    return {"ok": not missing, "output": missing,
            "evidence": "all outputs present" if not missing else f"missing: {missing}"}


# ---------------------------------------------------------------- planning
def step_splitter(task):
    """Split an instruction into steps on sentence / list boundaries."""
    text = task if isinstance(task, str) else task.get("instruction", "")
    parts = [p.strip() for p in re.split(r"(?<=[.;])\s+|\n+", text) if p.strip()]
    return {"ok": True, "output": parts, "evidence": f"{len(parts)} step(s)"}


def dependency_orderer(task):
    """Kahn's algorithm, alphabetical tie-break (deterministic)."""
    deps = {k: list(v) for k, v in task["deps"].items()}
    done, out = set(), []
    while deps:
        ready = sorted(k for k, v in deps.items() if all(d in done for d in v))
        if not ready:
            return {"ok": False, "output": out, "evidence": "dependency cycle"}
        k = ready[0]
        out.append(k); done.add(k); del deps[k]
    return {"ok": True, "output": out, "evidence": "topological order"}


def acceptance_writer(task):
    """Turn a check spec into the gate list the testing niche will apply."""
    chk = task["check"]
    gates = ["exit==0"]
    gates.append({"stdout_equals": "stdout matches exactly",
                  "stdout_lines_equals": "stdout lines match exactly",
                  "file_json_equals": "file JSON deep-equals expected",
                  "file_equals": "file content matches exactly"}.get(chk["kind"], chk["kind"]))
    if task.get("save_as"):
        gates.append(f"file {task['save_as']} exists")
    return {"ok": True, "output": gates, "evidence": f"{len(gates)} gate(s)"}


# ---------------------------------------------------------------- compliance
def instruction_splitter(task):
    """Split a literal instruction into single checkable requirement items."""
    text = task if isinstance(task, str) else task.get("instruction", "")
    raw = re.split(r"(?<=[.;])\s+|\s+and\s+(?=(?:print|save|write|return|create))", text)
    items = [p.strip().rstrip(".") for p in raw if len(p.strip()) > 8]
    return {"ok": True, "output": items, "evidence": f"{len(items)} requirement item(s)"}


def literal_checker(task):
    """Check one requirement item literally against the finished result.

    Handles the structural kinds: 'save ... as FILE' (file exists),
    'one per line' (line count equals the probe count), quoted strings and
    numbers (appear in output). Anything else is marked needs-model for
    the semantic checker — never silently passed.
    """
    item, result = task["item"], task["result"]
    wd = Path(result.get("workdir", "."))
    stdout = result.get("stdout", "")
    m = re.search(r"save .*? as ([\w.\-]+)", item, re.I)
    if m:
        ok = (wd / m.group(1)).exists()
        return {"ok": ok, "output": "literal-pass" if ok else "literal-fail",
                "evidence": f"file {m.group(1)} {'exists' if ok else 'missing'}"}
    if "one per line" in item or "one result per line" in item:
        n = len(result.get("expected_lines", []))
        got = len([l for l in stdout.strip().splitlines() if l != ""]) if stdout.strip() else 0
        ok = (n == 0 or got == n) and bool(stdout.strip())
        return {"ok": ok, "output": "literal-pass" if ok else "literal-fail",
                "evidence": f"{got} non-empty line(s), expected {n}"}
    quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", item)
    quoted = [a or b for a, b in quoted]
    if quoted:
        ok = all(q in stdout for q in quoted)
        return {"ok": ok, "output": "literal-pass" if ok else "literal-fail",
                "evidence": f"quoted strings {quoted} {'all present' if ok else 'not all in output'}"}
    return {"ok": False, "output": "needs-model", "evidence": "no literal check applies",
            "gap": "semantic-check"}


def fidelity_scorer(task):
    """Instruction fidelity = items literally/semantically passed / items."""
    checks = task["checks"]
    passed = sum(1 for c in checks if c["output"] in ("literal-pass", "semantic-pass"))
    score = passed / len(checks) if checks else 1.0
    return {"ok": score == 1.0, "output": score,
            "evidence": f"{passed}/{len(checks)} instruction items followed"}


# ---------------------------------------------------------------- interface niche
def request_normalizer(task):
    """Any of the three API shapes -> the one internal message list."""
    if isinstance(task, list):
        return {"ok": True, "output": task, "evidence": "already OpenAI-style"}
    if isinstance(task, dict) and "messages" in task:  # anthropic-style w/ system
        msgs = ([{"role": "system", "content": task["system"]}] if task.get("system") else []) \
            + task["messages"]
        return {"ok": True, "output": msgs, "evidence": "anthropic shape normalized"}
    if isinstance(task, dict) and "prompt" in task:
        return {"ok": True, "output": [{"role": "user", "content": task["prompt"]}],
                "evidence": "bare prompt wrapped"}
    return {"ok": False, "output": None, "evidence": "unknown request shape"}


def response_normalizer(task):
    """Any backend reply shape -> {"text": ...}."""
    if isinstance(task, str):
        return {"ok": True, "output": {"text": task}, "evidence": "plain text"}
    if isinstance(task, dict):
        if "choices" in task:
            return {"ok": True, "output": {"text": task["choices"][0]["message"]["content"]},
                    "evidence": "openai shape"}
        if "content" in task and isinstance(task["content"], list):
            text = "".join(b.get("text", "") for b in task["content"])
            return {"ok": True, "output": {"text": text}, "evidence": "anthropic shape"}
        if "text" in task:
            return {"ok": True, "output": {"text": task["text"]}, "evidence": "internal shape"}
    return {"ok": False, "output": None, "evidence": "unknown response shape"}


def backend_router(task):
    """Parse a model_ref and name its backend (the routing decision only)."""
    ref = task if isinstance(task, str) else task.get("model_ref", "")
    for prefix, name in [("local:", "local-constructed"), ("local-hf:", "local-hf"),
                         ("local-gguf:", "local-gguf"), ("api:openai:", "api-openai"),
                         ("api:anthropic:", "api-anthropic")]:
        if ref.startswith(prefix):
            return {"ok": True, "output": name, "evidence": f"{ref} -> {name}"}
    return {"ok": False, "output": None, "evidence": f"unparsable model_ref {ref}"}


class UsageMeter:
    """usage-meter specialist: accumulates approximate token usage per role."""

    def __init__(self):
        self.totals = {}

    def __call__(self, task):
        role, usage = task["role"], task["usage"]
        t = self.totals.setdefault(role, {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
        t["prompt_tokens"] += usage.get("prompt_tokens", 0)
        t["completion_tokens"] += usage.get("completion_tokens", 0)
        t["calls"] += 1
        return {"ok": True, "output": dict(t), "evidence": f"{role}: {t['calls']} call(s)"}
