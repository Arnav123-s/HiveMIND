"""Observe each specialist on its held-out eval set and score it.

    python training/observe.py --only coordinator verifier --tag base --no-adapters
    python training/observe.py --tag trained

Writes training/reports/<tag>.json with per-case outputs and per-specialist scores.
"""
import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "training"))

ap = argparse.ArgumentParser()
ap.add_argument("--only", nargs="*")
ap.add_argument("--tag", default="eval")
ap.add_argument("--no-adapters", action="store_true")
ap.add_argument("--live", action="store_true", help="also run live browser tasks")
args = ap.parse_args()
if args.no_adapters:
    os.environ["AGENT_TEAM_NO_ADAPTERS"] = "1"

from team import llm  # noqa: E402
from team.board import Board  # noqa: E402
from team.guard import Guard  # noqa: E402
from team.specialists import browser_agent, coder, coordinator, researcher, verifier, writer  # noqa: E402
from team.tools.sandbox import run_python  # noqa: E402
from evals import cases  # noqa: E402
from evals.browser_cases import CASES as BROWSER_CASES, LIVE as BROWSER_LIVE  # noqa: E402

WORK = ROOT / "training" / "runs"
WORK.mkdir(parents=True, exist_ok=True)
REPORT = {"tag": args.tag, "adapters": not args.no_adapters, "time": time.strftime("%F %T"), "scores": {}, "cases": {}}


def record(spec, case, score, out, **extra):
    REPORT["cases"].setdefault(spec, []).append({"case": case, "score": round(score, 3), "output": out, **extra})
    print(f"  {spec:<18} {score:.2f}  {case[:70]}", flush=True)


# ---------------------------------------------------------------- coordinator
def eval_coordinator():
    for c in cases.COORDINATOR:
        data, raw = llm.chat_json("coordinator", coordinator.plan_messages(c["task"]), max_new_tokens=900)
        steps, problems = coordinator.normalize(data, c["task"])
        checks = {"valid": steps is not None}
        if steps:
            agents = {s["agent"] for s in steps}
            checks["clean"] = not problems
            checks["right_agents"] = all(any(a in agents for a in grp) for grp in c["need"])
            checks["size"] = 3 <= len(steps) <= 7
            checks["done_when"] = all(s["done_when"] for s in steps)
            checks["ends_writer"] = (data or {}).get("steps", [{}])[-1].get("agent") == "writer" if isinstance(data, dict) and data.get("steps") else False
            if c.get("for_each"):
                checks["for_each"] = any(s["for_each"] for s in steps)
        score = sum(checks.values()) / max(len(checks), 6)
        record("coordinator", c["task"], score, raw, checks=checks, problems=problems)


# ---------------------------------------------------------------- researcher
VALID_SOURCES = {"huggingface", "hn", "arxiv", "pypi", "wikipedia", "web", "url"}


def eval_researcher_plan():
    for c in cases.RESEARCHER_PLAN:
        data, raw = llm.chat_json("researcher", researcher.plan_messages(c["task"], ""), max_new_tokens=300)
        checks = {"valid": isinstance(data, dict) and isinstance(data.get("searches"), list)}
        if checks["valid"]:
            srcs = [str(s.get("source", "")).lower() for s in data["searches"] if isinstance(s, dict)]
            used = set(srcs) | ({"url"} if data.get("urls") else set())
            checks["known_sources"] = bool(srcs or data.get("urls")) and all(s in VALID_SOURCES for s in srcs)
            checks["right_source"] = bool(used & set(c["sources"]))
            checks["short_queries"] = all(len(str(s.get("q", "")).split()) <= 8 for s in data["searches"] if isinstance(s, dict))
        score = sum(checks.values()) / 4
        record("researcher_plan", c["task"], score, raw, checks=checks)


def eval_researcher_extract():
    for c in cases.RESEARCHER_EXTRACT:
        data, raw = llm.chat_json("researcher", researcher.extract_messages(c["task"], c["sources"]), max_new_tokens=900)
        checks = {"valid": isinstance(data, dict)}
        if checks["valid"]:
            facts = [f for f in data.get("facts") or [] if isinstance(f, dict)]
            all_text = "\n".join(c["corpus"].values())
            checks["has_facts"] = len(facts) > 0
            checks["quotes_exact"] = bool(facts) and all(verifier.quote_in(f.get("quote", ""), all_text) for f in facts)
            checks["urls_real"] = bool(facts) and all(
                f.get("url") in c["corpus"] or f.get("url", "") in all_text for f in facts)
            items = [str(i) for i in data.get("items") or []]
            if c["items"]:
                want = {verifier.norm(i) for i in c["items"]}
                got = {verifier.norm(i) for i in items}
                checks["items_recall"] = len(want & got) / len(want) >= 0.6
                checks["items_precise"] = bool(got) and len(got & want) / len(got) >= 0.6
            for m in c.get("must_mention", []):
                checks["mentions_" + m] = m in json.dumps(data)
        score = sum(checks.values()) / len(checks) if checks["valid"] else 0
        record("researcher_extract", c["task"], score, raw, checks=checks)


# ---------------------------------------------------------------- verifier
def eval_verifier():
    for kind, label, p in cases.VERIFIER:
        if kind == "fact":
            ok, why = verifier.check_fact(p["claim"], p["quote"])
            got = "SUPPORTED" if ok else "UNSUPPORTED"
        else:
            got, why = verifier.judge(p["check"], p["work"], p["evidence"])
        record("verifier", f"{label}: {p.get('claim') or p.get('check')}", float(got == label), f"{got}: {why}")


# ---------------------------------------------------------------- coder
def check_code_case(c, wd, res):
    chk = c["check"]
    if res["returncode"] != 0:
        return False
    if "stdout_regex" in chk:
        return bool(re.search(chk["stdout_regex"], res["stdout"]))
    f = wd / chk["file"]
    if not f.exists():
        return False
    t = f.read_text(errors="replace")
    if "file_regex" in chk:
        return bool(re.search(chk["file_regex"], t, re.M))
    if "json_equals" in chk:
        try:
            return json.loads(t) == chk["json_equals"]
        except json.JSONDecodeError:
            return False
    if "csv_rows" in chk:
        rows = list(csv.reader(t.strip().splitlines()))
        return len(rows) - 1 == chk["csv_rows"]
    if "first_line" in chk:
        return t.strip().splitlines()[0].strip().lower() == chk["first_line"] if t.strip() else False
    return True


def eval_coder():
    class _G:  # approve nothing risky during evals
        def check_code(self, agent, code):
            return True
    for c in cases.CODER:
        wd = Path(tempfile.mkdtemp(prefix="coder_eval_", dir=WORK))
        for name, content in c.get("setup", {}).items():
            (wd / name).write_text(content)
        b = Board(wd / "_board", echo=False)
        # first-try score and with-repair score
        from team.tools.preview import preview
        out = llm.chat("coder", coder.task_messages(c["task"], "", preview(c["task"], wd)), max_new_tokens=1400, stop="code")
        code = coder.extract_code(out)
        res = run_python(code, wd, name="first.py", timeout=180)
        first = check_code_case(c, wd, res)
        if first:
            final, attempts = True, 1
        else:
            r = coder.run(c["task"], "", b, "eval", _G(), wd)
            res2 = {"returncode": r["returncode"], "stdout": r["summary"]}
            final, attempts = check_code_case(c, wd, res2), r["attempts"]
        record("coder", c["task"], (first + final) / 2, code[:1500], first_try=first, with_repair=final,
               attempts=attempts, stderr=res["stderr"][-400:])


# ---------------------------------------------------------------- writer
def eval_writer():
    for c in cases.WRITER:
        out = llm.chat("writer", writer.messages(c["goal"], c["task"], c["results"], c["sources"]), max_new_tokens=900)
        cites = [int(n) for n in re.findall(r"\[(\d+)\]", out)]
        urls = re.findall(r"https?://[^\s)\]]+", out)
        checks = {
            "cites_valid": all(1 <= n <= len(c["sources"]) for n in cites),
            "cites_present": bool(cites),
            "no_new_urls": all(any(u.startswith(s[:40]) for s in c["sources"]) for u in urls),
            "has_key_facts": all(m in out for m in c["must"]),
            "concise": len(out) < 2500,
        }
        if c.get("must_flag_gap"):
            checks["flags_gap"] = bool(re.search(r"not confirmed|could not|unverified|failed|unknown", out, re.I))
        record("writer", c["goal"], sum(checks.values()) / len(checks), out, checks=checks)


# ---------------------------------------------------------------- browser
def score_browser_action(case, obs_elements, page_text, action):
    exp = case["expect"]
    if not isinstance(action, dict):
        return 0.0
    a = action.get("action")
    if "click_text" in exp:
        ok_ids = {e["id"] for e in obs_elements.values() if re.search(exp["click_text"], e["text"])}
        return float(a == "click" and str(action.get("id")).isdigit() and int(action["id"]) in ok_ids)
    if "done_evidence" in exp:
        ev = str(action.get("evidence", ""))
        return float(a == "done" and verifier.quote_in(ev, page_text) and bool(re.search(exp["done_evidence"], ev + " " + str(action.get("answer", "")))))
    if "fail" in exp:
        return float(a == "fail")
    if "goto_host" in exp:
        return float(a == "goto" and exp["goto_host"] in str(action.get("url", "")))
    return 0.0


def eval_browser():
    from team.tools.browser import Browser
    b = Browser()
    try:
        for c in BROWSER_CASES:
            if c["url"] != "about:blank":
                b.goto(c["url"])
            else:
                b.page.goto("about:blank")
            obs = b.observe(c["goal"])
            page_text = b.text(20000)
            action, raw = llm.chat_json("browser", browser_agent.turn_messages(c["goal"], obs, c.get("history", [])),
                                        max_new_tokens=160)
            record("browser", c["name"], score_browser_action(c, b.elements, page_text, action), raw)
    finally:
        b.close()


def eval_browser_live():
    for c in BROWSER_LIVE:
        wd = Path(tempfile.mkdtemp(prefix="browser_live_", dir=WORK))
        board = Board(wd, echo=False)
        res = browser_agent.run(c["goal"], "", board, "live", Guard(board, "never"), start_url=c["url"])
        ok = (not res.get("failed")) and verifier.quote_in(res.get("evidence", ""), res.get("page_text", "")) \
            and bool(re.search(c["answer"], res.get("summary", "") + " " + res.get("evidence", "")))
        record("browser_live", c["name"], float(ok), res.get("summary") or res.get("failed"),
               actions=res.get("actions"))


SUITES = {"coordinator": eval_coordinator, "researcher_plan": eval_researcher_plan,
          "researcher_extract": eval_researcher_extract, "verifier": eval_verifier, "writer": eval_writer,
          "browser": eval_browser, "coder": eval_coder}
if args.live:
    SUITES["browser_live"] = eval_browser_live

out_path = ROOT / "training" / "reports" / f"{args.tag}.json"
if out_path.exists():
    old = json.loads(out_path.read_text())
    REPORT["scores"].update(old.get("scores", {}))
    REPORT["cases"].update(old.get("cases", {}))
for name, fn in SUITES.items():
    if args.only and name not in args.only:
        continue
    print(f"== {name}", flush=True)
    REPORT["cases"][name] = []
    t0 = time.time()
    fn()
    sc = [c["score"] for c in REPORT["cases"][name]]
    REPORT["scores"][name] = {"mean": round(sum(sc) / len(sc), 3), "n": len(sc), "seconds": round(time.time() - t0)}
    print(f"   -> {name}: {REPORT['scores'][name]}", flush=True)
    out_path.write_text(json.dumps(REPORT, indent=1, ensure_ascii=False))
print(json.dumps(REPORT["scores"], indent=1))
