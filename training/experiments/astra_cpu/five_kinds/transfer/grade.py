"""Execute first programs and grade fresh official module contracts without giving expected values to the guest."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import tempfile

from team import solo
from team.deliverables import regular
from team.specialists.coder import extract_code
from team.tools.sandbox import _HOOK_SRC, give
from training import exam, hive_bench, lessons
from training.experiments.fieldwork.guest import Guest
from training.kinds import _programs

HERE = Path(__file__).resolve().parent
PANEL_HASH = "8d3903f5bd41ea2d65973931026069baa297c0009af57471a0cdef8ee9db1945"
FUEL = 5_000_000_000
LIMIT = 1_000_000
RUN = """import sys
sys.path.insert(0, '/hooks')
import sitecustomize
sys.path.insert(0, '.')
sys.argv = ['member1_1.py']
with open(sys.argv[0], encoding='utf-8') as f:
    code = compile(f.read(), sys.argv[0], 'exec')
exec(code, {'__name__': '__main__', '__file__': sys.argv[0]})
"""
CHECK = """import contextlib, importlib.util, json, sys
scenarios=json.load(sys.stdin)
with contextlib.redirect_stdout(sys.stderr):
    spec=importlib.util.spec_from_file_location('m','subject.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results=[]
    for constructor, steps in scenarios:
        try:
            obj=getattr(module,constructor[0])(*constructor[1]) if constructor else module
        except Exception as error:
            results.append({'constructor_error':type(error).__name__})
            continue
        values=[]
        for name, args in steps:
            try:
                values.append(json.loads(json.dumps(getattr(obj,name)(*args))))
            except Exception as error:
                values.append({'raises':type(error).__name__})
        results.append({'values':values})
print(json.dumps(results, allow_nan=False))
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def panel():
    raw = (HERE / "panel.json").read_bytes()
    if sha(raw) != PANEL_HASH:
        raise ValueError("frozen panel changed")
    return json.loads(raw)["rows"]


def run_guest(guest, work, control, boot, inputs, writable):
    w, engine, mod, linker, _ = guest.runtime
    control.mkdir()
    hooks = control / "hooks"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text(_HOOK_SRC)
    stdin, stdout, stderr = [control / k for k in ("in", "out", "err")]
    stdin.write_text(json.dumps(inputs))
    error = None
    with w.Store(engine) as store:
        wasi = w.WasiConfig()
        wasi.argv = ["python", "-B", "-S", "-c", boot]
        wasi.env = [("PYTHONHOME", "/sdk"), ("PYTHONHASHSEED", "19")]
        wasi.preopen_dir(str(guest.sdk / "lib"), "/sdk/lib", w.DirPerms.READ_ONLY, w.FilePerms.READ_ONLY)
        wasi.preopen_dir(str(hooks), "/hooks", w.DirPerms.READ_ONLY, w.FilePerms.READ_ONLY)
        dp = w.DirPerms.READ_WRITE if writable else w.DirPerms.READ_ONLY
        fp = w.FilePerms.READ_WRITE if writable else w.FilePerms.READ_ONLY
        wasi.preopen_dir(str(work), ".", dp, fp)
        wasi.stdin_file, wasi.stdout_file, wasi.stderr_file = str(stdin), str(stdout), str(stderr)
        store.set_wasi(wasi)
        store.set_limits(memory_size=256 * 1024 * 1024)
        store.set_fuel(FUEL)
        try:
            instance = linker.instantiate(store, mod)
            instance.exports(store)["_start"](store)
        except w.ExitTrap as exc:
            if exc.code:
                error = f"CPython exit {exc.code}"
        except w.Trap as exc:
            error = "instruction limit" if not store.get_fuel() else str(exc).splitlines()[0]
        fuel = FUEL - store.get_fuel()
    if stdout.stat().st_size > LIMIT or stderr.stat().st_size > LIMIT:
        error = "output limit"
    def read(path):
        with path.open("rb") as stream:
            return stream.read(LIMIT).decode("utf-8", "replace")
    return {"stdout": read(stdout), "stderr": read(stderr)[-800:], "error": error, "fuel": fuel}


def grade(guest, row, raw):
    name = row["name"] + ".py"
    _, _, task, check = exam.remake(row["maker"], row["seed"], row["level"])
    assert task == row["task"]
    state = inspect.getclosurevars(check).nonlocals
    scenarios = state["draw"]()
    total = sum(len(s["steps"]) for s in scenarios)
    rec = dict(name=row["name"], generated=bool(raw.strip()), file_sha256=None,
               module_source=None, program_exit_ok=False, public_values_ok=False,
               hidden_passed=0, hidden_total=total, full_pass=False)
    if not raw.strip():
        return rec | {"reason": "no generated answer"}
    program = extract_code(raw)
    rec["program_sha256"] = sha(program.encode())
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        work = home / "work"
        work.mkdir()
        give(task, work, skip=solo.wanted(task))
        (work / "member1_1.py").write_text(program)
        first = run_guest(guest, work, home / "first-io", RUN, [], True)
        rec["execution"] = first
        rec["program_exit_ok"] = first["error"] is None
        rec["public_values_ok"] = all(_programs.told(hive_bench._body(first["stdout"]), v) for v in state["asked"])
        if rec["program_exit_ok"]:
            saved = solo.module(task, program, work)
        else:
            saved = ""
        try:
            with regular(work / name) as stream:
                data = stream.read(LIMIT + 1)
        except (OSError, ValueError):
            return rec | {"reason": "requested module absent or unreadable"}
        if len(data) > LIMIT:
            return rec | {"reason": "requested module exceeds size limit"}
        rec.update(file_sha256=sha(data), module_source="stock AST materializer" if saved else "member file")
        # Only public operation names and inputs accompany the candidate module into the fresh read-only guest.
        hidden = home / "hidden"
        hidden.mkdir()
        (hidden / "subject.py").write_bytes(data)
        operations = [(s["new"], [(n, args) for n, args, _ in s["steps"]]) for s in scenarios]
        runs = run_guest(guest, hidden, home / "hidden-io", CHECK, operations, False)
        rec["hidden_fuel"] = runs["fuel"]
        if runs["error"]:
            return rec | {"reason": runs["error"], "hidden_error": runs["stderr"]}
        try:
            answers = json.loads(runs["stdout"])
            if not isinstance(answers, list) or len(answers) != len(scenarios):
                raise ValueError("wrong result count")
            for answer, scenario in zip(answers, scenarios):
                if "constructor_error" in answer:
                    continue
                values, steps = answer["values"], scenario["steps"]
                if not isinstance(values, list) or len(values) != len(steps):
                    raise ValueError("wrong step count")
                rec["hidden_passed"] += sum(v == step[2] for v, step in zip(values, steps))
        except (KeyError, TypeError, ValueError) as e:
            return rec | {"reason": "unreadable module result: " + type(e).__name__}
    rec["full_pass"] = rec["program_exit_ok"] and rec["public_values_ok"] and rec["hidden_passed"] == total
    return rec


def evaluate(sdk, native):
    rows = panel()
    guest = Guest(sdk)
    if native is None:
        controls = []
        for r in rows:
            _, _, task, check = exam.remake(r["maker"], r["seed"], r["level"])
            program = lessons.program_for(task, check)
            assert program
            controls.append(grade(guest, r, "```python\n" + program + "\n```"))
        assert all(x["full_pass"] for x in controls)
        negatives = [grade(guest, rows[0], "print('finished')"),
                     grade(guest, rows[1], "def evaluate(text):\n    return 0\nprint(0)")]
        assert not any(x["full_pass"] for x in negatives)
        assert negatives[0]["file_sha256"] is None and negatives[1]["file_sha256"] is not None
        return {"positive_controls": controls, "negative_controls": negatives}
    if not native.get("complete") or len(native["calls"]) != len(rows):
        raise ValueError("incomplete native panel")
    assert [c["name"] for c in native["calls"]] == [r["name"] for r in rows]
    return {"arm": native["arm"], "graded": [grade(guest, r, c["text"]) for r, c in zip(rows, native["calls"])]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk", type=Path, required=True)
    p.add_argument("--native", type=Path, help="omit for the separate reference-file WASI controls")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    data = evaluate(a.sdk, json.loads(a.native.read_bytes()) if a.native else None)
    data["python_wasm_sha256"] = sha((a.sdk / "python.wasm").read_bytes())
    data["panel_sha256"] = PANEL_HASH
    a.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
