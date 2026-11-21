"""Paired multi-turn runs of two published tasks through solo.member on the G55 trunk."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import socket
import subprocess
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from team import solo
from training import exam, kinds
from training.experiments.astra_orders import generate, panel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "model", "lora", "out", "log"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--familiar-index", type=Path, required=True)
    parser.add_argument("--cutoff-repair", action="store_true", help="run the separate post-trial recovery condition")
    parser.add_argument("--resume-stdout-from", type=Path,
                        help="measure a separate CSV continuation from its frozen first native reply")
    parser.add_argument("--borrow-stdout-budget", action="store_true",
                        help="separate matched follow-up allowing the continuation to spend remaining tokens")
    parser.add_argument("--resume", action="store_true", help="resume a complete prefix after releasing the CPU")
    parser.add_argument("--arms-this-session", type=int, help="checkpoint and release the server after this many arms")
    args = parser.parse_args()
    if args.borrow_stdout_budget and not args.resume_stdout_from:
        parser.error("the extended allowance requires a matched stdout comparison")
    if args.arms_this_session is not None and args.arms_this_session < 1:
        parser.error("--arms-this-session must be positive")
    index_sha = generate.file_hash(args.familiar_index)
    if index_sha != "6379846f333435ea1818a5821822b208f26d28da13a4f3ff4fb69983647418e6":
        raise ValueError("expected the frozen G55 checked task text index")
    if args.out.exists() and not args.resume:
        raise FileExistsError(args.out)
    for name, digest in generate.ASSETS.items():
        if generate.file_hash(getattr(args, name)) != digest:
            raise ValueError(name + " digest mismatch")
    selected = "x_h_edit_0"
    question = exam._made(kinds.get("h_edit").make, "held:h_edit:0")
    cases = [("cold-chain", panel.NOVEL["cold-chain"]), (selected, question[2])]
    prefix = None
    if args.resume_stdout_from:
        if args.cutoff_repair or args.resume:
            parser.error("the matched stdout experiment takes its own fresh output file")
        base_sha = generate.file_hash(args.resume_stdout_from)
        if base_sha != "c402019834f294033dc181249d620cc4342dd59b5c5d05cb79fe2a4decd065e0":
            raise ValueError("expected the frozen original four-arm receipt")
        frozen = json.loads(args.resume_stdout_from.read_bytes())
        prefix = next(row for row in frozen["arms"] if row["id"] == selected and row["inspect"] == "1")
        cases = [cases[1]]
    directives = (1,) if args.cutoff_repair or prefix else (0, 1)
    treatments = [(ident, task, str(enabled)) for ident, task in cases for enabled in directives]
    settings = {"max_tokens": 192, "temperature": 0., "top_p": 1., "top_k": 0, "cache_prompt": False,
                "seed": 8103, "chat_template_kwargs": {"enable_thinking": False}}
    record = {"familiarity_index_sha256": index_sha, "assets": generate.ASSETS, "sampling": settings, "turn_limit": 3,
              "seat": "t80+g55trunk", "affinity": sorted(os.sched_getaffinity(0)), "arms": []}
    if prefix:
        record.update(resume_stdout=True, prefix_source_sha256=base_sha)
        if args.borrow_stdout_budget:
            record["borrow_stdout_budget"] = True
    if args.cutoff_repair:
        record["cutoff_repair"] = True
    if args.resume:
        previous = json.loads(args.out.read_bytes())
        if bool(previous.get("cutoff_repair")) != args.cutoff_repair:
            raise ValueError("the saved repair condition differs")
        if (any(previous.get(k) != value for k, value in record.items() if k not in {"arms", "affinity"})
                or len(previous["affinity"]) != len(record["affinity"])):
            raise ValueError("the saved protocol or reserved CPU count differs")
        completed = [(row["id"], row["inspect"]) for row in previous["arms"]]
        if completed != [(ident, flag) for ident, _, flag in treatments][:len(completed)]:
            raise ValueError("the saved arms are not a complete prefix")
        if previous.get("complete"):
            return
        record = previous
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    flags = ["-ngl", "0", "-c", "2048", "-t", "2", "-tb", "2", "-rtr", "-b", "128", "-ub", "128",
             "--parallel", "1", "--threads-http", "2", "--port", str(port), "--host", "127.0.0.1", "--jinja"]
    if "flags" in record:
        record.setdefault("resumptions", []).append({"first_index": len(record["arms"]), "flags": flags,
                                                     "affinity": sorted(os.sched_getaffinity(0))})
    else:
        record["flags"] = flags
    with args.log.open("wb") as log, ExitStack() as cleanup:
        proc = subprocess.Popen([str(args.runtime), "-m", str(args.model), "--lora", str(args.lora), *flags],
                                stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        cleanup.callback(proc.wait)
        cleanup.callback(proc.terminate)
        startup = time.monotonic()
        while time.monotonic() - startup < 120 and proc.poll() is None:
            try:
                if generate.call(url + "/health", timeout=1)["status"] == "ok":
                    break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError("model startup failed")
        record["adapters"] = generate.call(url + "/lora-adapters")
        assert [a["scale"] for a in record["adapters"]] == [1.]
        remaining = treatments[len(record["arms"]):]
        for ident, task, flag in remaining[:args.arms_this_session]:
            calls = []
            def ask(who, endpoint, cell, path, body, cap):
                assert path == "/v1/chat/completions" and cell == ("g55trunk", ())
                if prefix and not calls:
                    first = prefix["calls"][0]
                    if body["messages"] != prefix["messages"][:2] or cap != first["token_cap"]:
                        raise ValueError("the first request differs from the frozen native control")
                    calls.append(dict(first, origin="frozen native control"))
                    return {"choices": [{"message": {"content": first["response"]},
                                         "finish_reason": first["finish"]}], "usage": first["usage"]}
                start, prev = time.monotonic(), generate.cpu(proc.pid)
                payload = dict(settings, messages=body["messages"], max_tokens=cap)
                reply = generate.call(endpoint + path, payload)
                choice = reply["choices"][0]
                calls.append({"token_cap": cap, "response": choice["message"]["content"], "finish": choice["finish_reason"],
                              "usage": reply["usage"], "wall_s": round(time.monotonic() - start, 3),
                              "cpu_s": round(generate.cpu(proc.pid) - prev, 3)})
                return reply
            with (TemporaryDirectory() as root, patch.dict(os.environ, {"HIVE_ASSERT_FIRST": flag,
                                                                     "HIVE_FAMILIAR_TASKS": str(args.familiar_index),
                                                                     "HIVE_CUTOFF_REPAIR": str(int(args.cutoff_repair)),
                                                                     "HIVE_CUTOFF_CONTINUE": str(int(bool(prefix))),
                                                                     "HIVE_CUTOFF_CONTINUE_BORROW": str(int(args.borrow_stdout_budget))}),
                  patch.object(solo.ternary, "up", return_value=url), patch.object(solo.ternary, "_ask", ask),
                  patch.object(solo, "LONG", 192), patch.object(solo, "TURNS", 3),
                  patch.object(solo, "solved", return_value=[])):
                work = Path(root) / "work"
                work.mkdir()
                board = solo.Board(root, echo=False)
                result = solo.member(task, 1, board, solo.Guard(board, approve="never", goal=task), work, 0,
                                     who="t80+g55trunk")
                grade = (question[3](Path(root), result["answer"]) if ident == selected
                         else panel.grade({"id": ident}, result["answer"], work))
                files = {p: (work / p).read_text(errors="replace")[:2000] for p in solo.wanted(task)
                         if (work / p).is_file()}
                assert 1 <= len(calls) <= 3 and sum(c["usage"]["completion_tokens"] for c in calls) <= 576
                record["arms"].append({"id": ident, "inspect": flag, "ok": grade[0], "reason": grade[1],
                                       "files": files, "calls": calls, "messages": result["messages"],
                                       "answer": result["answer"], "turns": result["turns"],
                                       "affinity": sorted(os.sched_getaffinity(0))})
                generate.save(args.out, record)
                print(ident, flag, grade, flush=True)
        record["complete"] = len(record["arms"]) == len(treatments)
        generate.save(args.out, record)


if __name__ == "__main__":
    main()
