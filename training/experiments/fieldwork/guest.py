"""Run a candidate in CPU WebAssembly with only its inputs and a read-only Python standard library."""

import json
import tempfile
import time
from functools import cached_property
from pathlib import Path


def least_squares(X, y):
    """Small dense least-squares tool shared unchanged by all contenders."""
    X = [list(map(float, row)) for row in X]
    if not X or len(X) != len(y) or not 0 < len(X[0]) <= 40:
        raise ValueError("expected 1 to 40 features and one response per row")
    k = len(X[0])
    matrix = [
        [sum(r[i] * r[j] for r in X) + (1e-8 if i == j else 0) for j in range(k)]
        + [sum(r[i] * v for r, v in zip(X, y))]
        for i in range(k)
    ]
    for i in range(k):
        pivot = max(range(i, k), key=lambda j: abs(matrix[j][i]))
        matrix[i], matrix[pivot] = matrix[pivot], matrix[i]
        scale = matrix[i][i]
        if not scale:
            raise ValueError("singular design")
        matrix[i] = [v / scale for v in matrix[i]]
        for j in range(k):
            if j != i:
                factor = matrix[j][i]
                matrix[j] = [v - factor * b for v, b in zip(matrix[j], matrix[i])]
    return [row[-1] for row in matrix]


BOOT = """
import contextlib, io, json, sys
data = json.load(sys.stdin)
scope = {"least_squares": least_squares}
results = []
class Quiet:
    def write(self, value): return len(value)
    def flush(self): pass
with contextlib.redirect_stdout(Quiet()), contextlib.redirect_stderr(Quiet()):
    try:
        exec(data["program"], scope)
        for sample in data["inputs"]:
            try:
                result = scope["solve"](sample)
                results.append({"value": json.loads(json.dumps(result, allow_nan=False))})
            except Exception as exc:
                results.append({"error": type(exc).__name__ + ": " + str(exc)[:220]})
    except Exception as exc:
        results = [{"error": type(exc).__name__ + ": " + str(exc)[:220]} for _ in data["inputs"]]
print(json.dumps(results, allow_nan=False, separators=(",",":")))
"""


class Guest:
    def __init__(self, sdk):
        self.sdk = Path(sdk).resolve(strict=True)

    @cached_property
    def runtime(self):
        import inspect
        import wasmtime as w

        config = w.Config()
        config.consume_fuel = True
        engine = w.Engine(config)
        module = w.Module.from_file(engine, self.sdk / "python.wasm")
        linker = w.Linker(engine)
        linker.define_wasi()
        return w, engine, module, linker, inspect.getsource(least_squares) + BOOT

    def run(self, program, inputs, fuel=5_000_000_000):
        if not inputs:
            return [], 0, 0
        w, engine, module, linker, boot = self.runtime
        start = time.monotonic()
        with tempfile.TemporaryDirectory() as tmp, w.Store(engine) as store:
            tmp = Path(tmp)
            stdin, stdout, stderr = (tmp / name for name in ("inputs", "stdout", "stderr"))
            stdin.write_text(json.dumps({"program": program, "inputs": inputs}, allow_nan=False))
            wasi = w.WasiConfig()
            wasi.argv = ["python", "-B", "-S", "-c", boot]
            wasi.env = [("PYTHONHOME", "/sdk"), ("PYTHONHASHSEED", "19")]
            wasi.preopen_dir(str(self.sdk / "lib"), "/sdk/lib", w.DirPerms.READ_ONLY, w.FilePerms.READ_ONLY)
            wasi.stdin_file, wasi.stdout_file, wasi.stderr_file = str(stdin), str(stdout), str(stderr)
            store.set_wasi(wasi)
            store.set_limits(memory_size=256 * 1024 * 1024)
            store.set_fuel(fuel)
            try:
                instance = linker.instantiate(store, module)
                instance.exports(store)["_start"](store)
            except w.ExitTrap as exc:
                if exc.code != 0:
                    result = [
                        {"error": "Python guest exit " + str(exc.code) + " " + stderr.read_text()[-240:]}
                        for _ in inputs
                    ]
                else:
                    result = None
            except w.Trap as exc:
                result = [
                    {
                        "error": "WASM instruction limit"
                        if store.get_fuel() == 0
                        else str(exc).splitlines()[0]
                    }
                    for _ in inputs
                ]
            else:
                result = None
            if result is None:
                try:
                    with stdout.open() as output:
                        result = json.loads(output.read(12_000_000))
                    if not isinstance(result, list) or len(result) != len(inputs):
                        raise ValueError("wrong result count")
                except (OSError, ValueError):
                    result = [{"error": "guest returned unreadable output"} for _ in inputs]
            used = fuel - store.get_fuel()
        return result, used, time.monotonic() - start
