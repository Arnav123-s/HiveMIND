"""Record real adapter scales and replies for the released open and explicit choice requests."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new or resumable receipt directory")
    parser.add_argument("--port", type=int, default=18227, help="dedicated local port for this study")
    parser.add_argument("--form", choices=("open", "choice", "both"), default="both")
    parser.add_argument("--cases", type=Path, default=HERE / "chat-cases.json", help="JSON map of named prompts and labels")
    parser.add_argument("--domain", help="optionally run one public corpus domain")
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HIVE_TERNARY_HOME", str(args.out / "runtime"))
    os.environ.setdefault("HIVE_ENGRAMS_HOME", str(ROOT / "cells/engrams"))
    os.environ.setdefault("HIVE_BANK", "off")
    os.environ.setdefault("HIVE_TALK_LONG", "48")
    os.environ.setdefault("HIVE_TERNARY_CTX", "4096")
    os.environ.setdefault("AGENT_TEAM_SOLO", "2")
    os.environ.setdefault("AGENT_TEAM_SOLO_ALONE", "1")
    os.environ.setdefault("AGENT_TEAM_SOLO_TURNS", "1")
    os.environ.setdefault("AGENT_TEAM_SOLO_LONG", "80")
    os.environ.setdefault("AGENT_TEAM_THREADS", "2")
    from team import talk, ternary
    bank = Path(os.environ["HIVE_ENGRAMS_HOME"]) / "index.jsonl"
    modules = ("talk", "ternary", "engram", "domain_route", "domain_advice", "domain_consensus", "signals", "solo")
    inventory = dict(
        index_sha256=hashlib.sha256(bank.read_bytes()).hexdigest(),
        cases_sha256=hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        sources={p: hashlib.sha256((ROOT / "team" / (p + ".py")).read_bytes()).hexdigest() for p in modules},
        settings={key: os.environ.get(key) for key in ("AGENT_TEAM_THREADS", "HIVE_TERNARY_CTX", "HIVE_TALK_LONG",
                  "AGENT_TEAM_SOLO", "AGENT_TEAM_SOLO_TURNS", "AGENT_TEAM_SOLO_LONG", "HIVE_MEMBERS",
                  "HIVE_SIGNALS", "HIVE_ENGRAMS", "HIVE_ENGRAM_GATE", "HIVE_BANK")},
    )
    encoded = json.dumps(inventory, sort_keys=True, indent=2) + "\n"
    launch = "launch-" + hashlib.sha256(encoded.encode()).hexdigest()[:12] + ".json"
    (args.out / launch).write_text(encoded)
    # The dedicated port and local HOME isolate this process's native server and lock from other runs.
    ternary.port = lambda member: args.port
    post = ternary._post
    calls = []
    def observed_post(url, body, timeout=1800):
        if not (url.endswith("/v1/chat/completions") or url.endswith("/completion")):
            return post(url, body, timeout)
        at = url.partition("/v1/chat/completions")[0].partition("/completion")[0]
        body = dict(body, seed=741 + len(calls))
        scales = {name: scale for name, scale in ternary._loaded(at, scales=True).items() if scale}
        data = json.dumps(body.get("messages", body.get("prompt")), sort_keys=True, ensure_ascii=False)
        call = dict(active=scales, seed=body["seed"], temperature=body.get("temperature"),
                    prompt_sha256=hashlib.sha256(data.encode()).hexdigest(),
                    token_budget=body.get("max_tokens", body.get("n_predict")))
        calls.append(call)
        reply = post(url, body, timeout)
        choice = (reply.get("choices") or [{}])[0]
        call.update(text=(choice.get("message") or {}).get("content", reply.get("content", "")),
                    finish_reason=choice.get("finish_reason"), usage=reply.get("usage"))
        return reply
    ternary._post = observed_post
    cases = json.loads(args.cases.read_text())
    if not isinstance(cases, dict) or any(not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", key) for key in cases):
        parser.error("case names must be short alphanumeric file names, with optional hyphens and underscores")
    forms = ("open", "choice") if args.form == "both" else (args.form,)
    for form in forms:
        for domain, example in cases.items():
            if (args.domain and domain != args.domain) or form not in example:
                continue
            path = args.out / f"{domain}-{form}.json"
            if path.is_file():
                continue
            calls.clear()
            logs = []
            result = talk.reply(example[form], base="t80", now=datetime.datetime(2026, 11, 19, 12),
                                log=logs.append, run_dir=args.out / f"work-{domain}-{form}")
            receipt = dict(domain=domain, form=form, prompt=example[form], expected=example["label"], launch=launch,
                           result={k: v for k, v in result.items() if k not in ("dir", "task")},
                           calls=calls)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
            tmp.replace(path)
            print(domain, form, str(result.get("text"))[:150], flush=True)


if __name__ == "__main__":
    main()
