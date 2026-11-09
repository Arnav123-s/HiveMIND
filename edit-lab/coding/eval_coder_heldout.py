"""Held-out coder eval — skeleton, UNTESTED.

Mirrors training/observe.py's eval_coder exactly (same task messages, same
sandbox, same (first-try + with-repair) / 2 scoring, same repair loop),
but scores the NEW held-out tasks in eval_tasks.jsonl with the extended
check kinds defined there. These tasks are never training data.

Run (when the machine is free — loads Qwen2.5-Coder-1.5B through the HF
engine of the copied repo tree):

    cd ~/workspace/edit-lab/tree
    HF_HOME=~/workspace/edit-lab/hf AGENT_TEAM_ENGINE=hf \
    AGENT_TEAM_ADAPTERS=~/workspace/edit-lab/candidates-coder \
        ~/workspace/edit-lab/venv/bin/python \
        ~/workspace/edit-lab/coding/eval_coder_heldout.py --tag base
    # candidate: put the trained adapter in <AGENT_TEAM_ADAPTERS>/coder/
    # base:      add --no-adapters

Win rule (PLAN.md section 8): the adapter is kept only if its mean score
beats the reproduced base mean on this set AND does not materially
regress on the repo's own cases.CODER (observe.py --only coder).
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = Path(os.environ.get("EDIT_LAB_TREE", Path.home() / "workspace/edit-lab/tree"))

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="heldout")
ap.add_argument("--no-adapters", action="store_true")
ap.add_argument("--only", nargs="*", help="task ids")
args = ap.parse_args()
if args.no_adapters:
    os.environ["AGENT_TEAM_NO_ADAPTERS"] = "1"

sys.path.insert(0, str(TREE))
sys.path.insert(0, str(TREE / "training"))

from team import llm  # noqa: E402
from team.board import Board  # noqa: E402
from team.specialists import coder  # noqa: E402
from team.tools.preview import preview  # noqa: E402
from team.tools.sandbox import run_python  # noqa: E402

WORK = HERE / "runs"
WORK.mkdir(exist_ok=True)
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)


def check(task, wd, res):
    """Hard checks only: the program ran, then its output/files must match."""
    if res["returncode"] != 0:
        return False
    chk = task["check"]
    kind = chk["kind"]
    if kind == "stdout_equals":
        return res["stdout"].strip() == chk["text"].strip()
    if kind == "stdout_lines_equals":
        got = [l for l in res["stdout"].strip().splitlines()]
        return got == [str(x) for x in chk["lines"]]
    if kind == "stdout_regex":
        import re
        return bool(re.search(chk["stdout_regex"], res["stdout"]))
    f = Path(wd) / chk["file"]
    if not f.exists():
        return False
    text = f.read_text(errors="replace")
    if kind == "file_equals":
        return text == chk["text"]
    if kind == "file_json_equals":
        try:
            return json.loads(text) == chk["value"]
        except json.JSONDecodeError:
            return False
    raise ValueError(f"unknown check kind {kind}")


def main():
    tasks = [json.loads(l) for l in (HERE / "eval_tasks.jsonl").read_text().splitlines() if l.strip()]
    if args.only:
        tasks = [t for t in tasks if t["id"] in args.only]
    report = {"tag": args.tag, "adapters": not args.no_adapters,
              "time": time.strftime("%F %T"), "cases": []}

    class _G:  # approve nothing risky during evals (same as observe.py)
        def check_code(self, agent, code):
            return True

    for t in tasks:
        wd = Path(tempfile.mkdtemp(prefix="coder_heldout_", dir=WORK))
        for name, content in t.get("setup", {}).items():
            (wd / name).write_text(content)
        b = Board(wd / "_board", echo=False)
        out = llm.chat("coder", coder.task_messages(t["task"], "", preview(t["task"], wd)),
                       max_new_tokens=1400, stop="code")
        code = coder.extract_code(out)
        res = run_python(code, wd, name="first.py", timeout=180)
        first = check(t, wd, res)
        if first:
            final, attempts = True, 1
        else:
            r = coder.run(t["task"], "", b, "eval", _G(), wd)
            res2 = {"returncode": r["returncode"], "stdout": r["summary"]}
            final, attempts = check(t, wd, res2), r["attempts"]
        score = (first + final) / 2
        report["cases"].append({"id": t["id"], "category": t["category"], "score": score,
                                "first_try": first, "with_repair": final, "attempts": attempts})
        print(f"  {t['id']:<24} {score:.2f}  first={first} repair={final}", flush=True)

    scores = [c["score"] for c in report["cases"]]
    report["mean"] = round(sum(scores) / len(scores), 3) if scores else 0.0
    report["n"] = len(scores)
    (RESULTS / f"{args.tag}.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({"mean": report["mean"], "n": report["n"]}))


if __name__ == "__main__":
    main()
