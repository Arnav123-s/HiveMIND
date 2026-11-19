"""Replay one-token adapter switches against either the old or corrected checkout on a private loopback port."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
STARTERS = HERE.parents[1] / "domain-engrams"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--conversation", type=Path, required=True)
    p.add_argument("--water-a", type=Path)
    p.add_argument("--water-b", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if bool(a.water_a) != bool(a.water_b):
        p.error("supply both water revisions or neither")
    sys.path.insert(0, str(a.checkout.resolve()))
    from team import ternary
    os.environ.update(HIVE_TERNARY_BIN=str(a.runtime.resolve()), AGENT_TEAM_THREADS="1")
    exercises = json.loads((STARTERS / "exercises.json").read_text())
    system = (STARTERS / "system.txt").read_text()
    roots = {"conversation": a.conversation}
    panels = [("conversation", 1, ["", "conversation", ""])]
    if a.water_a:
        roots.update(water_a=a.water_a, water_b=a.water_b)
        panels.insert(0, ("physics", 0, ["", "water_a", "water_b", "water_a"]))
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        ternary.ADAPTERS = scratch / "cells"
        ternary.ADAPTERS.mkdir()
        for name, path in roots.items():
            shutil.copyfile(path, ternary.ADAPTERS / f"t80+{name}.gguf")
        ternary.HOME = scratch / "server"
        ternary.ENGRAMS = scratch / "no-other-engrams"
        ternary.weights = lambda base: str(a.model.resolve(strict=True))
        ternary.CTX = 512
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            port = available.getsockname()[1]
        ternary.port = lambda member: port
        cases = []
        try:
            at = ternary.up("t80")
            pid = ternary._PROC[port].pid
            args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            def messages_for(domain, index):
                exercise = exercises[domain]
                prompt = exercise["instruction"] + " " + exercise["check"][index][0]
                return [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
            # Normal clients clear the prompt cache when the active adapter changes.
            for seat in ("", "conversation", ""):
                content = ternary.chat("t80", messages_for("conversation", 1), 1, 0.0, also=(seat,) if seat else ())
                cases.append(dict(api="chat", case="conversation", requested=seat, output=content,
                                  scales=ternary._loaded(at, scales=True)))
            for domain, index, seats in panels:
                messages = messages_for(domain, index)
                text = ternary._post(at+"/apply-template", dict(messages=messages, chat_template_kwargs={"enable_thinking":False}))["prompt"]
                tokens = ternary._post(at+"/tokenize", dict(content=text, add_special=False, parse_special=True))["tokens"]
                # These output-only heads leave the prefix K/V unchanged. Deliberately reuse the prefix on this arm.
                for i, seat in enumerate(seats):
                    ids = ternary._loaded(at)
                    ternary._switch(at, [{"id": ident, "scale": float(name==seat)} for name, ident in ids.items()])
                    reply = ternary._post(at+"/completion", dict(prompt=tokens, n_predict=1, temperature=0,
                                          seed=741, cache_prompt=i>0, n_probs=3))
                    cases.append(dict(api="completion", case=domain, requested=seat, output=reply["content"],
                                      prompt_tokens=reply["timings"]["prompt_n"], scales=ternary._loaded(at, scales=True)))
            receipt = dict(graph_reuse_disabled=b"--no-graph-reuse" in args, runtime_pin=ternary.PIN,
                           sha256={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in roots.items()},
                           cases=cases)
            a.out.write_text(json.dumps(receipt, indent=2)+"\n")
        finally:
            process = ternary._PROC.get(port)
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
