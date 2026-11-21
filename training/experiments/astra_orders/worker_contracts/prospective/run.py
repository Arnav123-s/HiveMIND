"""Run or resume the preregistered G55 three-task fixed versus borrowed-budget comparison."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import stat
import subprocess
import time
from unittest.mock import patch

from team import solo
from training import exam, kinds
from training.experiments.astra_orders import generate

HERE = Path(__file__).resolve().parent
REGISTRATION = "bf8b4d74042bcb037477d661ac43cdb0f9eaded04861fc98bf2c9b3be39f81ee"
LEGACY_RUNNER = "e8dd600a80b6e757e135dd72a0dae244a2a6220f6d530f33e03b1bfb2fd6ae70"
LEGACY_JOURNAL = "fb9d175346f79b605d8d3e86ce23a9ab28225dcc325705ddcaf9be244dc61ceb"
LEGACY_ROOT = "/tmp/tmpt5ib3ei5"
PATH_RUNNER = "b92fddd59e658b0497e4be1e3b3704c89f5e508a7f12865773f0c69aa322aa06"
PATH_JOURNAL = "ee1508442b6f0935b94f473562a6155b5d51b0f0078113fdc489fbf0fb4360a5"
SEAT = "t80+g55trunk"
ARMS = ("fixed", "borrow")
SETTINGS = {"temperature": 0., "top_p": 1., "top_k": 0, "cache_prompt": False, "seed": 8103,
            "chat_template_kwargs": {"enable_thinking": False}}
FLAGS = ["-ngl", "0", "-c", "2048", "-t", "2", "-tb", "2", "-rtr", "-b", "128", "-ub", "128",
         "--parallel", "1", "--threads-http", "2", "--host", "127.0.0.1", "--jinja"]
ENV = {"HIVE_ASSERT_FIRST": "1", "HIVE_CUTOFF_CONTINUE": "1", "HIVE_CUTOFF_REPAIR": "0", "HIVE_LIBRARY": "0",
       "HIVE_NOTES": "0", "HIVE_PAGE_CHECKS": "0", "HIVE_HTTP_CACHE": "0", "HIVE_FULL_ORDERS": "0", "HIVE_SHORT_ORDERS": "0"}


def utc():
    return datetime.now(timezone.utc).isoformat()


class Pause(Exception):
    """The next genuine model request has not been sent."""


def case_roots(run_id, kinds, migrated):
    if not isinstance(run_id, str) or not re.fullmatch("[0-9a-f]{32}", run_id):
        raise ValueError("invalid workspace ID")
    return {k: LEGACY_ROOT if migrated and k == "h_tab_dates" else f"/tmp/hive-f3-{run_id}-{k}" for k in kinds}


def migrate(raw, record, config):
    """Only the two exact published partial checkpoints may cross runner versions."""
    digest = hashlib.sha256(raw).hexdigest()
    if digest == PATH_JOURNAL:
        case = "h_tab_dates"
        fixed, borrow = (record["calls"][case][arm] for arm in ARMS)
        if (record["config"] != (config | {"runner_sha256": PATH_RUNNER}) or record["complete"] or record.get("in_flight")
                or list(record["arms"][case]) != ["fixed"] or len(fixed) != 3 or len(borrow) != 3
                or record["case_roots"] != case_roots(record["workspace_id"], record["calls"], True)
                or any(b["source"] != f["id"] or b["request"] != f["request"] or b["response"] != f["response"]
                       for f, b in zip(fixed, borrow))):
            raise ValueError("unexpected six-call observation checkpoint")
        record["config"] = config
        record["output_check_migration"] = {
            "from_runner_sha256": PATH_RUNNER, "from_journal_sha256": PATH_JOURNAL,
            "retained_calls": [c["id"] for c in fixed + borrow], "retained_grade": f"{case}/fixed",
            "reason": "The earlier runner stopped before recording a shared-response pair with different worker stdout."}
        return
    if (digest != LEGACY_JOURNAL or record["config"] != (config | {"runner_sha256": LEGACY_RUNNER})
            or record["config"]["registration_sha256"] != REGISTRATION or record.get("in_flight") or record["complete"]
            or any(record["arms"].values())):
        raise ValueError("the run configuration or legacy journal differs")
    saved = [c for arms in record["calls"].values() for journal in arms.values() for c in journal]
    if ([c["id"] for c in saved] != ["h_tab_dates/fixed/1", "h_tab_dates/fixed/2"]
            or any(c["origin"] != "native" or c["source"] != c["id"] for c in saved)):
        raise ValueError("legacy checkpoint has different sampled calls")
    feedback = saved[1]["request"]["messages"][-1]
    if (feedback["role"] != "user" or f'File "{LEGACY_ROOT}/work/member1_1.py", line 23' not in feedback["content"]
            or "SyntaxError:" not in feedback["content"]):
        raise ValueError("legacy receipt does not establish the original worker path")
    if os.path.lexists(LEGACY_ROOT):
        raise FileExistsError(LEGACY_ROOT)
    record.update(config=config, migration={"from_runner_sha256": LEGACY_RUNNER, "from_journal_sha256": LEGACY_JOURNAL,
                                            "retained_calls": [c["id"] for c in saved]})


@contextmanager
def empty_case_root(path):
    """Create exclusively. Clean entries through the original directory descriptor."""
    root = Path(path)
    root.mkdir(mode=0o700)  # An existing directory, file or symlink belongs to someone else.
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield root
    finally:
        try:
            if not os.path.samestat(os.fstat(fd), root.lstat()):
                raise RuntimeError(f"the trial directory was replaced: {root}")
            for name in os.listdir(fd):
                if stat.S_ISDIR(os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode):
                    shutil.rmtree(name, dir_fd=fd)
                else:
                    os.unlink(name, dir_fd=fd)
            if os.path.samestat(os.fstat(fd), root.lstat()):
                root.rmdir()
        finally:
            os.close(fd)


@contextmanager
def server(args):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    flags = FLAGS + ["--port", str(port)]
    with args.log.open("ab") as log:
        proc = subprocess.Popen([str(args.runtime), "-m", str(args.model), "--lora", str(args.lora), *flags],
                                stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            start = time.monotonic()
            while time.monotonic() - start < 120 and proc.poll() is None:
                try:
                    if generate.call(url + "/health", timeout=1).get("status") == "ok":
                        break
                except OSError:
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError("packed worker failed to start")
            adapters = generate.call(url + "/lora-adapters")
            if len(adapters) != 1 or Path(adapters[0]["path"]).resolve() != args.lora.resolve() or adapters[0]["scale"] != 1.:
                raise ValueError("loaded adapter differs from the preregistered G55 trunk")
            yield url, proc, flags, adapters
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def run_arm(args, record, case, grade, arm, url, proc):
    kind = case["kind"]
    logs = record["calls"][kind]
    journal = logs[arm]
    ordinal = 0

    def ask(who, endpoint, cell, path, body, cap):
        nonlocal ordinal
        if (who != SEAT or endpoint != url or cell != ("g55trunk", ()) or path != "/v1/chat/completions"
                or body["max_tokens"] != cap or not 1 <= cap <= 384 or ordinal >= 3):
            raise ValueError("unexpected worker request")
        # Only cache_prompt and the deterministic seed are set by this runner.
        payload = dict(body, cache_prompt=False, seed=8103)
        if {k: v for k, v in payload.items() if k not in ("max_tokens", "messages")} != SETTINGS:
            raise ValueError("unexpected sampling settings")
        # Later feedback mutates the worker conversation. Preserve exactly what crossed the model boundary.
        payload = json.loads(json.dumps(payload))
        i = ordinal
        ident = f"{kind}/{arm}/{i + 1}"
        if i < len(journal):
            row = journal[i]
            if row["id"] != ident or row["request"] != payload:
                raise ValueError(f"resumed worker request changed at {ident}")
        else:
            control = logs["fixed"][i] if arm == "borrow" and i < len(logs["fixed"]) else None
            if control is not None and control["request"] == payload:
                row = {"id": ident, "source": control["id"], "origin": "shared", "response": control["response"]}
            else:
                if arm == "borrow" and i == 0:
                    raise ValueError("first requests must match across arms")
                if args.pause_file.exists():
                    raise Pause()
                start, cpu = time.monotonic(), generate.cpu(proc.pid)
                # Journal the intent first so an interrupted response cannot silently become a second draw.
                record["in_flight"] = {"id": ident, "request": payload, "utc": utc()}
                generate.save(args.out, record)
                try:
                    reply = generate.call(url + path, payload, timeout=900)
                except Exception as exc:
                    record["in_flight"]["error"] = f"{type(exc).__name__}: {exc}"
                    generate.save(args.out, record)
                    raise RuntimeError(f"no completed receipt for {ident}") from exc
                row = {"id": ident, "source": ident, "origin": "native", "response": reply,
                       "wall_s": round(time.monotonic() - start, 3), "server_cpu_s": round(generate.cpu(proc.pid) - cpu, 3)}
                del record["in_flight"]
            row.update(request=payload, ordinal=i + 1, utc=utc())
            journal.append(row)
            generate.save(args.out, record)
        reply = row["response"]
        tokens = reply["usage"]["completion_tokens"]
        if (type(tokens) is not int or not 0 <= tokens <= cap or
                not isinstance(reply["choices"][0]["message"]["content"], str)):
            raise ValueError(f"unmeasured or invalid native response at {ident}")
        ordinal += 1
        return reply

    flags = dict(ENV, HIVE_FAMILIAR_TASKS=str(args.familiar_index.resolve()), HIVE_CUTOFF_CONTINUE_BORROW=str(int(arm == "borrow")))
    orders = solo.orders
    with (empty_case_root(record["case_roots"][kind]) as root, patch.dict(os.environ, flags),
          patch.object(solo, "orders", side_effect=lambda who: orders(who, today=record["orders_date_utc"])),
          patch.object(solo.ternary, "up", return_value=url), patch.object(solo.ternary, "_ask", side_effect=ask),
          patch.object(solo, "LONG", 192), patch.object(solo, "TURNS", 3), patch.object(solo, "solved", return_value=[])):
        work = Path(root) / "work"
        work.mkdir()
        board = solo.Board(root, echo=False)
        result = solo.member(case["task"], 1, board, solo.Guard(board, approve="never", goal=case["task"]), work, 0., who=SEAT)
        if ordinal != len(journal) or not 1 <= ordinal <= 3:
            raise ValueError("completed worker did not consume the expected journal")
        total = sum(c["response"]["usage"]["completion_tokens"] for c in journal)
        if total > 576:
            raise ValueError("worker exceeded its registered token budget")
        try:
            ok, why = grade(Path(root), result["answer"])
        except Exception as exc:  # Same failed-check outcome as training.exam.sit.
            ok, why = False, f"check failed: {type(exc).__name__}: {exc}"
        files = {}
        for name in case["requested_files"]:
            try:
                with solo.deliverables.regular(work / name) as f:
                    digest = hashlib.file_digest(f, "sha256").hexdigest()
                    size = os.fstat(f.fileno()).st_size
                    f.seek(0)
                    preview = f.read(2000).decode(errors="replace")
            except (FileNotFoundError, ValueError):
                continue
            files[name] = {"sha256": digest, "bytes": size, "preview": preview}
        return {"ok": bool(ok), "reason": why, "answer": result["answer"], "files": files, "hints": result["hints"],
                "messages": result["messages"], "turns": result["turns"], "completion_tokens": total,
                "call_count": ordinal, "fresh_calls": sum(c["origin"] == "native" for c in journal),
                "larger_cap_offered": any(c["request"]["max_tokens"] > 192 for c in journal)}


def shared_outputs(fixed, borrow):
    """Compare the original worker answers verbatim, the exact file digests and the official pass/fail grade."""
    return {"identical_file_bytes": fixed["files"] == borrow["files"], "identical_stdout": fixed["answer"] == borrow["answer"],
            "identical_grade": fixed["ok"] == borrow["ok"], "identical_call_count": fixed["call_count"] == borrow["call_count"]}


def summarize(record):
    paired = {k: arms for k, arms in record["arms"].items() if all(a in arms for a in ARMS)}
    gained = [k for k, a in paired.items() if a["borrow"]["ok"] and not a["fixed"]["ok"]]
    lost = [k for k, a in paired.items() if a["fixed"]["ok"] and not a["borrow"]["ok"]]
    comparisons = {k: a["borrow"]["shared_output_check"] for k, a in paired.items() if "shared_output_check" in a["borrow"]}
    return {"paired": len(paired), "required": 3, "right_on_paired": {a: sum(v[a]["ok"] for v in paired.values()) for a in ARMS},
            "gained": gained, "lost": lost, "net": len(gained) - len(lost),
            "larger_cap_offered": [k for k, a in paired.items() if a["borrow"]["larger_cap_offered"]],
            "unchanged_requests": [k for k, check in comparisons.items() if check["identical_call_count"]],
            "identical_outputs": [k for k, check in comparisons.items() if all(check.values())],
            "shared_reply_outputs_differ": [k for k, check in comparisons.items() if not all(check.values())],
            "paired_tokens": {a: sum(v[a]["completion_tokens"] for v in paired.values()) for a in ARMS},
            "fresh_calls": sum(row["origin"] == "native" for arms in record["calls"].values() for calls in arms.values() for row in calls)}


def run(args):
    register = HERE / "registration.json"
    if generate.file_hash(register) != REGISTRATION:
        raise ValueError("the frozen three-prompt registration changed")
    registration = json.loads(register.read_bytes())
    index = generate.file_hash(args.familiar_index)
    if index != registration["familiar_index_sha256"] or any(generate.file_hash(getattr(args, name)) != digest
                                                              for name, digest in generate.ASSETS.items()):
        raise ValueError("wrong packed model, runtime, adapter or checked history")
    affinity = sorted(os.sched_getaffinity(0))
    if len(affinity) != 2:
        raise ValueError("run on two assigned CPU cores")
    cases = registration["cases"]
    grades = {}
    for case in cases:
        kind = case["kind"]
        _, _, task, grade = exam._made(kinds.get(kind).make, case["seed"])
        if case["task"] != task or hashlib.sha256(task.encode()).hexdigest() != case["task_sha256"] or solo.wanted(task) != case["requested_files"]:
            raise ValueError(f"generator or file declaration changed for {kind}")
        grades[kind] = grade
    config = {"registration_sha256": REGISTRATION, "runner_sha256": generate.file_hash(Path(__file__)),
              "familiar_index_sha256": index, "assets": generate.ASSETS, "settings": SETTINGS, "flags": FLAGS,
              "seat": SEAT, "environment": ENV}
    if args.out.exists():
        raw = args.out.read_bytes()
        record = json.loads(raw)
        if record["config"] != config:
            migrate(raw, record, config)
            generate.save(args.out, record)
        if record.get("in_flight"):
            raise RuntimeError(f"unresolved native call {record['in_flight']['id']}; inspect server logs before retrying")
        if record["complete"]:
            return
    else:
        record = {"config": config, "start_utc": utc(), "orders_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d (%A)"),
                  "calls": {k: {a: [] for a in ARMS} for k in grades}, "arms": {k: {} for k in grades},
                  "sessions": [], "complete": False}
    migrated = "migration" in record
    if migrated and record["migration"].get("from_journal_sha256") != LEGACY_JOURNAL:
        raise ValueError("unrecognised original workspace")
    if "workspace_id" not in record:
        if any(j for arms in record["calls"].values() for j in arms.values()) and not migrated:
            raise ValueError("missing original workspace identity")
        record["workspace_id"] = secrets.token_hex(16)
        record["case_roots"] = case_roots(record["workspace_id"], grades, migrated)
        generate.save(args.out, record)
    if record.get("case_roots") != case_roots(record["workspace_id"], grades, migrated):
        raise ValueError("unexpected task workspace paths")
    try:
        if args.pause_file.exists():
            raise Pause()
        with server(args) as (url, proc, flags, adapters):
            record["sessions"].append({"utc": utc(), "flags": flags, "affinity": affinity, "adapters": adapters})
            generate.save(args.out, record)
            for case in cases:
                kind = case["kind"]
                arms = record["arms"][kind]
                for arm in ARMS:
                    if arm in arms:
                        continue
                    outcome = run_arm(args, record, case, grades[kind], arm, url, proc)
                    if arm == "borrow" and outcome["fresh_calls"] == 0:
                        outcome["shared_output_check"] = shared_outputs(arms["fixed"], outcome)
                    arms[arm] = outcome
                    record["summary"] = summarize(record)
                    generate.save(args.out, record)
                    print(kind, arm, outcome["ok"], outcome["call_count"], flush=True)
        record.update(complete=True, finished_utc=utc())
    except Pause:
        print("Paused at a native call boundary.", flush=True)
    record["summary"] = summarize(record)
    generate.save(args.out, record)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("runtime", "model", "lora", "familiar-index", "out", "log", "pause-file"):
        p.add_argument("--" + flag, type=Path, required=True)
    args = p.parse_args()
    with Path(str(args.out) + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(args)
