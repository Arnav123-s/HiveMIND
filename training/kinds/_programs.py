"""What the kinds of the family "programs" share (K2c, the h_prog_* kinds): a module the hive writes and saves, put to
hidden tests in a process of its own, and the frame of the lesson's program that writes such a module.

A hidden test is a scenario: an object made from the module (a class and its arguments), or the module itself, and
calls on it one after another, each with the value it must give back ({"raises": "ValueError"}: it must raise that).
The scenarios are drawn from a seed the task never showed and worked out by the kind's own reference code.
"""
import json
import subprocess
import sys
from pathlib import Path

from training import hive_bench as B
from training.kinds._common import _file

_RUN = """import importlib.util, json, sys
spec = importlib.util.spec_from_file_location('m', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
n, bad = 0, []
for sc in json.loads(sys.stdin.read()):
    try:
        obj = getattr(m, sc['new'][0])(*sc['new'][1]) if sc['new'] else m
    except Exception as e:
        n += len(sc['steps']); bad.append([sc['new'], 'made', f'{type(e).__name__}: {e}']); continue
    for name, args, want in sc['steps']:
        n += 1
        try:
            got = json.loads(json.dumps(getattr(obj, name)(*args)))
        except Exception as e:
            got = {'raises': type(e).__name__}
        if got != want:
            bad.append([name, args, want, got])
print(json.dumps([n, len(bad), bad[:1]], default=str))
"""


def raises(name="ValueError"):
    return {"raises": name}


def plain(x):
    """A value as the hidden tests compare it: through JSON (a tuple is a list)."""
    return json.loads(json.dumps(x))


def hidden(path, scenarios, timeout=30):
    """(ok, why): the module at path put to the scenarios [{"new": [cls, args] or None, "steps": [[name, args, want]]}]."""
    try:
        p = subprocess.run([sys.executable, "-I", "-c", _RUN, str(path)], input=json.dumps(scenarios), capture_output=True, text=True,
                           timeout=timeout, cwd=str(Path(path).parent))
        n, bad, first = json.loads(p.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
        return False, f"the hidden tests could not run: {type(e).__name__}"
    return bad == 0, f"{n - bad} of {n} hidden tests pass" + (f"; first failure {str(first[0] if len(first) == 1 else first)[:200]}" if bad else "")


def told(body, want):
    """The answer states the value (as Python or JSON writes it)."""
    return any(s in body for s in {str(want), repr(want), json.dumps(want)})


def module_check(mod, draw, asked):
    """The check of a task that asks for mod.py: the module passes the hidden tests (draw() makes them, from the
    kind's own seed) and the answer states every value asked of it."""
    def check(run, report):
        f = _file(run, f"{mod}.py")
        if not f:
            return False, f"no {mod}.py saved"
        ok, why = hidden(f, draw())
        body = B._body(report)
        said = all(told(body, w) for w in asked)
        return ok and said, f"{why}; the values asked for ({asked}) in the answer: {said}"
    return check


def program(mod, source, tests, prints):
    """The lesson's program: the module's own code, then what runs only when it is run itself (never when imported):
    it saves itself under the module's name, tests itself and prints what the task asks."""
    body = [f"shutil.copy(__file__, {mod + '.py'!r})", *tests, *prints]
    return source.strip() + '\n\n\nif __name__ == "__main__":\n    import shutil\n\n' + "".join(f"    {ln}\n" for ln in body)
