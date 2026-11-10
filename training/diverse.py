"""Do small models of different families miss different things? (His question: the small hive may be losing because
its members are all the same model.)

    python training/diverse.py [--n 32] [--models ...]   (default: the coder's two, Qwen3-1.7B, and every recruit)
The coder's exam lessons (training/data/school/coder.jsonl, never trained on by anyone): each small model writes the
program alone, the program is run, and what it prints is compared with what the 7B teacher's program printed
(team/school.py, _program_key). The taught Qwen2.5-Coder-1.5B (coder_school) and the untouched one are the same model
twice; the others are other families. Measured:
- each model alone;
- for every pair, how many lessons both get wrong, against what two independent models with those scores would
  both get wrong by chance (above it: they make the same mistakes);
- "someone right": lessons at least one of a group gets right, for the same-model pair and for mixed groups;
- a vote that needs no teacher: what most models print (a tie goes to the best one alone), and how often two
  different models that print the same are right.
Nothing is trained. Writes training/reports/diverse_coders.json (answers are kept: a cut-off run goes on).
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team import llm, school  # noqa: E402

OUT = ROOT / "training" / "reports" / "diverse_coders.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=32)
    from team import recruit
    ap.add_argument("--models", nargs="+", default=["coder15+coder_school", "coder15", "fast"]
                    + [k for k in recruit.record() if not k.startswith("_")])
    a = ap.parse_args()
    te = [x for x in school.lessons("coder") if x["exam"]][:a.n]
    try:
        got = json.loads(OUT.read_text())["answers"]
    except (OSError, ValueError, KeyError):
        got = {}
    for m in a.models:
        mine = got.setdefault(m, {})
        for i, x in enumerate(te):
            if x["task"] in mine:
                continue
            with school._as("coder", m):
                out = llm.chat("coder", x["messages"], max_new_tokens=900, adapter="+" in m, stop="code")
            mine[x["task"]] = school._program_key(out, x["task"])
            if i % 8 == 7:
                OUT.write_text(json.dumps({"answers": got}, indent=1, ensure_ascii=False))
        OUT.write_text(json.dumps({"answers": got}, indent=1, ensure_ascii=False))
        print(f"{m}: {sum(school._k(mine[x['task']]) == x['key'] for x in te)} of {len(te)}", flush=True)
        llm.unload_all()
    n = len(te)
    right = {m: [school._k(got[m][x["task"]]) == x["key"] for x in te] for m in a.models}
    alone = {m: sum(right[m]) for m in a.models}
    pairs = {}
    for p, q in itertools.combinations(a.models, 2):
        both = sum(not r and not s for r, s in zip(right[p], right[q]))
        pairs[f"{p} & {q}"] = {"both_wrong": both, "by_chance": round((n - alone[p]) * (n - alone[q]) / n, 1),
                               "someone_right": sum(r or s for r, s in zip(right[p], right[q]))}
    order = sorted(a.models, key=lambda m: -alone[m])

    def vote(ms):
        ok = 0
        for x in te:
            keys = {m: school._k(got[m][x["task"]]) for m in ms}
            ok += school.majority(keys, [m for m in order if m in ms]) == x["key"]
        return ok
    groups = {"same model twice": a.models[:2], "three families": [order[0]] + [m for m in order if m.split("+")[0] != order[0].split("+")[0]][:2],
              "all": a.models}
    agree = {}
    for p, q in itertools.combinations(a.models, 2):
        if p.split("+")[0] == q.split("+")[0]:
            continue
        same = [x for x in te if got[p][x["task"]] is not None and school._k(got[p][x["task"]]) == school._k(got[q][x["task"]])]
        agree[f"{p} & {q}"] = {"print_the_same": len(same), "of_those_right": sum(school._k(got[p][x["task"]]) == x["key"] for x in same)}
    res = {"lessons": n, "alone": alone, "pairs": pairs,
           "groups": {g: {"models": ms, "someone_right": sum(any(right[m][i] for m in ms) for i in range(n)),
                          "most_print": vote(ms)} for g, ms in groups.items()},
           "two_different_models_print_the_same": agree, "answers": got}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in res.items() if k != "answers"}, indent=1))


if __name__ == "__main__":
    main()
