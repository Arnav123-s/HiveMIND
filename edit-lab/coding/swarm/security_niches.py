"""Phase 4 security-operations niches (PLAN.md section 15, family F).

Arnav's directive (2026-11-08): the hive gets a cybersecurity branch
for testing and hardening HIS OWN systems and devices, built the same
way as everything else — smallest specialists, one weakness class /
one check per specialist, each niche with its own micro-coordinator
(from niches.build_swarm, like every niche):

  sec-code      per-weakness-class vulnerability finders over code
  sec-deps      dependency-risk checks over requirement lists
  sec-config    config-hardening checks over config/Dockerfile text
  sec-inventory this machine's own exposed-service inventory (read-only)
  sec-scan      credential-exposure scanning of his own files, composed
                from the sec-scan finders + the secret-line MODEL

Finders never return secret values — locations and kinds only.
"""
import re
from pathlib import Path

from . import field_sec as FS
from .specialist import Specialist

SECURITY_NICHES = ["sec-code", "sec-deps", "sec-config",
                   "sec-inventory", "sec-scan"]

_SCAN_EXTS = {".py", ".env", ".txt", ".md", ".cfg", ".ini", ".toml",
              ".yaml", ".yml", ".json", ".sh"}
_SHAPE_FALLBACK = re.compile(
    r"(?i)(password|passwd|api_?key|secret|token)\s*=\s*['\"][^'\"]{6,}['\"]")


def _scan_lines(reg, files):
    """The scanner's one job, per line: structural finders first
    (deterministic). The secret-line MODEL channel is gated by the
    secret SHAPE: the model was trained on synthetic line shapes and
    over-fires on real code (measured in the phase-4 order check:
    11,269 model hits over the lab's own 44 source files), so a model
    hit counts only where the line also carries a credential shape
    (name = 'literal') — two specialists' judgments composed, the
    model proposing and the shape corroborating. While no model is
    loaded the shape alone is the fallback channel. Returns hit
    dicts, values never kept."""
    model = reg.get("secret-line-model")
    hits = []
    for rel in sorted(files):
        for i, line in enumerate(files[rel].splitlines(), 1):
            kind = None
            if FS._AWS_KEY.search(line):
                kind = "aws-access-key"
            elif FS._PRIV_KEY.search(line):
                kind = "private-key"
            elif _SHAPE_FALLBACK.search(line):
                if model is None or model.run(
                        {"text": line}).get("output") == "secret":
                    kind = "secret-line"
            if kind:
                hits.append({"file": rel, "line": i, "kind": kind})
    return hits


def make_workspace_secret_scanner(reg):
    """Bind the scanner to the registry: it composes the sec-scan
    finders and the secret-line model — composition, not a new brain."""
    def _scan(task):
        files = task.get("files")
        if files is None:
            root = Path(task["root"])
            files = {}
            for p in sorted(root.rglob("*")):
                if p.is_file() and p.suffix in _SCAN_EXTS \
                        and p.stat().st_size <= 200_000:
                    try:
                        files[str(p.relative_to(root))] = p.read_text(
                            errors="replace")
                    except OSError:
                        pass
        hits = _scan_lines(reg, files)
        return {"ok": not hits, "output": hits,
                "evidence": f"scanned {len(files)} file(s): "
                            f"{len(hits)} credential exposure(s), "
                            f"locations only"}
    return _scan


def register_security_niches(reg):
    def add(name, niche, job, fn=None, binding=None):
        return reg.add(Specialist(name, niche, job, fn=fn, binding=binding))

    # sec-code — one finder per weakness class (phase 2's `security`
    # niche keeps its six; these are the classes it did not cover)
    add("path-traversal-finder", "sec-code",
        "find path-traversal shapes (non-literal open paths, '..')", FS.path_traversal_finder)
    add("insecure-random-finder", "sec-code",
        "find random.* guarding secrets (tokens, passwords, OTPs)", FS.insecure_random_finder)
    add("unsafe-yaml-load-finder", "sec-code",
        "find yaml.load without SafeLoader / unsafe_load", FS.unsafe_yaml_load_finder)
    add("tls-verify-off-finder", "sec-code",
        "find verify=False (TLS checking disabled)", FS.tls_verify_off_finder)
    add("ssrf-finder", "sec-code",
        "find HTTP requests with non-literal (steerable) URLs", FS.ssrf_finder)

    # sec-deps — dependency risk, one check per specialist
    add("known-bad-version-finder", "sec-deps",
        "find pins matching the local known-bad version table", FS.known_bad_version_finder)
    add("typosquat-suspect-finder", "sec-deps",
        "find requirement names one edit from a popular package", FS.typosquat_suspect_finder)
    add("setup-exec-finder", "sec-deps",
        "find command execution inside a setup/install file", FS.setup_exec_finder)

    # sec-config — hardening checks, one per specialist
    add("debug-true-finder", "sec-config",
        "find debug switched on in config/code text", FS.debug_true_finder)
    add("wildcard-bind-finder", "sec-config",
        "find 0.0.0.0 / :: binds (exposed on every interface)", FS.wildcard_bind_finder)
    add("chmod-777-finder", "sec-config",
        "find chmod 777 (world-writable)", FS.chmod_777_finder)
    add("docker-root-finder", "sec-config",
        "check a Dockerfile runs as a non-root USER", FS.docker_root_finder)
    add("env-secret-finder", "sec-config",
        "find env lines with secret keys and real-looking values", FS.env_secret_finder)

    # sec-inventory — his own machines' exposure, read-only
    add("tcp-listener-parser", "sec-inventory",
        "parse /proc/net/tcp text into listening sockets", FS.tcp_listener_parser)
    add("listening-port-lister", "sec-inventory",
        "list this machine's listening TCP ports from /proc", FS.listening_port_lister)
    add("service-name-mapper", "sec-inventory",
        "name the probable service for one port", FS.service_name_mapper)
    add("external-bind-checker", "sec-inventory",
        "flag listeners bound to every interface, not localhost", FS.external_bind_checker)

    # sec-scan — credential exposure in his own files
    add("aws-key-finder", "sec-scan",
        "find AWS access-key shapes (locations only)", FS.aws_key_finder)
    add("private-key-finder", "sec-scan",
        "find private-key block headers (locations only)", FS.private_key_finder)
    add("workspace-secret-scanner", "sec-scan",
        "scan his own files for credential exposure, composing the "
        "sec-scan finders + the secret-line model",
        make_workspace_secret_scanner(reg))
    return reg
