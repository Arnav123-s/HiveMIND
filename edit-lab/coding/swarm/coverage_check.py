"""Coverage verification for the phase-2 field niches (PLAN.md §15/§16).

    python3 -m swarm.coverage_check

Builds the swarm, then runs every probe below against the named
specialist: each probe is (task, expected-envelope-subset) with at
least one discriminating case (a clean input and a dirty one, a hit
and a miss). A constructed specialist counts as verified — and is
marked running-alone — only if ALL its probes match. Model-bound
specialists have no probes here: they stay in-development until
their backends load (PLAN section 14).

demo.py imports run_probes so the demo's development marks rest on
exactly this evidence.
"""

# ------------------------------------------------------------- fixtures
SRC = '''"""Module docstring."""
import os
import sys
from collections import OrderedDict

CONSTANT = 3


def greet(name, punct="!"):
    """Say hello."""
    return "hi " + name + punct


class Calc:
    def add(self, a, b):
        return a + b

    def total(self, xs):
        t = 0
        for x in xs:
            if x > 0:
                t += x
        return t


def fact(n):
    return 1 if n <= 1 else n * fact(n - 1)
'''

TEST_SRC = '''def test_a():
    pass


def helper():
    pass


class TestThing:
    def test_b(self):
        pass

    def helper(self):
        pass
'''

# ------------------------------------------------------------- probes
PROBES = {
    # reading
    "import-lister": [
        ({"code": SRC}, {"ok": True, "output": ["collections", "os", "sys"]}),
        ({"code": "x = 1\n"}, {"ok": True, "output": []}),
    ],
    "function-lister": [
        ({"code": SRC},
         {"ok": True, "output": ["greet", "Calc.add", "Calc.total", "fact"]}),
    ],
    "class-lister": [
        ({"code": SRC},
         {"ok": True, "output": [{"class": "Calc", "methods": ["add", "total"]}]}),
    ],
    "signature-extractor": [
        ({"code": SRC, "name": "greet"},
         {"ok": True, "output": "greet(name, punct='!')"}),
        ({"code": SRC, "name": "nope"}, {"ok": False}),
    ],
    "docstring-extractor": [
        ({"code": SRC}, {"ok": True, "output": "Module docstring."}),
        ({"code": SRC, "name": "greet"}, {"ok": True, "output": "Say hello."}),
        ({"code": SRC, "name": "Calc"}, {"ok": True, "output": None}),
    ],
    "call-finder": [
        ({"code": SRC}, {"ok": True, "output": ["fact"]}),
    ],
    "branch-counter": [
        ({"code": SRC, "name": "total"}, {"ok": True, "output": 2}),
        ({"code": SRC}, {"ok": True, "output": 3}),
    ],
    "recursion-detector": [
        ({"code": SRC}, {"ok": True, "output": ["fact"]}),
        ({"code": "def f():\n    return 1\n"}, {"ok": True, "output": []}),
    ],
    "code-line-counter": [
        ({"code": "x = 1\n\n# comment\ny = 2\n"}, {"ok": True, "output": 2}),
    ],
    # testing extension
    "test-function-counter": [
        ({"code": TEST_SRC}, {"ok": True, "output": 2}),
        ({"code": SRC}, {"ok": True, "output": 0}),
    ],
    "assertion-counter": [
        ({"code": "class T:\n    def test_m(self):\n"
                  "        self.assertEqual(1, 1)\n        assert True\n"},
         {"ok": True, "output": 2}),
        ({"code": "x = 1\n"}, {"ok": True, "output": 0}),
    ],
    "untested-function-finder": [
        ({"code": "def used_fn():\n    pass\n\ndef unused_fn():\n    pass\n",
          "tests": "def test_used():\n    used_fn()\n"},
         {"ok": True, "output": ["unused_fn"]}),
    ],
    # linting
    "line-length-checker": [
        ({"text": "short\n" + "x" * 101 + "\nok\n", "limit": 100},
         {"ok": False, "output": [(2, 101)]}),
        ({"text": "short\nok\n"}, {"ok": True, "output": []}),
    ],
    "trailing-whitespace-checker": [
        ({"text": "a = 1 \nb = 2\n"}, {"ok": False, "output": [1]}),
        ({"text": "a = 1\nb = 2\n"}, {"ok": True, "output": []}),
    ],
    "tab-indent-checker": [
        ({"text": "\tx = 1\ny = 2\n"}, {"ok": False, "output": [1]}),
        ({"text": "    x = 1\n"}, {"ok": True, "output": []}),
    ],
    "final-newline-checker": [
        ({"text": "abc\n"}, {"ok": True}),
        ({"text": "abc"}, {"ok": False}),
        ({"text": "abc\n\n"}, {"ok": False}),
    ],
    "function-name-case-checker": [
        ({"code": "def BadName():\n    pass\n"}, {"ok": False, "output": ["BadName"]}),
        ({"code": "def good_name():\n    pass\n"}, {"ok": True, "output": []}),
    ],
    "constant-name-case-checker": [
        ({"code": "max_size = 5\nLIMIT = 5\n"},
         {"ok": False, "output": ["max_size"]}),
        ({"code": "LIMIT = 5\nx = compute()\n"}, {"ok": True, "output": []}),
    ],
    "wildcard-import-checker": [
        ({"code": "from os import *\nimport sys\n"},
         {"ok": False, "output": [{"module": "os", "line": 1}]}),
        ({"code": "import sys\n"}, {"ok": True, "output": []}),
    ],
    "bare-except-checker": [
        ({"code": "try:\n    pass\nexcept:\n    pass\n"},
         {"ok": False, "output": [3]}),
        ({"code": "try:\n    pass\nexcept ValueError:\n    pass\n"},
         {"ok": True, "output": []}),
    ],
    "print-call-checker": [
        ({"code": "print('x')\n"}, {"ok": False, "output": [1]}),
        ({"code": "x = 1\n"}, {"ok": True, "output": []}),
    ],
    # refactoring
    "trailing-whitespace-stripper": [
        ({"code": "a = 1  \nb = 2\t\n"}, {"ok": True, "output": "a = 1\nb = 2\n"}),
    ],
    "tab-expander": [
        ({"code": "\tx = 1\n\t\ty = 2\n"},
         {"ok": True, "output": "    x = 1\n        y = 2\n"}),
    ],
    "final-newline-fixer": [
        ({"code": "abc"}, {"ok": True, "output": "abc\n"}),
        ({"code": "abc\n\n\n"}, {"ok": True, "output": "abc\n"}),
    ],
    "import-block-sorter": [
        ({"code": "import sys\nimport os\n\nx = 1\n"},
         {"ok": True, "output": "import os\nimport sys\n\nx = 1\n"}),
        ({"code": "import os\nfrom x import (\n    y)\n"}, {"ok": False}),
    ],
    "unused-import-remover": [
        ({"code": "import os\nimport json\n\nprint(json.dumps({}))\n"},
         {"ok": True, "output": "import json\n\nprint(json.dumps({}))\n"}),
        ({"code": "import numpy as np\nprint(np.array([]))\n"},
         {"ok": True, "output": "import numpy as np\nprint(np.array([]))\n"}),
    ],
    "rename-symbol": [
        ({"code": "x = 1\nprint(x + x)\n", "old": "x", "new": "total"},
         {"ok": True, "output": "total = 1\nprint(total + total)\n"}),
        ({"code": "x = 1\n", "old": "zz", "new": "total"}, {"ok": False}),
    ],
    # documenting
    "docstring-coverage-checker": [
        ({"code": "def documented():\n    \"\"\"Doc.\"\"\"\n\n"
                  "def undocumented():\n    pass\n"},
         {"ok": False,
          "output": {"missing": ["undocumented"], "covered": 1, "total": 2}}),
        ({"code": "def documented():\n    \"\"\"Doc.\"\"\"\n"},
         {"ok": True,
          "output": {"missing": [], "covered": 1, "total": 1}}),
    ],
    "todo-marker-finder": [
        ({"code": "# TODO: fix\ny = 1  # FIXME later\n"},
         {"ok": True, "output": [{"line": 1, "marker": "TODO", "text": "# TODO: fix"},
                                  {"line": 2, "marker": "FIXME",
                                   "text": "y = 1  # FIXME later"}]}),
        ({"code": "y = 1\n"}, {"ok": True, "output": []}),
    ],
    "license-header-checker": [
        ({"text": "# Copyright 2026 Arnav\n# more\nx = 1\n"}, {"ok": True}),
        ({"text": "x = 1\ny = 2\n"}, {"ok": False}),
    ],
    "comment-density-counter": [
        ({"text": "# c1\nx = 1\n# c2\ny = 2\n"}, {"ok": True, "output": 0.5}),
    ],
    # security
    "hardcoded-secret-finder": [
        ({"code": "api_key = \"abc123\"\nname = \"x\"\n"},
         {"ok": False, "output": [{"name": "api_key", "line": 1}]}),
        ({"code": "password = \"\"\ntoken = get_token()\n"},
         {"ok": True, "output": []}),
    ],
    "eval-exec-finder": [
        ({"code": "eval('1')\n"}, {"ok": False, "output": [1]}),
        ({"code": "evaluate(1)\n"}, {"ok": True, "output": []}),
    ],
    "pickle-load-finder": [
        ({"code": "import pickle\npickle.loads(data)\n"},
         {"ok": False, "output": [2]}),
        ({"code": "from pickle import loads\nloads(data)\n"},
         {"ok": False, "output": [2]}),
        ({"code": "import json\njson.loads(s)\n"}, {"ok": True, "output": []}),
    ],
    "sql-interpolation-finder": [
        ({"code": "cur.execute(f\"SELECT * FROM t WHERE id={i}\")\n"},
         {"ok": False, "output": [1]}),
        ({"code": "cur.execute(\"SELECT * FROM t WHERE id=?\", (i,))\n"},
         {"ok": True, "output": []}),
        ({"code": "cur.execute(\"SELECT * FROM t WHERE id=%s\" % i)\n"},
         {"ok": False, "output": [1]}),
    ],
    "shell-true-finder": [
        ({"code": "import subprocess\nsubprocess.run('ls', shell=True)\n"},
         {"ok": False, "output": [2]}),
        ({"code": "import subprocess\nsubprocess.run(['ls'], shell=False)\n"},
         {"ok": True, "output": []}),
    ],
    "weak-hash-finder": [
        ({"code": "import hashlib\nhashlib.md5(b'x')\n"},
         {"ok": False, "output": [2]}),
        ({"code": "import hashlib\nhashlib.sha256(b'x')\n"},
         {"ok": True, "output": []}),
    ],
    # performance
    "loop-depth-finder": [
        ({"code": "def f(m):\n    for row in m:\n        for v in row:\n"
                  "            print(v)\n"},
         {"ok": True, "output": {"max_depth": 2, "deep_functions": ["f"]}}),
        ({"code": "x = 1\n"},
         {"ok": True, "output": {"max_depth": 0, "deep_functions": []}}),
    ],
    "string-concat-in-loop-finder": [
        ({"code": "out = \"\"\nfor w in words:\n    out += w\n"},
         {"ok": True, "output": [3]}),
        ({"code": "out = []\nfor w in words:\n    out.append(w)\n"},
         {"ok": True, "output": []}),
    ],
    "global-mutation-finder": [
        ({"code": "counter = 0\ndef bump():\n    global counter\n    counter += 1\n"},
         {"ok": True, "output": ["bump"]}),
        ({"code": "def f():\n    return 1\n"}, {"ok": True, "output": []}),
    ],
}

PROBES.update({
    # data
    "json-validity-checker": [
        ({"text": "{\"a\": 1}"}, {"ok": True, "output": "dict"}),
        ({"text": "{bad"}, {"ok": False}),
    ],
    "json-key-lister": [
        ({"text": "{\"b\": 1, \"a\": 2}"}, {"ok": True, "output": ["a", "b"]}),
        ({"text": "[1, 2]"}, {"ok": False}),
    ],
    "csv-shape-checker": [
        ({"text": "a,b\n1,2\n3\n"},
         {"ok": False,
          "output": {"rows": 2, "columns": 2, "bad_rows": [(2, 1)]}}),
        ({"text": "a,b\n1,2\n"},
         {"ok": True,
          "output": {"rows": 1, "columns": 2, "bad_rows": []}}),
    ],
    "csv-column-lister": [
        ({"text": "name,age\nx,3\n"}, {"ok": True, "output": ["name", "age"]}),
    ],
    "toml-validity-checker": [
        ({"text": "a = 1\n"}, {"ok": True}),
        ({"text": "a = \n"}, {"ok": False}),
    ],
    # sql
    "sql-statement-classifier": [
        ({"sql": "select * from t"}, {"ok": True, "output": "SELECT"}),
        ({"sql": "DELETE FROM t WHERE id=1"}, {"ok": True, "output": "DELETE"}),
        ({"sql": "frobnicate x"}, {"ok": False}),
    ],
    "sql-table-extractor": [
        ({"sql": "SELECT * FROM users JOIN orders ON users.id = orders.uid"},
         {"ok": True, "output": ["users", "orders"]}),
    ],
    "sql-where-checker": [
        ({"sql": "DELETE FROM users"}, {"ok": False}),
        ({"sql": "DELETE FROM users WHERE id = 1"}, {"ok": True}),
        ({"sql": "SELECT * FROM users"}, {"ok": True}),
    ],
    "sql-keyword-caser": [
        ({"sql": "select name from users where id = 1"},
         {"ok": True, "output": "SELECT name FROM users WHERE id = 1"}),
    ],
    # dependencies
    "requirements-parser": [
        ({"text": "requests==2.31.0\n# comment\nflask>=2.0\n\n"},
         {"ok": True, "output": [{"name": "requests", "spec": "==2.31.0"},
                                  {"name": "flask", "spec": ">=2.0"}]}),
    ],
    "unpinned-dependency-finder": [
        ({"text": "requests==2.31.0\nflask>=2.0\n"},
         {"ok": True, "output": ["flask"]}),
        ({"text": "a==1.0\nb==2.0\n"}, {"ok": True, "output": []}),
    ],
    "import-origin-classifier": [
        ({"module": "os"}, {"ok": True, "output": "stdlib"}),
        ({"module": "os.path"}, {"ok": True, "output": "stdlib"}),
        ({"module": "requests"}, {"ok": True, "output": "third-party"}),
        ({"module": "myapp", "locals": ["myapp"]}, {"ok": True, "output": "local"}),
    ],
    "version-satisfies-checker": [
        ({"version": "1.2.3", "spec": ">=1.2,<2.0"}, {"ok": True, "output": True}),
        ({"version": "2.0.0", "spec": ">=1.2,<2.0"}, {"ok": False, "output": False}),
        ({"version": "1.2", "spec": "==1.2.0"}, {"ok": True, "output": True}),
    ],
    # build
    "pyproject-field-checker": [
        ({"text": "[project]\nname = \"x\"\nversion = \"1.0\"\n"}, {"ok": True}),
        ({"text": "[project]\nname = \"x\"\n"},
         {"ok": False,
          "output": {"name": "x", "version": None, "missing": ["version"]}}),
    ],
    "dockerfile-instruction-lister": [
        ({"text": "FROM python:3.12\n# comment\nRUN pip install x\nCOPY . .\n"},
         {"ok": True, "output": ["FROM", "RUN", "COPY"]}),
    ],
    "makefile-target-lister": [
        ({"text": "build:\n\tgcc x\nclean:\n\trm x\nVAR := 1\n.PHONY: build\n"},
         {"ok": True, "output": ["build", "clean"]}),
    ],
    # vcs
    "conflict-marker-finder": [
        ({"text": "a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> branch\n"},
         {"ok": False, "output": [{"line": 2, "marker": "<<<<<<<"},
                                   {"line": 4, "marker": "======="},
                                   {"line": 6, "marker": ">>>>>>>"}]}),
        ({"text": "clean\ntext\n"}, {"ok": True, "output": []}),
    ],
    "diff-stat-counter": [
        ({"text": "+++ b/f\n--- a/f\n+new\n-old\n context\n+another\n"},
         {"ok": True, "output": {"added": 2, "removed": 1}}),
    ],
    "conventional-commit-checker": [
        ({"text": "feat(parser): add thing\n"}, {"ok": True}),
        ({"text": "fix: typo\n"}, {"ok": True}),
        ({"text": "fixed the stuff\n"}, {"ok": False}),
    ],
    # regex
    "regex-compile-checker": [
        ({"pattern": r"\d+"}, {"ok": True}),
        ({"pattern": "("}, {"ok": False}),
    ],
    "regex-match-runner": [
        ({"pattern": r"^\d+$", "samples": ["123", "12a", ""]},
         {"ok": True, "output": [True, False, False]}),
    ],
    "nested-quantifier-finder": [
        ({"pattern": "(a+)+"}, {"ok": False, "output": ["(a+)+"]}),
        ({"pattern": "(ab)+"}, {"ok": True, "output": []}),
        ({"pattern": "a+"}, {"ok": True, "output": []}),
    ],
    # shell
    "bash-syntax-checker": [
        ({"code": "if true; then\n  echo hi\nfi\n"}, {"ok": True}),
        ({"code": "if true; then\n  echo hi\n"}, {"ok": False}),
    ],
    "shebang-checker": [
        ({"text": "#!/usr/bin/env bash\necho hi\n"}, {"ok": True, "output": "bash"}),
        ({"text": "#!/usr/bin/python3\n"}, {"ok": True, "output": "python3"}),
        ({"text": "echo hi\n"}, {"ok": False}),
    ],
    "unquoted-variable-finder": [
        ({"text": "rm $TARGET\n"},
         {"ok": True, "output": [{"line": 1, "var": "TARGET"}]}),
        ({"text": "rm \"$TARGET\"\n"}, {"ok": True, "output": []}),
        ({"text": "cp $SRC \"$DST\"\n"},
         {"ok": True, "output": [{"line": 1, "var": "SRC"}]}),
    ],
    "dangerous-rm-finder": [
        ({"text": "rm -rf $BUILD_DIR\n"},
         {"ok": True, "output": [{"line": 1, "level": "high",
                                   "text": "rm -rf $BUILD_DIR"}]}),
        ({"text": "rm -rf ./tmp\n"},
         {"ok": True, "output": [{"line": 1, "level": "recursive-force",
                                   "text": "rm -rf ./tmp"}]}),
        ({"text": "rm file.txt\n"}, {"ok": True, "output": []}),
    ],
    # languages
    "language-identifier": [
        ({"filename": "x.py"}, {"ok": True, "output": "python"}),
        ({"filename": "x.zzz", "text": "#!/bin/bash\necho hi\n"},
         {"ok": True, "output": "shell"}),
        ({"filename": "", "text": "hello\n"}, {"ok": False, "output": "unknown"}),
    ],
    "javascript-syntax-checker": [
        ({"code": "function f() { return 1; }\n"}, {"ok": True}),
        ({"code": "function f( { return 1; }\n"}, {"ok": False}),
    ],
    "c-brace-balance-checker": [
        ({"code": "int main() { return (0); }"}, {"ok": True}),
        ({"code": "char *s = \"}\"; int x = (1);"}, {"ok": True}),
        ({"code": "void f() { if (x) { }"}, {"ok": False}),
    ],
    # web
    "html-tag-balance-checker": [
        ({"text": "<div><p>hi</p></div>"}, {"ok": True, "output": []}),
        ({"text": "<div><p>hi</div>"}, {"ok": False}),
        ({"text": "<br><img src='x'>"}, {"ok": True, "output": []}),
    ],
    "url-extractor": [
        ({"text": "see https://example.com/a, and http://x.io/b."},
         {"ok": True, "output": ["https://example.com/a", "http://x.io/b"]}),
    ],
})


PROBES.update({
    # ---- phase 4: security operations branch (PLAN.md section 15F) --
    "path-traversal-finder": [
        ({"code": "def f(p):\n    return open(p).read()\n"},
         {"ok": False, "output": [2]}),
        ({"code": "def f():\n    return open('fixed.txt').read()\n"},
         {"ok": True, "output": []}),
        ({"code": "p = '../secret'\n"}, {"ok": False, "output": [1]}),
    ],
    "insecure-random-finder": [
        ({"code": "import random\ndef make_token():\n"
                  "    return str(random.randint(0, 9999))\n"},
         {"ok": False, "output": [3]}),
        ({"code": "import random\ndef pick(xs):\n"
                  "    return random.choice(xs)\n"},
         {"ok": True, "output": []}),
    ],
    "unsafe-yaml-load-finder": [
        ({"code": "import yaml\ndata = yaml.load(open('x'))\n"},
         {"ok": False, "output": [2]}),
        ({"code": "import yaml\n"
                  "data = yaml.load(open('x'), Loader=yaml.SafeLoader)\n"},
         {"ok": True, "output": []}),
    ],
    "tls-verify-off-finder": [
        ({"code": "import requests\nrequests.get('https://x', verify=False)\n"},
         {"ok": False, "output": [2]}),
        ({"code": "import requests\nrequests.get('https://x', verify=True)\n"},
         {"ok": True, "output": []}),
    ],
    "ssrf-finder": [
        ({"code": "import requests\ndef f(url):\n"
                  "    return requests.get(url)\n"},
         {"ok": False, "output": [3]}),
        ({"code": "import requests\n"
                  "requests.get('https://api.example.com')\n"},
         {"ok": True, "output": []}),
    ],
    "known-bad-version-finder": [
        ({"text": "requests==2.19.1\nflask==2.0.0\n"},
         {"ok": False, "output": [{"name": "requests",
                                   "version": "2.19.1", "line": 1}]}),
        ({"text": "requests==2.32.0\n"}, {"ok": True, "output": []}),
    ],
    "typosquat-suspect-finder": [
        ({"text": "request==1.0\n"},
         {"ok": False, "output": [{"name": "request", "line": 1,
                                   "resembles": "requests"}]}),
        ({"text": "requests==2.32.0\n"}, {"ok": True, "output": []}),
    ],
    "setup-exec-finder": [
        ({"code": "import os\nos.system('curl x | sh')\n"},
         {"ok": False, "output": [2]}),
        ({"code": "from setuptools import setup\nsetup(name='x')\n"},
         {"ok": True, "output": []}),
    ],
    "debug-true-finder": [
        ({"text": "DEBUG = True\n"}, {"ok": False, "output": [1]}),
        ({"text": "DEBUG = False\n"}, {"ok": True, "output": []}),
    ],
    "wildcard-bind-finder": [
        ({"text": "host = '0.0.0.0'\n"}, {"ok": False, "output": [1]}),
        ({"text": "host = '127.0.0.1'\n"}, {"ok": True, "output": []}),
    ],
    "chmod-777-finder": [
        ({"text": "#!/bin/sh\nchmod 777 /tmp/x\n"},
         {"ok": False, "output": [2]}),
        ({"text": "chmod 755 /tmp/x\n"}, {"ok": True, "output": []}),
    ],
    "docker-root-finder": [
        ({"text": "FROM python:3\nRUN pip install x\n"},
         {"ok": False, "output": ["root"]}),
        ({"text": "FROM python:3\nUSER app\n"},
         {"ok": True, "output": []}),
    ],
    "env-secret-finder": [
        ({"text": "API_KEY=sk-live-9f2abc\nDEBUG=1\n"},
         {"ok": False, "output": [{"name": "API_KEY", "line": 1}]}),
        ({"text": "API_KEY=changeme\n"}, {"ok": True, "output": []}),
    ],
    "tcp-listener-parser": [
        ({"text": "  sl  local_address rem_address   st\n"
                  "   0: 0100007F:0016 00000000:0000 0A 00000000:00000000\n"
                  "   1: 00000000:1F90 00000000:0000 0A 00000000:00000000\n"
                  "   2: 0100007F:0035 0100007F:9999 01 00000000:00000000\n"},
         {"ok": True, "output": [{"port": 22, "bind": "127.0.0.1"},
                                 {"port": 8080, "bind": "0.0.0.0"}]}),
    ],
    "listening-port-lister": [
        ({}, {"ok": True}),
    ],
    "service-name-mapper": [
        ({"port": 22}, {"ok": True, "output": "ssh"}),
        ({"port": 54321}, {"ok": True, "output": "unknown"}),
    ],
    "external-bind-checker": [
        ({"listeners": [{"port": 22, "bind": "127.0.0.1"},
                        {"port": 8080, "bind": "0.0.0.0"}]},
         {"ok": False, "output": [{"port": 8080, "bind": "0.0.0.0"}]}),
        ({"listeners": [{"port": 22, "bind": "127.0.0.1"}]},
         {"ok": True, "output": []}),
    ],
    "aws-key-finder": [
        ({"text": "key = \"AKIAIOSFODNN7EXAMPLE\"\n"},
         {"ok": False, "output": [{"line": 1, "kind": "aws-access-key"}]}),
        ({"text": "nothing here\n"}, {"ok": True, "output": []}),
    ],
    "private-key-finder": [
        ({"text": "-----BEGIN RSA PRIVATE KEY-----\n"},
         {"ok": False, "output": [{"line": 1, "kind": "private-key"}]}),
        ({"text": "-----BEGIN CERTIFICATE-----\n"},
         {"ok": True, "output": []}),
    ],
    "workspace-secret-scanner": [
        ({"files": {"a.py": "x = 1\nprint(x)\n",
                    "b.py": "aws = \"AKIAIOSFODNN7EXAMPLE\"\n"}},
         {"ok": False, "output": [{"file": "b.py", "line": 1,
                                   "kind": "aws-access-key"}]}),
        ({"files": {"a.py": "x = 1\n"}}, {"ok": True, "output": []}),
    ],
})


# ------------------------------------------------------------- runner
def run_probes(reg):
    """Run every probe against the built registry.

    Returns (verified_names, failures) where failures is a list of
    {"specialist", "task", "expected", "got"} for every mismatch.
    """
    verified, failures = [], []
    for name, probes in PROBES.items():
        spec = reg.get(name)
        if spec is None:
            failures.append({"specialist": name, "task": None,
                             "expected": "registered", "got": "missing"})
            continue
        bad = []
        for task, expected in probes:
            got = spec.run(task)
            if any(got.get(k) != v for k, v in expected.items()):
                bad.append({"specialist": name, "task": task,
                            "expected": expected,
                            "got": {k: got.get(k) for k in expected}})
        if bad:
            failures.extend(bad)
        else:
            verified.append(name)
    return verified, failures


def main():
    from .board import Board
    from .niches import build_swarm

    board = Board()
    reg = build_swarm(board)
    verified, failures = run_probes(reg)
    for name in verified:
        reg.get(name).dev_status = "running-alone"
    probed = set(PROBES)
    constructed = [s.name for s in reg.all() if s.kind == "constructed"]
    unprobed = sorted(n for n in constructed if n not in probed)
    by_niche = {}
    for name in verified:
        by_niche.setdefault(reg.get(name).niche, []).append(name)
    print(f"== phase-2 coverage probes: {len(verified)}/{len(PROBES)} "
          f"specialists verified running-alone")
    for niche in sorted(by_niche):
        print(f"  {niche:<14} {len(by_niche[niche]):>2} verified")
    if unprobed:
        print(f"  (constructed without phase-2 probes — phase-1 demo "
              f"verifies its own: {len(unprobed)})")
    for f in failures:
        print(f"  FAIL {f['specialist']}: task={f['task']!r} "
              f"expected={f['expected']} got={f['got']}")
    print("COVERAGE OK" if not failures else "COVERAGE FAILURES ABOVE")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
