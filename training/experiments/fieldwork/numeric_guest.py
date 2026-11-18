"""Optional Linux CPU guest for experiments that explicitly permit NumPy."""

import contextlib
import ctypes
import errno
import inspect
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def confine():
    # Imported numerical code works on in-memory arrays. Only the two result streams survive as open fds.
    lib = ctypes.CDLL("libseccomp.so.2")
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    filt = lib.seccomp_init(0x00050000 | errno.EPERM)
    if not filt:
        raise RuntimeError("failed to create syscall filter")
    try:
        allowed = (
            "write writev close fstat brk mmap mremap munmap mprotect madvise "
            "rt_sigaction rt_sigprocmask rt_sigreturn sigaltstack futex clock_gettime gettimeofday "
            "getrusage getpid gettid sched_getaffinity getrandom exit exit_group"
        )
        for name in allowed.split():
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and lib.seccomp_rule_add(filt, 0x7FFF0000, number, 0) != 0:
                raise RuntimeError("failed to add numerical guest rule")
        if lib.seccomp_load(filt) != 0:
            raise RuntimeError("could not restrict numerical guest")
    finally:
        lib.seccomp_release(filt)


def child():
    import importlib
    import numpy as np

    for name in (
        "bisect",
        "collections",
        "csv",
        "datetime",
        "decimal",
        "fractions",
        "functools",
        "heapq",
        "itertools",
        "math",
        "operator",
        "random",
        "re",
        "statistics",
        "string",
        "typing",
        "io",
    ):
        importlib.import_module(name)
    np.linalg.lstsq(np.array([[1.0], [2.0]]), np.array([2.0, 4.0]), rcond=None)
    np.linalg.svd(np.eye(2), compute_uv=False)
    np.random.default_rng(1).integers(0, 5)
    data = json.load(sys.stdin)
    limit = data["limit"]
    resource.setrlimit(resource.RLIMIT_CPU, (limit, limit + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (12_000_000, 12_000_000))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    os.close(0)
    os.closerange(3, 4096)
    confine()
    scope = {}
    exec(data["tool"], scope)
    result = []

    class Quiet:
        def write(self, value):
            return len(value)

        def flush(self):
            pass

    with contextlib.redirect_stdout(Quiet()), contextlib.redirect_stderr(Quiet()):
        try:
            exec(data["source"], scope)
            for x in data["inputs"]:
                try:
                    val = scope["solve"](x)
                    result.append({"value": json.loads(json.dumps(val, allow_nan=False))})
                except Exception as exc:
                    result.append({"error": type(exc).__name__ + ": " + str(exc)[:220]})
        except Exception as exc:
            result = [{"error": type(exc).__name__ + ": " + str(exc)[:220]} for _ in data["inputs"]]
    print(json.dumps(result, allow_nan=False, separators=(",", ":")))


class NumericGuest:
    def __init__(self):
        from .guest import least_squares

        self.tool = inspect.getsource(least_squares)

    def run(self, program, inputs, fuel=8_000_000_000):
        if not inputs:
            return [], 0, 0
        limit = min(18, 3 + int(fuel // 3_000_000_000))
        payload = json.dumps(dict(source=program, inputs=inputs, tool=self.tool, limit=limit)).encode()
        start = time.monotonic()
        env = {"OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "LC_ALL": "C"}
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            try:
                with (dest / "stdout").open("wb") as out, (dest / "stderr").open("wb") as err:
                    proc = subprocess.run(
                        [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child"],
                        input=payload,
                        cwd=tmp,
                        env=env,
                        stdout=out,
                        stderr=err,
                        timeout=120,
                        close_fds=True,
                    )
                if proc.returncode != 0:
                    raise ValueError(
                        "numerical guest exit "
                        + str(proc.returncode)
                        + " "
                        + (dest / "stderr").read_text()[-160:]
                    )
                result = json.loads((dest / "stdout").read_text())
                if len(result) != len(inputs):
                    raise ValueError("wrong result count")
            except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                result = [{"error": str(exc)[:240]} for _ in inputs]
        return result, 0, time.monotonic() - start


if __name__ == "__main__" and sys.argv[1:] == ["--child"]:
    child()
