"""Grade sealed first-program outputs with CPython WASI and the frozen panel grader."""
import argparse
import ast
import hashlib
import json
import tempfile
from pathlib import Path

from team.deliverables import regular, wanted
from team.specialists.coder import extract_code
from team.tools.sandbox import _HOOK_SRC, give
from training.experiments.astra_orders import panel
from training.experiments.fieldwork.guest import Guest

LIMIT = 1_000_000
BOOT = """import sys
sys.path.insert(0, '/hooks')
import sitecustomize
sys.path.insert(0, '.')
sys.argv = ['main.py']
with open('main.py', encoding='utf-8') as f:
    code = compile(f.read(), 'main.py', 'exec')
exec(code, {'__name__': '__main__', '__file__': 'main.py'})
"""


def execute(guest, folder, program, control, fuel=5_000_000_000):
    """Fresh store. Only the task folder is writable; stdout and hooks live outside it."""
    w, engine, module, linker, _ = guest.runtime
    hooks = control / "hooks"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text(_HOOK_SRC)
    (folder / "main.py").write_text(program)
    stdout, stderr = control / "stdout", control / "stderr"
    with w.Store(engine) as store:
        wasi = w.WasiConfig()
        wasi.argv = ["python", "-B", "-S", "-c", BOOT]
        wasi.env = [("PYTHONHOME", "/sdk"), ("PYTHONHASHSEED", "19")]
        wasi.preopen_dir(str(guest.sdk / "lib"), "/sdk/lib", w.DirPerms.READ_ONLY, w.FilePerms.READ_ONLY)
        wasi.preopen_dir(str(hooks), "/hooks", w.DirPerms.READ_ONLY, w.FilePerms.READ_ONLY)
        wasi.preopen_dir(str(folder), ".", w.DirPerms.READ_WRITE, w.FilePerms.READ_WRITE)
        wasi.stdout_file, wasi.stderr_file = str(stdout), str(stderr)
        store.set_wasi(wasi)
        store.set_limits(memory_size=256 * 1024 * 1024)
        store.set_fuel(fuel)
        error = ""
        try:
            instance = linker.instantiate(store, module)
            instance.exports(store)["_start"](store)
        except w.ExitTrap as exc:
            if exc.code:
                error = f"guest exit {exc.code}"
        except w.Trap as exc:
            error = "instruction limit" if store.get_fuel() == 0 else str(exc).splitlines()[0]
        used = fuel - store.get_fuel()
    def read(path):
        with path.open("rb") as f:
            return f.read(LIMIT).decode("utf-8", "replace")
    if max(stdout.stat().st_size, stderr.stat().st_size) > LIMIT:
        error = "output limit"
    return dict(stdout=read(stdout), stderr=read(stderr), error=error, fuel=used)


def score(guest, row, call):
    if call.get("error") or not isinstance(call.get("raw"), str):
        return dict(ok=False, status="inference_error", reason=str(call.get("error") or "missing text"))
    source = extract_code(call["raw"])
    try:
        if not source:
            raise SyntaxError("empty response")
        ast.parse(source)
    except SyntaxError as exc:
        return dict(ok=False, status="syntax", reason=str(exc), finish_reason=call.get("finish_reason"))
    with tempfile.TemporaryDirectory() as tmp:
        control = Path(tmp)
        work = control / "work"
        work.mkdir()
        names = wanted(row["task"])
        give(row["task"], work, skip=names)
        run = execute(guest, work, source, control)
        artifacts = {}
        for name in names:
            path = work / name
            try:
                with regular(path) as f:
                    data = f.read(LIMIT + 1)
                if len(data) > LIMIT:
                    raise ValueError("artifact too large")
                artifacts[name] = hashlib.sha256(data).hexdigest()
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as exc:
                run["error"] = f"invalid requested file: {exc}"
        if run["error"]:
            return dict(ok=False, status="runtime", reason=run["error"], **run, files=artifacts)
        ok, reason = panel.grade(row, run["stdout"], work)
        return dict(ok=ok, status="passed" if ok else "incorrect", reason=reason, **run, files=artifacts)


def evaluate(guest, panel_rows, prepared, native):
    calls = {(c["id"], c["arm"]): c for c in native["calls"]}
    if len(calls) != len(native["calls"]):
        raise ValueError("duplicate native call")
    fields = {r["id"]: r for r in prepared["rows"]}
    needed = {(r["id"], arm) for r in panel_rows for arm in
              (("short", "full", "scaffold") if fields[r["id"]]["scaffold"] else ("short", "full"))}
    if set(calls) != needed:
        raise ValueError("native calls missing or outside frozen panel")
    results = []
    for row in panel_rows:
        arms = {arm: score(guest, row, calls[(row["id"], arm)]) for arm in ("short", "full")}
        if fields[row["id"]]["scaffold"]:
            arms["scaffold"] = score(guest, row, calls[(row["id"], "scaffold")])
        else:
            arms["scaffold"] = dict(arms["short"], reused="short")
        results.append(dict(id=row["id"], group=row["group"], arms=arms))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for opt in ("sdk", "panel", "inputs", "native", "out"):
        parser.add_argument("--" + opt, type=Path, required=True)
    args = parser.parse_args()
    inputs = [json.loads(p.read_text()) for p in (args.panel, args.inputs, args.native)]
    results = evaluate(Guest(args.sdk), *inputs)
    args.out.write_text(panel.serialize(dict(results=results, native_sha256=hashlib.sha256(args.native.read_bytes()).hexdigest())))
