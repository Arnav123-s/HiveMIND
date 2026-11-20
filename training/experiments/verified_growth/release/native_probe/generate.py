"""Run one direct frozen native call per blind request and checkpoint the raw reply before any grade."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import os
import socket
import subprocess
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
REQUESTS_SHA = "b6828e21e3ffd77284c600d318bd2de8c4ffbb17e2577069ff7b2a6be739f5ed"
SETTINGS_SHA = "8db4ecc9ca9ce8896ceb1331920b11d91e8e3647496251b4a0713088a1bc8719"


def digest(path):
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def call(address, path, data=None, timeout=120):
    req = Request(address + path, data=None if data is None else json.dumps(data).encode(),
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as err:
        raise OSError(f"HTTP {err.code}: {err.read(1500).decode(errors='replace')}") from err


def process_cpu(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1].split()
    return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")


def memory_guard(proc, stopped, record):
    stats = Path("/sys/fs/cgroup/memory.stat")
    cap = Path("/sys/fs/cgroup/memory.max")
    if not stats.exists() or not cap.exists() or cap.read_text().strip() == "max":
        return
    limit = int(cap.read_text())
    threshold = limit - (2 << 30)
    while not stopped.wait(1) and proc.poll() is None:
        values = dict(line.split() for line in stats.read_text().splitlines())
        private = int(values["anon"]) + int(values.get("kernel", 0))
        if private > threshold:
            record.write_text(json.dumps({"cgroup_non_file_bytes": private, "threshold_bytes": threshold}) + "\n")
            proc.terminate()
            return


def save(path, data):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    temp.replace(path)


@contextmanager
def native(args, settings):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    command = [str(args.runtime), "-m", str(args.model), "-ngl", "0", "-c", str(settings["context"]),
               "-t", str(args.threads), "-tb", str(args.threads), "-rtr", "-b", "128", "-ub", "128", "--parallel", "1", "--threads-http", "2",
               "--host", "127.0.0.1", "--port", str(port), "--jinja"]
    started = time.monotonic()
    with (args.scratch / "server.log").open("wb") as log:
        proc = subprocess.Popen(command, cwd=args.scratch, stdout=log, stderr=log)
        stopped = threading.Event()
        watcher = threading.Thread(target=memory_guard, args=(proc, stopped, args.scratch/"memory-cutoff.json"), daemon=True)
        watcher.start()
        try:
            while time.monotonic() - started < 90:
                if proc.poll() is not None:
                    raise RuntimeError(f"native exited with code {proc.returncode}")
                try:
                    if call(address, "/health", timeout=1).get("status") == "ok":
                        break
                except OSError:
                    pass
                time.sleep(0.25)
            else:
                raise TimeoutError("native startup")
            yield proc, address, time.monotonic() - started
        finally:
            stopped.set()
            watcher.join()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def run(args):
    assert digest(HERE / "settings.json") == SETTINGS_SHA and digest(HERE / "requests.json") == REQUESTS_SHA
    settings = json.loads((HERE / "settings.json").read_bytes())
    requests = json.loads((HERE / "requests.json").read_bytes())
    assert digest(args.runtime) == settings["runtime_sha256"]
    assert digest(args.model) == settings["model_sha256"]
    args.scratch.mkdir(parents=True, exist_ok=False)
    if args.out.exists():
        raise FileExistsError(args.out)
    earlier = None
    prior_calls = []
    if args.resume_transport:
        earlier = json.loads(args.resume_transport.read_bytes())
        assert earlier["settings_sha256"] == SETTINGS_SHA and earlier["requests_sha256"] == REQUESTS_SHA
        assert earlier["model_sha256"] == settings["model_sha256"]
        prior_calls = [r for r in earlier["calls"] if r["state"] == "returned"]
    returned_ids = {r["id"] for r in prior_calls}
    record = {"settings_sha256": SETTINGS_SHA, "requests_sha256": REQUESTS_SHA,
              "runtime_sha256": settings["runtime_sha256"], "model_sha256": settings["model_sha256"],
              "threads": args.threads, "affinity": sorted(os.sched_getaffinity(0)),
              "start_utc": datetime.now(timezone.utc).isoformat(), "calls": list(prior_calls),
              "prior_transport_sha256": digest(args.resume_transport) if earlier else None,
              "prior_returned_retained": len(prior_calls), "runtime_repack": True, "batch": 128}
    with native(args, settings) as (proc, address, startup_s):
        record["startup_s"] = round(startup_s, 4)
        save(args.out, record)
        for case in requests:
            if case["id"] in returned_ids:
                continue
            message = {"messages": [{"role": "system", "content": settings["system"]},
                                    {"role": "user", "content": case["task"]}],
                       "max_tokens": settings["max_tokens"], "temperature": 0, "top_k": 1, "cache_prompt": False,
                       "seed": settings["seed"], "chat_template_kwargs": {"enable_thinking": False}}
            row = {"id": case["id"], "state": "started"}
            record["calls"].append(row)
            save(args.out, record)
            start, cpu = time.monotonic(), process_cpu(proc.pid)
            try:
                reply = call(address, "/v1/chat/completions", message, timeout=600)
                choice = reply["choices"][0]
                row.update(state="returned", raw=choice["message"].get("content") or "",
                           finish_reason=choice["finish_reason"], usage=reply["usage"], timings=reply.get("timings"),
                           system_fingerprint=reply.get("system_fingerprint"))
            except (OSError, ValueError, KeyError, IndexError) as err:
                row.update(state="infrastructure_failure", error=f"{type(err).__name__}: {err}", raw="")
            finally:
                row["wall_s"] = round(time.monotonic() - start, 4)
                row["server_cpu_s"] = round(process_cpu(proc.pid) - cpu, 4) if proc.poll() is None else None
                save(args.out, record)
            print(len(record["calls"]), case["id"], row["state"], row.get("finish_reason"),
                  (row.get("usage") or {}).get("completion_tokens"), row["wall_s"], flush=True)
            if proc.poll() is not None:
                break
    record["end_utc"] = datetime.now(timezone.utc).isoformat()
    record["native_log_sha256"] = digest(args.scratch / "server.log")
    save(args.out, record)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--threads", type=int, choices=(1, 2), default=2)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--resume-transport", type=Path, help="retain every completed answer from interrupted transport")
    run(p.parse_args())
