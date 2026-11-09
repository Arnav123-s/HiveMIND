"""The same test inputs, answered by whatever does each job in the hive TODAY (bigger member or code rule).

    python training/cells_incumbents.py <skill> [...]
Writes training/reports/cells/incumbent_<skill>.json: score and seconds per call.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AGENT_TEAM_ENGINE", "gguf")
os.environ["AGENT_TEAM_CELLS"] = "0"  # the incumbents alone: no cell may answer for them (e.g. inside parse_json)
from team import guard, llm, prompts  # noqa: E402
from team.cells import skills as S  # noqa: E402
from training.cells import data  # noqa: E402

OUT = ROOT / "training" / "reports" / "cells"

# who does each job today: (member, how it is asked)
INCUMBENT = {
    "route_step": "coordinator", "pick_source": "researcher", "next_move": "coordinator", "split_orders": "coordinator",
    "quote_pick": "researcher", "claim_support": "verifier", "pick_element": "browser", "licence_open": "juror_brain",
    "json_repair": "code:parse_json", "family_topic": "code:guard.FAMILY",
    # the research hive's jobs: what does each without the cell (word overlap; any claim counts; the 4B juror, as
    # nothing cross-checks sources without the cell)
    "result_relevant": "code:words", "answers_q": "code:any", "claims_agree": "juror_brain",
    "de_grammar": "code:ok",  # nothing checks a translation's German today: every sentence passes
    **{f"orders_{k}": "order_reader" for k in ("spend", "delete", "send", "login", "signup")},
}


_ORDERS = {}


def ask_member(member, skill, x):
    spec = S.SKILLS[skill]
    if skill == "pick_element":  # exactly how the browser is asked today: its own prompt, the id of the action it takes
        from team.specialists.browser_agent import turn_messages
        goal, els = x.split("\nELEMENTS:\n", 1)
        obs = {"url": "https://shop.example/", "title": "Shop", "text": "", "elements": els}
        data_, raw = llm.chat_json(member, turn_messages(goal.removeprefix("GOAL: "), obs, []), max_new_tokens=60)
        if isinstance(data_, dict) and str(data_.get("id", "")).isdigit():
            return str(data_["id"])
        m = re.search(r"\d+", raw or "")
        return m.group(0) if m else ""
    if skill == "claim_support":  # exactly how the verifier is asked today
        claim, quote = x.split("\nQUOTE: ")
        data_, _ = llm.chat_json(member, [{"role": "system", "content": prompts.VERIFIER_FACT},
                                          {"role": "user", "content": f"{claim}\nQUOTE: {quote}"}], max_new_tokens=60)
        return str((data_ or {}).get("verdict", "")).upper() if isinstance(data_, dict) else ""
    if skill.startswith("orders_"):  # exactly how the order reader is asked today (once per sentence)
        if x not in _ORDERS:
            data_, _ = llm.chat_json(member, [{"role": "system", "content": prompts.ORDER_READER},
                                              {"role": "user", "content": x}], max_new_tokens=40)
            _ORDERS[x] = (data_ or {}).get("orders", []) if isinstance(data_, dict) else []
        return "yes" if skill.split("_", 1)[1] in _ORDERS[x] else "no"
    if "labels" in spec:
        sys_ = spec["instr"] + ' Reply with JSON only: {"answer": "<one of: ' + ", ".join(spec["labels"]) + '>"}'
    else:
        sys_ = spec["instr"] + ' Reply with JSON only: {"answer": "<your answer>"}'
    data_, raw = llm.chat_json(member, [{"role": "system", "content": sys_}, {"role": "user", "content": x}],
                               max_new_tokens=spec.get("max_new", 30) + 20)
    return str((data_ or {}).get("answer", "")) if isinstance(data_, dict) else raw


def ask_code(skill, x):
    if skill == "json_repair":
        got = llm.parse_json(x)
        return json.dumps(got) if got is not None else ""
    if skill == "family_topic":
        return "yes" if guard.FAMILY.search(x) else "no"
    if skill == "result_relevant":  # exactly the research hive's fallback
        from team.specialists import research_hive
        q, r = x.split("\nRESULT: ", 1)
        t, _, sn = r.partition(" | ")
        return "yes" if research_hive.relevant(q.removeprefix("QUESTION: "), [{"title": t, "snippet": sn}])[0] else "no"
    if skill == "answers_q":
        return "yes"
    if skill == "de_grammar":
        return "ok"
    raise ValueError(skill)


def run(skill, out_name=None):
    inc = INCUMBENT[skill]
    _, _, te = data(skill)
    t0 = time.time()
    preds = [ask_code(skill, x) if inc.startswith("code:") else ask_member(inc, skill, x) for x, _ in te]
    sec = (time.time() - t0) / len(te)
    acc = sum(S.score(skill, p, y) for p, (_, y) in zip(preds, te)) / len(te)
    member = inc if inc.startswith("code:") else f"{inc} = {__import__('team.config', fromlist=['x']).GGUF_ROSTER[inc]}"
    res = {"skill": skill, "incumbent": member, "test": round(acc, 4), "ms_per_call": round(sec * 1000, 1), "n": len(te),
           "errors": [(x, y, p) for (x, y), p in zip(te, preds) if not S.score(skill, p, y)]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (out_name or f"incumbent_{skill}.json")).write_text(json.dumps(res, indent=1))
    print(f"{skill}: {member} test {acc:.3f} ({sec * 1000:.0f} ms/call)", flush=True)
    return res


if __name__ == "__main__":
    for s in sys.argv[1:]:  # skill, or skill=member to measure another member on the same inputs (not the incumbent)
        if "=" in s:
            sk, member = s.split("=", 1)
            INCUMBENT[sk] = member  # its own file: the incumbent's measurement is never overwritten
            run(sk, out_name=f"alt_{sk}_{member}.json")
        else:
            run(s)
