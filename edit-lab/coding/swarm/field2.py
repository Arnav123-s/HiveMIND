"""Field-coverage specialists, part 2 (phase 2): the artifact/language
niches — data formats, SQL, dependencies, build files, version control,
regex, shell, language identification, web text.

Same conventions as field.py. Two of these shell out to a *checker*
only (bash -n, node --check): they verify syntax, they never execute
the program under test.
"""
import csv
import io
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from html.parser import HTMLParser
from pathlib import Path


# --------------------------------------------------------------------- data
def json_validity_checker(task):
    """Does this text parse as JSON? ok = it does."""
    try:
        value = json.loads(task["text"])
        return {"ok": True, "output": type(value).__name__,
                "evidence": "valid JSON"}
    except json.JSONDecodeError as e:
        return {"ok": False, "output": None,
                "evidence": f"invalid JSON: {e.msg} at line {e.lineno} col {e.colno}"}


def json_key_lister(task):
    """Top-level keys of a JSON object."""
    try:
        value = json.loads(task["text"])
    except json.JSONDecodeError as e:
        return {"ok": False, "output": None, "evidence": f"invalid JSON: {e.msg}"}
    if not isinstance(value, dict):
        return {"ok": False, "output": None,
                "evidence": f"top level is {type(value).__name__}, not an object"}
    return {"ok": True, "output": sorted(value.keys()),
            "evidence": f"{len(value)} top-level key(s)"}


def csv_shape_checker(task):
    """Every CSV row has the header's column count. ok = uniform."""
    rows = list(csv.reader(io.StringIO(task["text"])))
    if not rows:
        return {"ok": False, "output": None, "evidence": "no rows (no header)"}
    width = len(rows[0])
    bad = [(i, len(r)) for i, r in enumerate(rows) if len(r) != width]
    return {"ok": not bad,
            "output": {"rows": len(rows) - 1, "columns": width, "bad_rows": bad},
            "evidence": f"{len(rows) - 1} data row(s), {width} column(s), "
                        f"{len(bad)} ragged row(s)"}


def csv_column_lister(task):
    """The header row of a CSV text."""
    rows = list(csv.reader(io.StringIO(task["text"])))
    if not rows:
        return {"ok": False, "output": None, "evidence": "no rows"}
    return {"ok": True, "output": rows[0], "evidence": f"{len(rows[0])} column(s)"}


def toml_validity_checker(task):
    """Does this text parse as TOML? ok = it does."""
    try:
        tomllib.loads(task["text"])
        return {"ok": True, "output": True, "evidence": "valid TOML"}
    except tomllib.TOMLDecodeError as e:
        return {"ok": False, "output": None, "evidence": f"invalid TOML: {e}"}


# ---------------------------------------------------------------------- sql
_SQL_KINDS = {"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
              "ALTER", "WITH", "REPLACE", "TRUNCATE", "GRANT", "REVOKE"}


def sql_statement_classifier(task):
    """Classify a SQL statement by its first keyword."""
    text = task["sql"].strip()
    m = re.match(r"([A-Za-z]+)", text)
    if not m:
        return {"ok": False, "output": None, "evidence": "empty statement"}
    kind = m.group(1).upper()
    if kind in _SQL_KINDS:
        return {"ok": True, "output": kind, "evidence": f"statement kind {kind}"}
    return {"ok": False, "output": kind,
            "evidence": f"unrecognized leading keyword {kind}", "gap": "unknown-sql-kind"}


def sql_table_extractor(task):
    """Table names after FROM / JOIN, in order of appearance."""
    out = []
    for m in re.finditer(r"(?i)\b(?:from|join)\s+([A-Za-z_][\w.]*)", task["sql"]):
        if m.group(1) not in out:
            out.append(m.group(1))
    return {"ok": True, "output": out, "evidence": f"{len(out)} table(s)"}


def sql_where_checker(task):
    """UPDATE/DELETE without a WHERE clause rewrites everything.
    ok = safe (or not an UPDATE/DELETE)."""
    cls = sql_statement_classifier(task)
    if not cls["ok"] or cls["output"] not in ("UPDATE", "DELETE"):
        return {"ok": True, "output": cls["output"],
                "evidence": "not an UPDATE/DELETE statement"}
    if re.search(r"(?i)\bwhere\b", task["sql"]):
        return {"ok": True, "output": cls["output"], "evidence": "WHERE clause present"}
    return {"ok": False, "output": cls["output"],
            "evidence": f"{cls['output']} without WHERE affects every row"}


_SQL_KEYWORDS = ["SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER",
                 "OUTER", "ON", "GROUP", "ORDER", "BY", "LIMIT", "OFFSET",
                 "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
                 "CREATE", "TABLE", "AND", "OR", "NOT", "NULL", "AS",
                 "DISTINCT", "HAVING", "UNION", "ALL", "BETWEEN", "LIKE", "IN"]


def sql_keyword_caser(task):
    """Uppercase SQL keywords. Lexical: keywords inside string literals
    are uppercased too — the evidence says so."""
    out, n = task["sql"], 0
    for kw in _SQL_KEYWORDS:
        out, k = re.subn(rf"(?i)\b{kw}\b", kw, out)
        n += k
    return {"ok": True, "output": out,
            "evidence": f"{n} keyword occurrence(s) uppercased (lexical)"}


# -------------------------------------------------------------- dependencies
def requirements_parser(task):
    """Parse requirements text into (name, spec) pairs."""
    out = []
    for line in task["text"].splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("-"):
            continue
        s = s.split(" #", 1)[0].strip()
        m = re.match(r"([A-Za-z0-9_.\-]+)\s*(.*)$", s)
        if m:
            out.append({"name": m.group(1), "spec": m.group(2).strip()})
    return {"ok": True, "output": out, "evidence": f"{len(out)} requirement(s)"}


def unpinned_dependency_finder(task):
    """Requirements with no == pin (bare names and loose ranges alike)."""
    parsed = requirements_parser(task)["output"]
    bad = [r["name"] for r in parsed if not r["spec"].startswith("==")]
    return {"ok": True, "output": bad,
            "evidence": f"{len(bad)} requirement(s) without an == pin"}


def import_origin_classifier(task):
    """stdlib, third-party, or local — for one module name."""
    root = task["module"].split(".")[0]
    if root in task.get("locals", []):
        origin = "local"
    elif root in sys.stdlib_module_names:
        origin = "stdlib"
    else:
        origin = "third-party"
    return {"ok": True, "output": origin, "evidence": f"{root}: {origin}"}


def _version_tuple(text):
    parts = []
    for p in text.strip().split("."):
        digits = re.match(r"\d+", p)
        if digits is None:
            return None
        parts.append(int(digits.group(0)))
    return tuple(parts)


def version_satisfies_checker(task):
    """Does a dotted-numeric version satisfy a comma-AND spec of
    ==/!=/>=/<=/>/< clauses?"""
    version = _version_tuple(task["version"])
    if version is None:
        return {"ok": False, "output": None,
                "evidence": f"unparsable version {task['version']!r}"}
    ops = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b,
           ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
           ">": lambda a, b: a > b, "<": lambda a, b: a < b}
    for clause in task["spec"].split(","):
        m = re.match(r"\s*(==|!=|>=|<=|>|<)\s*([\w.\-]+)\s*$", clause)
        if not m:
            return {"ok": False, "output": None,
                    "evidence": f"unparsable spec clause {clause!r}"}
        want = _version_tuple(m.group(2))
        if want is None:
            return {"ok": False, "output": None,
                    "evidence": f"unparsable spec version {m.group(2)!r}"}
        n = max(len(version), len(want))
        a = version + (0,) * (n - len(version))
        b = want + (0,) * (n - len(want))
        if not ops[m.group(1)](a, b):
            return {"ok": False, "output": False,
                    "evidence": f"{task['version']} fails clause {clause.strip()!r}"}
    return {"ok": True, "output": True,
            "evidence": f"{task['version']} satisfies {task['spec']!r}"}


# -------------------------------------------------------------------- build
def pyproject_field_checker(task):
    """project.name / project.version present in pyproject text?"""
    try:
        data = tomllib.loads(task["text"])
    except tomllib.TOMLDecodeError as e:
        return {"ok": False, "output": None, "evidence": f"invalid TOML: {e}"}
    project = data.get("project", {})
    missing = [f for f in ("name", "version") if f not in project]
    return {"ok": not missing,
            "output": {"name": project.get("name"),
                       "version": project.get("version"), "missing": missing},
            "evidence": "project name+version present" if not missing
                        else f"missing project fields: {missing}"}


_DOCKER_INSTRUCTIONS = {"FROM", "RUN", "CMD", "ENTRYPOINT", "COPY", "ADD",
                        "ENV", "ARG", "WORKDIR", "EXPOSE", "USER", "VOLUME",
                        "LABEL"}


def dockerfile_instruction_lister(task):
    """The instruction keywords of a Dockerfile, in order."""
    out = []
    for line in task["text"].splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        first = s.split(None, 1)[0].upper()
        if first in _DOCKER_INSTRUCTIONS:
            out.append(first)
    return {"ok": True, "output": out, "evidence": f"{len(out)} instruction(s)"}


def makefile_target_lister(task):
    """Target names in a Makefile (column-0 `name:` lines, not variables,
    not dot-targets like .PHONY)."""
    out = []
    for line in task["text"].splitlines():
        m = re.match(r"^([A-Za-z0-9_/\-]+)\s*:(?![=])", line)
        if m and not m.group(1).startswith("."):
            out.append(m.group(1))
    return {"ok": True, "output": out, "evidence": f"{len(out)} target(s)"}


# ---------------------------------------------------------------------- vcs
def conflict_marker_finder(task):
    """Merge-conflict markers left in a text. ok = none."""
    bad = []
    for i, line in enumerate(task["text"].splitlines(), 1):
        if line.startswith("<<<<<<<") or line.startswith(">>>>>>>") \
                or line.rstrip() == "=======":
            bad.append({"line": i, "marker": line[:7]})
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} conflict marker(s)"}


def diff_stat_counter(task):
    """Added/removed line counts of a unified diff."""
    added = removed = 0
    for line in task["text"].splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return {"ok": True, "output": {"added": added, "removed": removed},
            "evidence": f"+{added} -{removed}"}


_COMMIT_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\([^\r\n()]+\))?(!)?:\s+\S")


def conventional_commit_checker(task):
    """First line follows Conventional Commits. ok = it does."""
    first = task["text"].splitlines()[0] if task["text"].strip() else ""
    ok = bool(_COMMIT_RE.match(first))
    return {"ok": ok, "output": ok,
            "evidence": "conventional commit format" if ok
                        else f"not conventional: {first[:60]!r}"}


# -------------------------------------------------------------------- regex
def regex_compile_checker(task):
    """Does this pattern compile? ok = it does."""
    try:
        re.compile(task["pattern"])
        return {"ok": True, "output": True, "evidence": "pattern compiles"}
    except re.error as e:
        return {"ok": False, "output": None, "evidence": f"re.error: {e}"}


def regex_match_runner(task):
    """Which of the sample strings does the pattern search-hit?"""
    try:
        rx = re.compile(task["pattern"])
    except re.error as e:
        return {"ok": False, "output": None, "evidence": f"re.error: {e}"}
    out = [bool(rx.search(s)) for s in task["samples"]]
    return {"ok": True, "output": out,
            "evidence": f"{sum(out)}/{len(out)} sample(s) match"}


def nested_quantifier_finder(task):
    """A quantified group containing a quantifier — the classic
    catastrophic-backtracking shape. Lite scan (no nested parens).
    ok = none found."""
    bad = [m.group(0) for m in re.finditer(r"\([^()]*[+*]\)[+*]", task["pattern"])]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} nested-quantifier shape(s)"}


# -------------------------------------------------------------------- shell
def _syntax_check(argv, suffix, code, timeout=15):
    with tempfile.TemporaryDirectory(prefix="swarm_syntax_") as td:
        f = Path(td) / f"program{suffix}"
        f.write_text(code)
        try:
            r = subprocess.run(argv + [str(f)], capture_output=True, text=True,
                               timeout=timeout)
        except FileNotFoundError as e:
            return {"ok": False, "output": None,
                    "evidence": f"checker unavailable: {e.filename}", "gap": "no-checker"}
        first = (r.stderr.strip().splitlines() or [""])[-1]
        return {"ok": r.returncode == 0, "output": r.returncode,
                "evidence": "syntax ok" if r.returncode == 0 else f"syntax error: {first[:160]}"}


def bash_syntax_checker(task):
    """bash -n: parses the script, never executes it."""
    return _syntax_check(["bash", "-n"], ".sh", task["code"])


def shebang_checker(task):
    """First line names an interpreter. ok = a shebang is present."""
    first = task["text"].splitlines()[0] if task["text"] else ""
    if not first.startswith("#!"):
        return {"ok": False, "output": None, "evidence": "no shebang on line 1"}
    interp = first[2:].strip().split()[-1].split("/")[-1]
    return {"ok": True, "output": interp, "evidence": f"shebang interpreter: {interp}"}


def unquoted_variable_finder(task):
    """$VAR expansions outside any quotes (word-splitting risk).
    Quote state is tracked per line; comments are skipped. Heuristic,
    stated here."""
    out = []
    for i, line in enumerate(task["text"].splitlines(), 1):
        if line.strip().startswith("#"):
            continue
        in_s = in_d = False
        j = 0
        while j < len(line):
            ch = line[j]
            if ch == "'" and not in_d:
                in_s = not in_s
            elif ch == '"' and not in_s:
                in_d = not in_d
            elif ch == "$" and not in_s and not in_d:
                m = re.match(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", line[j:])
                if m:
                    out.append({"line": i, "var": m.group(1)})
                    j += len(m.group(0)) - 1
            j += 1
    return {"ok": True, "output": out,
            "evidence": f"{len(out)} unquoted expansion(s) (heuristic)"}


def dangerous_rm_finder(task):
    """rm with both recursive and force flags; danger rises with
    variables, / ~ or * in the target."""
    out = []
    for i, line in enumerate(task["text"].splitlines(), 1):
        if not re.search(r"\brm\b", line):
            continue
        flags = "".join(re.findall(r"(?<!\w)-([a-zA-Z]+)", line))
        if "r" in flags and "f" in flags:
            level = "high" if re.search(r"(\$|~|\*|\s/(\s|$))", line) else "recursive-force"
            out.append({"line": i, "level": level, "text": line.strip()[:80]})
    return {"ok": True, "output": out,
            "evidence": f"{len(out)} rm -rf site(s)"}


# ---------------------------------------------------------------- languages
_EXT_LANG = {".py": "python", ".js": "javascript", ".ts": "typescript",
             ".json": "json", ".toml": "toml", ".sql": "sql", ".sh": "shell",
             ".bash": "shell", ".html": "html", ".css": "css", ".md": "markdown",
             ".yml": "yaml", ".yaml": "yaml", ".rs": "rust", ".go": "go",
             ".java": "java", ".c": "c", ".h": "c", ".cpp": "cpp",
             ".hpp": "cpp", ".rb": "ruby"}


def language_identifier(task):
    """Name the language: by filename extension first, else by shebang."""
    name = task.get("filename", "")
    if name:
        lang = _EXT_LANG.get(Path(name).suffix.lower())
        if lang:
            return {"ok": True, "output": lang, "evidence": f"extension of {name}"}
    text = task.get("text", "")
    if text.startswith("#!"):
        first = text.splitlines()[0]
        for hint, lang in (("python", "python"), ("bash", "shell"),
                           ("sh", "shell"), ("node", "javascript")):
            if hint in first:
                return {"ok": True, "output": lang, "evidence": f"shebang: {first[:60]}"}
    return {"ok": False, "output": "unknown",
            "evidence": "no extension match, no shebang", "gap": "unknown-language"}


def javascript_syntax_checker(task):
    """node --check: parses the file, never executes it."""
    return _syntax_check(["node", "--check"], ".js", task["code"])


def c_brace_balance_checker(task):
    """Balance of () {} [] in C-like code, ignoring strings and comments."""
    text = task["code"] if "code" in task else task.get("text", "")
    stack, pairs = [], {")": "(", "}": "{", "]": "["}
    i, state = 0, None  # state: None | "'" | '"' | 'line' | 'block'
    while i < len(text):
        ch, nxt = text[i], text[i + 1] if i + 1 < len(text) else ""
        if state == "line":
            if ch == "\n":
                state = None
        elif state == "block":
            if ch == "*" and nxt == "/":
                state, i = None, i + 1
        elif state in ("'", '"'):
            if ch == "\\":
                i += 1
            elif ch == state:
                state = None
        else:
            if ch == "/" and nxt == "/":
                state = "line"
            elif ch == "/" and nxt == "*":
                state = "block"
            elif ch in ("'", '"'):
                state = ch
            elif ch in "([{":
                stack.append(ch)
            elif ch in ")]}":
                if not stack or stack[-1] != pairs[ch]:
                    return {"ok": False, "output": {"at": i, "char": ch},
                            "evidence": f"mismatched {ch!r} at offset {i}"}
                stack.pop()
        i += 1
    if stack:
        return {"ok": False, "output": {"unclosed": stack},
                "evidence": f"{len(stack)} unclosed opener(s): {stack}"}
    if state in ("'", '"', "block"):
        return {"ok": False, "output": {"unterminated": state},
                "evidence": f"unterminated {state} at end of input"}
    return {"ok": True, "output": True, "evidence": "all brackets balanced"}


# ---------------------------------------------------------------------- web
class _TagBalance(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.errors.append(f"</{tag}> closed while <{self.stack[-1]}> still open")
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            self.stack.pop()
        else:
            self.errors.append(f"stray </{tag}>")


def html_tag_balance_checker(task):
    """HTML tags open and close in nesting order. ok = balanced."""
    parser = _TagBalance()
    parser.feed(task["text"])
    parser.close()
    errors = parser.errors + [f"unclosed <{t}>" for t in parser.stack]
    return {"ok": not errors, "output": errors,
            "evidence": "tags balanced" if not errors else f"{len(errors)} tag error(s)"}


def url_extractor(task):
    """http(s) URLs in a text, in order, trailing punctuation stripped."""
    out = []
    for m in re.finditer(r"https?://[^\s'\"<>)\]]+", task["text"]):
        url = m.group(0).rstrip(".,;:")
        if url not in out:
            out.append(url)
    return {"ok": True, "output": out, "evidence": f"{len(out)} URL(s)"}
