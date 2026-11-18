"""Private CPU inference for the rule lab. The server and its adapter cache belong to this run."""
import os
import socket
import subprocess
import time
import urllib.error
from contextlib import contextmanager
from pathlib import Path

from team import ternary


class LabCPU:
    def __init__(self, binary, base, catalog, log_dir, slots=2, threads=4, flash=None, control=None):
        self.binary = Path(binary).resolve(strict=True)
        self.base = Path(base).resolve(strict=True)
        self.catalog = Path(catalog).resolve(strict=True)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        if min(slots, threads) < 1:
            raise ValueError("slots and threads must be positive")
        self.slots, self.threads, self.flash = slots, threads, flash
        self.control = control  # optional (GGUF direction, scale, first layer, last layer)
        self.proc = None
        self.resident = []
        self.ids = {}
        self.active = None
        self.starts = 0
        self.peak_kib = 0
        self.repairs = 0

    def sample_memory(self):
        if self.proc and self.proc.poll() is None:
            for line in Path(f"/proc/{self.proc.pid}/status").read_text().splitlines():
                if line.startswith("VmHWM:"):
                    self.peak_kib = max(self.peak_kib, int(line.split()[1]))

    def close(self):
        if self.proc:
            if self.proc.poll() is None:
                self.sample_memory()
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
            self.proc = None
        self.resident = []
        self.ids = {}
        self.active = None

    def activate(self, cell):
        path = self.catalog / f"{cell}.gguf"
        if not path.is_file() or path.parent != self.catalog:
            raise ValueError(f"unknown cell {cell}")
        if cell in self.resident:
            self.resident.remove(cell)
            self.resident.append(cell)
        else:
            # The pinned server can switch preloaded edits. A cache miss rebuilds only
            # our private server with the most recently used edits; disk holds the rest.
            wanted = (self.resident + [cell])[-self.slots:]
            self.close()
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            self.url = f"http://127.0.0.1:{port}"
            args = [str(self.binary), "-m", str(self.base), "-t", str(self.threads), "-c", "2048",
                    "-rtr", "--host", "127.0.0.1", "--port", str(port), "--parallel", "1", "--jinja",
                    "--lora-init-without-apply"]
            if self.flash is not None:
                args.extend(["-fa", "on" if self.flash else "off"])
            if self.control is not None:
                path, scale, first, last = self.control
                args.extend(["--control-vector-scaled", str(Path(path).resolve(strict=True)), str(scale),
                             "--control-vector-layer-range", str(first), str(last)])
            for name in wanted:
                args += ["--lora", str(self.catalog / f"{name}.gguf")]
            self.starts += 1
            log = self.log_dir / f"server-{os.getpid()}-{self.starts}.log"
            with log.open("w") as out:
                self.proc = subprocess.Popen(args, stdout=out, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 120
            while self.proc.poll() is None and time.monotonic() < deadline:
                if (ternary._get(self.url + "/health", timeout=1) or {}).get("status") == "ok":
                    break
                time.sleep(0.2)
            else:
                self.close()
                raise RuntimeError(f"private CPU server failed to start; see {log}")
            self.ids = {Path(a["path"]).stem: a["id"] for a in ternary._get(self.url + "/lora-adapters")}
            if set(self.ids) != set(wanted):
                raise RuntimeError(f"server loaded {sorted(self.ids)}, expected {wanted}")
            self.resident = wanted
        if self.active != cell:
            ternary._switch(self.url, [{"id": i, "scale": float(name == cell)} for name, i in self.ids.items()])
            self.active = cell

    def reply(self, cell, messages):
        start = time.monotonic()
        for attempt in range(2):
            try:
                if self.proc and self.proc.poll() is not None:
                    raise ConnectionError("private inference process exited")
                self.activate(cell)
                out = ternary._post(self.url + "/v1/chat/completions", {
                    "messages": messages, "max_tokens": 100, "temperature": 0.0, "seed": 1234,
                    "cache_prompt": False, "response_format": {"type": "json_object"},
                    "chat_template_kwargs": {"enable_thinking": False},
                }, timeout=180)
                break
            except (OSError, ternary.Silent) as exc:
                if attempt or (isinstance(exc, urllib.error.HTTPError) and exc.code < 500):
                    raise
                self.close()
                self.repairs += 1
        self.sample_memory()
        return {"text": out["choices"][0]["message"]["content"], "usage": out.get("usage", {}),
                "seconds": round(time.monotonic() - start, 3), "resident": self.resident.copy()}


@contextmanager
def serving(*args, **kwargs):
    cpu = LabCPU(*args, **kwargs)
    try:
        yield cpu
    finally:
        cpu.close()
