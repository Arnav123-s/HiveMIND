"""Run a fixed, CPU-only comparison of the native ik_llama speculative modes (Linux)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


HERE = Path(__file__).resolve().parent
ARMS = ("ordinary_first", "t4_draft", "t17_draft", "prompt_lookup", "ordinary_last")
HF = {
    "target": ("Ternary-Bonsai-8B-gguf", "Ternary-Bonsai-8B-PQ2_0.gguf", "c2aefbeb4b24469cd11579c3384b990404c17a30",
               "1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922"),
    "t4": ("Ternary-Bonsai-2-4B-gguf", "Ternary-Bonsai-2-4B-PQ2_0.gguf", "50ebba61be85e5be07e8083db468ace0fc1bac43",
           "d406b1e912c0d2a4c124ad10bf38a76ae662fdc4d24b176451403dc7b7f30409"),
    "t17": ("Ternary-Bonsai-1.7B-gguf", "Ternary-Bonsai-1.7B-PQ2_0.gguf", "40e40ecfe50bdfab51628042b1f8f4e97f08acd0",
            "de68ba48a8dacb21979915991e7741b917869d71410a370df951c0c3a237ae50"),
}


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def native_processes():
    found = []
    for path in Path("/proc").glob("[0-9]*/comm"):
        try:
            if path.read_text().strip() == "llama-server" and path.with_name("cmdline").read_bytes():
                found.append(int(path.parent.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return sorted(found)


def cpu_seconds(pid):
    # The first two entries following "(comm)" are fields 3 and 4 in proc_pid_stat(5).
    rest = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return (int(rest[11]) + int(rest[12])) / os.sysconf("SC_CLK_TCK")


def rss_kib(pid):
    values = Path(f"/proc/{pid}/status").read_text()
    return int(re.search(r"VmRSS:\s+(\d+)", values).group(1))


def request(port, route, data=None, timeout=180):
    address = f"http://127.0.0.1:{port}{route}"
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(address, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"HTTP {err.code}: {err.read(1000).decode(errors='replace')}") from err


def completion(proc, port, panel, prompt, max_tokens):
    cpu = cpu_seconds(proc.pid)
    started = time.monotonic()
    reply = request(port, "/v1/chat/completions", {
        "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
        "seed": panel["seed"], "temperature": 0, "top_k": 1, "cache_prompt": False,
        "chat_template_kwargs": {"enable_thinking": False}, "logprobs": True, "top_logprobs": 1,
    })
    wall = time.monotonic() - started
    cpu = cpu_seconds(proc.pid) - cpu
    choice = reply["choices"][0]
    stats = reply["timings"]
    ids = [row["id"] for row in choice.get("logprobs", {}).get("content", ())]
    return {
        "http_wall_s": round(wall, 4), "server_cpu_s": round(cpu, 4), "server_rss_kib": rss_kib(proc.pid),
        "timings": stats, "usage": reply["usage"], "finish_reason": choice["finish_reason"],
        "message": choice["message"], "token_ids": ids,
        "token_trace_complete": bool(ids) and len(ids) == reply["usage"]["completion_tokens"] == stats["predicted_n"],
    }


def test_arm(args, panel, arm, logs):
    port = args.port + ARMS.index(arm)
    with socket.socket() as check:
        check.bind(("127.0.0.1", port))
    flags = ["-m", str(args.target), "-t", "2", "-tb", "2", "-c", "512", "-rtr",
             "--host", "127.0.0.1", "--port", str(port), "--parallel", "1", "--threads-http", "2", "--jinja"]
    if arm in ("t4_draft", "t17_draft"):
        model = args.t4 if arm == "t4_draft" else args.t17
        flags += ["-md", str(model), "-td", "2", "-tbd", "2", "-cd", "512",
                  "--spec-type", "draft:n_max=5,n_min=1,p_min=0.0"]
    if arm == "prompt_lookup":
        flags += ["--spec-type", "ngram-simple:n_max=5,n_min=1,ngram_size_n=3,ngram_size_m=5"]
    models = {str(getattr(args, key)): f"<{key}>" for key in HF}
    rec = {"arm": arm, "flags": [models.get(flag, flag) for flag in flags], "cases": [],
           "other_native_pids_at_launch": native_processes(), "started_utc": datetime.now(timezone.utc).isoformat()}
    logfile = logs / f"{arm}.log"
    start = time.monotonic()
    with logfile.open("wb") as log:
        proc = subprocess.Popen([str(args.binary), *flags], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                cwd=logs.resolve())
        try:
            while True:
                if proc.poll() is not None:
                    raise RuntimeError(f"native server exited with code {proc.returncode}")
                try:
                    if request(port, "/health", timeout=2).get("status") == "ok":
                        break
                except (OSError, RuntimeError):
                    pass
                if time.monotonic() - start > 120:
                    raise TimeoutError("server did not become ready within 120 seconds")
                time.sleep(0.2)
            rec["ready_s"] = round(time.monotonic() - start, 4)
            rec["warmup"] = completion(proc, port, panel, panel["warmup"], 2)
            for case in panel["cases"]:
                print(arm, case["id"], flush=True)
                data = completion(proc, port, panel, case["prompt"], panel["max_tokens"])
                rec["cases"].append({"id": case["id"], **data})
            rec["status"] = "ok"
        except Exception as err:
            rec.update(status="failed", error=f"{type(err).__name__}: {err}")
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            rec["native_exit_code"] = proc.returncode
    lines = logfile.read_text(errors="replace").splitlines()
    select = r"general.architecture|general.name |tokenizer.ggml.pre |n_vocab\s+=|vocabs|incompatible|do not match|different|segmentation fault|assert|invalid|fatal|error|failed to|speculative decoding|speculative.*using|vocab size"
    rec["native_evidence"] = [line[:400] for line in lines if re.search(select, line, re.I)][:42]
    if rec["status"] != "ok":
        rec["native_error_tail"] = lines[-15:]
    return rec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for model in ("binary", *HF):
        parser.add_argument("--" + model, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--logs", type=Path)
    parser.add_argument("--resume", action="store_true", help="resume after completed, recorded arms")
    parser.add_argument("--port", type=int, default=18493)
    args = parser.parse_args()
    for key in ("binary", *HF):
        setattr(args, key, getattr(args, key).resolve())
    panel = json.loads((HERE / "panel.json").read_text())
    models = {}
    for key, (slug, name, rev, expected) in HF.items():
        path = getattr(args, key)
        actual = sha(path)
        if actual != expected:
            raise ValueError(f"{key} SHA-256 mismatch")
        models[key] = {"hf_repo": "prism-ml/" + slug, "filename": name, "revision": rev,
                       "bytes": path.stat().st_size, "sha256": actual}
    cpu = Path("/proc/cpuinfo").read_text()
    output = {"panel_sha256": sha(HERE / "panel.json"), "protocol_sha256": sha(HERE / "protocol.md"),
              "binary_sha256": sha(args.binary), "models": models,
              "cpu_model": re.search(r"model name\s+: (.*)", cpu).group(1),
              "cpu_cgroup_limit": Path("/sys/fs/cgroup/cpu.max").read_text().strip(), "arms": []}
    if args.resume:
        previous = json.loads(args.output.read_text())
        if any(previous[key] != value for key, value in output.items() if key != "arms"):
            raise ValueError("saved model, binary, protocol, or host metadata differ")
        done = previous["arms"]
        if [row["arm"] for row in done] != list(ARMS[:len(done)]):
            raise ValueError("saved arm order does not match protocol")
        output["arms"] = done
    with tempfile.TemporaryDirectory(prefix="native-decode-") as scratch:
        logs = args.logs or Path(scratch)
        logs.mkdir(exist_ok=True, parents=True)
        for arm in ARMS[len(output['arms']):]:
            print(arm, "starting", flush=True)
            output["arms"].append(test_arm(args, panel, arm, logs))
            args.output.write_text(json.dumps(output, indent=2) + "\n")
            print(arm, output["arms"][-1]["status"], flush=True)


if __name__ == "__main__":
    main()
