"""Collect one frozen arm. A fresh single-adapter native process prevents cross-adapter graph reuse."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
EXPECTED_PANEL = "8d3903f5bd41ea2d65973931026069baa297c0009af57471a0cdef8ee9db1945"
EXPECTED_MODEL = "1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922"
EXPECTED_RUNTIME = "0dc642d61dc39d51a8b5da348c43ba19d29f720b2a3ac790e0019351239da3b2"
EXPECTED_PARENT = "b603c9395c82838c28831a491d8fc8b48dd09e8bf26c158573724807bef2b3f4"
SAMPLING = {"temperature": 0.0, "seed": 314159, "top_k": 1, "top_p": 1.0, "max_tokens": 384,
            "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}


def digest(path):
    with path.open("rb") as src:
        return hashlib.file_digest(src, "sha256").hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def request(url, payload=None, timeout=240):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as res:
        return json.load(res)


def save(path, data):
    tmp = path.with_suffix(".pending")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def run(a):
    if a.out.exists():
        raise FileExistsError(a.out)
    if a.arm == "parent" and a.lora_sha != EXPECTED_PARENT:
        raise ValueError("starting blend differs from its frozen digest")
    for path, expected in ((HERE / "panel.json", EXPECTED_PANEL), (a.model, EXPECTED_MODEL),
                           (a.runtime, EXPECTED_RUNTIME), (a.lora, a.lora_sha)):
        if digest(path) != expected:
            raise ValueError(f"asset digest mismatch at {path.name}")
    cases = json.loads((HERE / "panel.json").read_bytes())["rows"]
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    flags = ["-ngl", "0", "-c", "2048", "-t", "2", "-tb", "2", "-rtr", "-b", "128", "-ub", "128",
             "--parallel", "1", "--threads-http", "2", "--host", "127.0.0.1", "--port", str(port), "--jinja"]
    record = {"arm": a.arm, "panel_sha256": EXPECTED_PANEL, "model_sha256": EXPECTED_MODEL,
              "runtime_sha256": EXPECTED_RUNTIME, "lora_sha256": a.lora_sha, "flags": flags, "sampling": SAMPLING,
              "affinity": sorted(os.sched_getaffinity(0)), "started": now(), "complete": False, "calls": []}
    with a.log.open("wb") as log:
        proc = subprocess.Popen([str(a.runtime), "-m", str(a.model), "--lora", str(a.lora), *flags],
                                stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(f"native server exited {proc.returncode}")
                try:
                    if request(url + "/health", timeout=1).get("status") == "ok":
                        break
                except OSError:
                    pass
                time.sleep(.25)
            else:
                raise TimeoutError("native load exceeded 120 seconds")
            weights = request(url + "/lora-adapters")
            if len(weights) != 1 or weights[0]["scale"] != 1 or Path(weights[0]["path"]).resolve() != a.lora.resolve():
                raise RuntimeError(f"unexpected active adapter {weights}")
            record["weight_after_load"] = {"filename": a.lora.name, "scale": weights[0]["scale"]}
            save(a.out, record)
            for r in cases:
                start = time.monotonic()
                answer = request(url + "/v1/chat/completions", {**SAMPLING, "messages": r["messages"]})
                choice = answer["choices"][0]
                record["calls"].append({"name": r["name"], "text": choice["message"].get("content") or "",
                                        "finish_reason": choice["finish_reason"], "usage": answer["usage"],
                                        "wall_seconds": round(time.monotonic() - start, 3)})
                save(a.out, record)
                print(a.arm, r["name"], answer["usage"]["completion_tokens"], flush=True)
            record.update(complete=True, finished=now())
            save(a.out, record)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("runtime", "model", "lora", "out", "log"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--arm", choices=("parent", "five"), required=True)
    p.add_argument("--lora-sha", required=True)
    run(p.parse_args())
