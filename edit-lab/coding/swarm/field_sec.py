"""Phase 4 security-operations behaviours (PLAN.md section 15, family F).

One smallest job per function, same envelope as field.py's finders:
{"ok": not hits, "output": [line numbers or hit dicts], "evidence": ...}.
For finders, ok=False means "found what it looks for" — a detection,
not a failure. Everything here is defensive tooling for Arnav's own
systems: scanning his code, his configs, his dependency lists and this
machine's own listener inventory so he can harden them. Secret VALUES
are never returned — only file/line/kind, so a scan report is safe to
put on the board.
"""
import ast
import re

from .field import _SECRET_NAME, _module_aliases, _parse


def _lines(task):
    text = task.get("text", task.get("code", "")) if isinstance(task, dict) else str(task)
    return text.splitlines()


# ------------------------------------------------------------ sec-code
def path_traversal_finder(task):
    """open()/send_file() with a non-literal path, or a literal '..'
    path segment — the shapes path traversal hides in. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and ("../" in node.value or "..\\" in node.value):
            bad.append(node.lineno)
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else \
                f.attr if isinstance(f, ast.Attribute) else None
            if name in ("open", "send_file") and node.args \
                    and not (isinstance(node.args[0], ast.Constant)
                             and isinstance(node.args[0].value, str)):
                bad.append(node.lineno)
    return {"ok": not bad, "output": sorted(set(bad)),
            "evidence": f"{len(set(bad))} path-traversal shape(s)"}


_SECRET_CONTEXT = re.compile(r"(?i)(token|password|passwd|secret|otp|session|reset|api_?key)")


def insecure_random_finder(task):
    """random.* calls in a file that talks about tokens/passwords/OTPs —
    predictable randomness guarding a secret. ok = none."""
    code = task["code"]
    if not _SECRET_CONTEXT.search(code):
        return {"ok": True, "output": [],
                "evidence": "no secret context in file; random use not flagged"}
    tree, err = _parse(code)
    if err:
        return err
    mod_names, func_names = _module_aliases(tree, "random")
    funcs = {"random", "randint", "randrange", "choice", "choices",
             "sample", "shuffle", "getrandbits", "uniform"}
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id in mod_names and f.attr in funcs:
            bad.append(node.lineno)
        elif isinstance(f, ast.Name) and func_names.get(f.id) in funcs:
            bad.append(node.lineno)
    return {"ok": not bad, "output": sorted(set(bad)),
            "evidence": f"{len(set(bad))} insecure-random call(s) in secret context"}


def unsafe_yaml_load_finder(task):
    """yaml.load without SafeLoader, or yaml.unsafe_load — arbitrary
    object deserialization. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    mod_names, func_names = _module_aliases(tree, "yaml")
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        fname = None
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id in mod_names:
            fname = f.attr
        elif isinstance(f, ast.Name):
            fname = func_names.get(f.id)
        if fname == "unsafe_load":
            bad.append(node.lineno)
        elif fname == "load":
            loader = next((k for k in node.keywords if k.arg == "Loader"), None)
            safe = loader is not None and "SafeLoader" in ast.dump(loader.value)
            if not safe:
                bad.append(node.lineno)
    return {"ok": not bad, "output": sorted(set(bad)),
            "evidence": f"{len(set(bad))} unsafe yaml load(s)"}


def tls_verify_off_finder(task):
    """verify=False on any call — TLS certificate checking switched
    off. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = [node.lineno for node in ast.walk(tree)
           if isinstance(node, ast.Call)
           for k in node.keywords
           if k.arg == "verify" and isinstance(k.value, ast.Constant)
           and k.value.value is False]
    return {"ok": not bad, "output": sorted(set(bad)),
            "evidence": f"{len(set(bad))} TLS verify=False call(s)"}


def ssrf_finder(task):
    """HTTP request calls whose URL is not a literal — a URL an attacker
    could steer (SSRF shape). Constant URLs are clean. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    mod_names, func_names = _module_aliases(tree, "requests")
    funcs = {"get", "post", "put", "delete", "head", "patch", "request"}
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        f = node.func
        hit = False
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id in mod_names and f.attr in funcs:
            hit = True
        elif isinstance(f, ast.Name) and func_names.get(f.id) in funcs:
            hit = True
        elif isinstance(f, ast.Attribute) and f.attr == "urlopen":
            hit = True
        if hit and not (isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
            bad.append(node.lineno)
    return {"ok": not bad, "output": sorted(set(bad)),
            "evidence": f"{len(set(bad))} request(s) with non-literal URL"}


# ------------------------------------------------------------ sec-deps
_KNOWN_BAD = {  # small LOCAL table, illustrative pins with public CVEs
    "requests": {"2.19.0", "2.19.1"}, "urllib3": {"1.24.0", "1.24.1"},
    "pyyaml": {"5.1", "5.1.1", "5.1.2"}, "django": {"1.11.0", "2.0.0", "2.0.1"},
    "flask": {"0.12.0"}, "pillow": {"8.0.0"}, "jinja2": {"2.10.0"},
    "cryptography": {"2.4.0"},
}
_REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([A-Za-z0-9_.!+\-]+)")


def _req_entries(task):
    out = []
    for i, line in enumerate(_lines(task), 1):
        m = _REQ_LINE.match(line)
        if m:
            out.append((m.group(1).lower().replace("_", "-"), m.group(2), i))
    return out


def known_bad_version_finder(task):
    """Pinned versions present in the local known-bad table. ok = none."""
    bad = [{"name": n, "version": v, "line": ln}
           for n, v, ln in _req_entries(task) if v in _KNOWN_BAD.get(n, set())]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} known-bad pin(s) (local table, "
                        f"{sum(len(s) for s in _KNOWN_BAD.values())} entries)"}


_POPULAR = ["requests", "numpy", "pandas", "flask", "django", "pillow",
            "cryptography", "urllib3", "jinja2", "pyyaml", "boto3",
            "sqlalchemy", "fastapi", "pydantic", "pytest", "lxml"]


def _lev(a, b):
    if abs(len(a) - len(b)) > 1:
        return 2
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def typosquat_suspect_finder(task):
    """Requirement names one edit away from a popular package but not
    equal to it — the typosquat shape. ok = none."""
    bad = []
    for n, _v, ln in _req_entries(task):
        if n in _POPULAR:
            continue
        near = [p for p in _POPULAR if _lev(n, p) == 1]
        if near:
            bad.append({"name": n, "line": ln, "resembles": near[0]})
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} typosquat suspect(s)"}


def setup_exec_finder(task):
    """A setup/install file that executes commands — install-time code
    execution beyond the declared build. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name) and f.id in ("eval", "exec"):
            bad.append(node.lineno)
        elif isinstance(f, ast.Attribute) and f.attr in (
                "system", "popen", "call", "run", "Popen", "check_output") \
                and isinstance(f.value, ast.Name) \
                and f.value.id in ("os", "subprocess"):
            bad.append(node.lineno)
    return {"ok": not bad, "output": sorted(set(bad)),
            "evidence": f"{len(set(bad))} install-time exec call(s)"}


# ------------------------------------------------------------ sec-config
def debug_true_finder(task):
    """debug turned on in config/code text (DEBUG = True, debug: true,
    debug=True). ok = none."""
    bad = [i for i, ln in enumerate(_lines(task), 1)
           if re.search(r"(?i)\bdebug\b\s*[:=]\s*(true|1|yes)\b", ln)]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} debug-on line(s)"}


def wildcard_bind_finder(task):
    """0.0.0.0 / :: binds in config or code text — service exposed on
    every interface. ok = none."""
    bad = [i for i, ln in enumerate(_lines(task), 1)
           if "0.0.0.0" in ln or "[::]" in ln or "host: ::" in ln]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} wildcard bind line(s)"}


def chmod_777_finder(task):
    """chmod 777 (world-writable+executable) in scripts/configs.
    ok = none."""
    bad = [i for i, ln in enumerate(_lines(task), 1)
           if re.search(r"chmod\s+(?:-\S+\s+)*0?777\b", ln)]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} chmod 777 line(s)"}


def docker_root_finder(task):
    """A Dockerfile with no non-root USER instruction runs as root.
    ok = a non-root USER exists."""
    users = [ln.split(None, 1)[1].strip() for ln in _lines(task)
             if re.match(r"(?i)\s*USER\s+\S+", ln)]
    non_root = [u for u in users if u not in ("root", "0")]
    bad = [] if non_root else ["root"]
    return {"ok": not bad, "output": bad,
            "evidence": "non-root USER present" if non_root
                        else "no non-root USER: container runs as root"}


_PLACEHOLDER = re.compile(r"(?i)(changeme|change-me|xxx|your[-_]|example|"
                          r"placeholder|todo|\$\{|<[^>]*>|\*{3,})")


def env_secret_finder(task):
    """KEY=value lines whose key looks secret-bearing and whose value
    is a real-looking literal (not a placeholder, not empty). The
    VALUE is never returned. ok = none."""
    bad = []
    for i, ln in enumerate(_lines(task), 1):
        m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\S.*)$", ln)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip("'\"")
        if _SECRET_NAME.search(key) and val and not _PLACEHOLDER.search(val):
            bad.append({"name": key, "line": i})
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} env secret(s) with real-looking values"}


# ------------------------------------------------------------ sec-inventory
def _parse_tcp(text):
    """Parse /proc/net/tcp(6) text -> [{port, bind}] for LISTEN (0A)."""
    out = []
    for ln in text.splitlines()[1:]:
        parts = ln.split()
        if len(parts) < 4 or parts[3] != "0A":
            continue
        addr, port_hex = parts[1].rsplit(":", 1)
        port = int(port_hex, 16)
        if len(addr) == 8:
            bind = ".".join(str(int(addr[i:i + 2], 16))
                            for i in (6, 4, 2, 0))
        else:
            bind = "::" if set(addr) == {"0"} else "ipv6"
        out.append({"port": port, "bind": bind})
    return out


def tcp_listener_parser(task):
    """/proc/net/tcp text -> listening sockets. Pure parser."""
    listeners = _parse_tcp(task.get("text", ""))
    return {"ok": True, "output": listeners,
            "evidence": f"{len(listeners)} listening socket(s)"}


def listening_port_lister(task):
    """THIS machine's listening TCP ports, read from its own /proc —
    the inventory Arnav hardens from. Read-only."""
    from pathlib import Path
    found = []
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            found += _parse_tcp(Path(f).read_text())
        except OSError:
            pass
    uniq = sorted({(l["port"], l["bind"]) for l in found})
    out = [{"port": p, "bind": b} for p, b in uniq]
    return {"ok": True, "output": out,
            "evidence": f"{len(out)} listening socket(s) on this machine"}


_SERVICES = {22: "ssh", 80: "http", 443: "https", 3000: "dev-http",
             3306: "mysql", 5432: "postgres", 6379: "redis",
             8000: "dev-http", 8080: "http-alt", 8443: "https-alt",
             27017: "mongodb", 53: "dns", 25: "smtp"}


def service_name_mapper(task):
    """One port -> its probable service name (small local table)."""
    port = int(task["port"])
    return {"ok": True, "output": _SERVICES.get(port, "unknown"),
            "evidence": f"port {port} -> {_SERVICES.get(port, 'unknown')}"}


def external_bind_checker(task):
    """Which of these listeners are bound to every interface
    (0.0.0.0 / ::) rather than localhost. ok = none."""
    bad = [l for l in task.get("listeners", [])
           if l.get("bind") in ("0.0.0.0", "::")]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} externally-bound listener(s)"}


# ------------------------------------------------------------ sec-scan
_AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
_PRIV_KEY = re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY")


def aws_key_finder(task):
    """AWS access-key-id shapes in text. Locations only, never values."""
    bad = [{"line": i, "kind": "aws-access-key"}
           for i, ln in enumerate(_lines(task), 1) if _AWS_KEY.search(ln)]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} AWS key shape(s)"}


def private_key_finder(task):
    """Private-key block headers in text. Locations only."""
    bad = [{"line": i, "kind": "private-key"}
           for i, ln in enumerate(_lines(task), 1) if _PRIV_KEY.search(ln)]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} private-key block(s)"}
