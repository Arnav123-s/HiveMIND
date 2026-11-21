"""Run every frozen prompt against one isolated CPU server; keep all generated programs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import Request, urlopen

from training import hint_dream
from training.experiments.fieldwork.guest import Guest

PANELS = {
    "initial": ("spade-development-20261120", (0, 1, 2, 3, 4, 5)),
    "confirmation": ("spade-format-confirmation-20261121", (1, 2, 8, 11, 6)),
    "transfer": ("spade-after-sft-20261121", (0, 9, 10)),
}
ASSETS = {"server": "0dc642d61dc39d51a8b5da348c43ba19d29f720b2a3ac790e0019351239da3b2",
          "model": "1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922",
          "adapter": "72913f1c566638f2177574178f1d6925cde956a92b35af06795e7598c5729036"}


def call(url, data=None):
    req = Request(url, data=None if data is None else json.dumps(data).encode(), headers={"Content-Type":"application/json"})
    with urlopen(req, timeout=300) as res:
        return json.load(res)


def save(path, obj):
    tmp = path.with_suffix(".pending")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(path)


def run(args):
    seed, indexes = PANELS[args.panel]
    specs = list(hint_dream.draw(seed, max(indexes) + 1))
    expected_assets = dict(ASSETS)
    if args.candidate_sha:
        if args.panel != "transfer":
            raise ValueError("A candidate can only sit the blind transfer panel")
        expected_assets["adapter"] = args.candidate_sha
    for name, expected in expected_assets.items():
        with getattr(args, name).open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != expected:
                raise ValueError(f"Unexpected {name}")
    args.out.mkdir()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    flags = ["-ngl", "0", "-c", "2048", "-t", "2", "-tb", "2", "-rtr", "-b", "128", "-ub", "128",
             "--parallel", "1", "--threads-http", "2", "--host", "127.0.0.1", "--port", str(port), "--jinja"]
    sampling = {"temperature":0, "max_tokens":hint_dream.TOKENS, "top_k":0, "top_p":1, "cache_prompt":False,
                "seed":8103, "chat_template_kwargs":{"enable_thinking":False}}
    rec = {"complete":False, "assets":expected_assets, "affinity":sorted(os.sched_getaffinity(0)), "flags":flags,
           "sampling":sampling, "seed":seed, "panel":args.panel, "pairs":[], "calls":[]}
    guest = Guest(args.sdk)
    with (args.out / "server.log").open("wb") as log:
        proc = subprocess.Popen([str(args.server), "-m", str(args.model), "--lora", str(args.adapter), *flags],
                                stdout=log, stderr=log)
        try:
            until = time.monotonic() + 120
            while time.monotonic() < until:
                if proc.poll() is not None:
                    raise RuntimeError("server startup failed")
                try:
                    if call(url+"/health").get("status") == "ok":
                        break
                except OSError:
                    pass
                time.sleep(.25)
            else:
                raise TimeoutError("startup")
            weights = call(url+"/lora-adapters")
            if len(weights) != 1 or Path(weights[0]["path"]).name != args.adapter.name or weights[0]["scale"] != 1:
                raise RuntimeError("wrong active LoRA")
            rec["weights"] = weights
            def ask(member, messages, **_):
                start = time.monotonic()
                data = call(url+"/v1/chat/completions", dict(sampling,messages=messages))
                choice = data["choices"][0]
                raw = choice["message"].get("content") or ""
                rec["calls"].append({"messages":messages, "raw":raw, "stop":choice["finish_reason"], "usage":data["usage"],
                                     "seconds":round(time.monotonic()-start,3)})
                save(args.out/"results.json", rec)
                return raw
            for index in indexes:
                spec = specs[index]
                member = "t80+f4hintdream" if args.candidate_sha else "t80+g55trunk"
                if args.panel == "transfer":
                    prompt, _ = hint_dream.instructions(spec)
                    raw = ask(member, hint_dream.messages(prompt))
                    grade, _ = hint_dream.grade(raw, spec, guest)
                    row = None
                    report = {"spec":spec.seed, "kind":spec.kind, "arm":"B" if args.candidate_sha else "A", "blind":grade}
                else:
                    row, report = hint_dream.trial(spec, member, ask, guest, all_pairs=True,
                                                  format_hint=args.panel == "confirmation")
                report["admitted"] = bool(row)
                rec["pairs"].append(report)
                if row:
                    with (args.out/"rows.jsonl").open("a") as f:
                        f.write(json.dumps(row)+"\n")
                save(args.out/"results.json", rec)
                print(report, flush=True)
            rec["complete"] = True
            save(args.out/"results.json", rec)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--panel", choices=tuple(PANELS), default="initial")
    p.add_argument("--candidate-sha", default="", help="SHA-256 of a trained comparison adapter on the blind transfer panel")
    for name in (*ASSETS, "sdk", "out"):
        p.add_argument("--"+name, type=Path, required=True)
    run(p.parse_args())
