"""tiny-hive engine: many small specialists + clones, acting as one model.

One task in, one answer out. Inside: the coordinator decomposes composed
tasks, routes each step to a specialist, fans lists out across clones,
runs clone votes, checks results, and keeps a board (shared record) plus
lessons (shared knowledge) that every member's run can read.

A task the hive has no member for is declared a capability gap - logged,
never guessed. Gaps are what the evolution engine (evolve.py) feeds on.
"""
import copy, json, os, time
from collections import Counter

import members

HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS_PATH = os.path.join(HERE, "lessons.jsonl")
BOARD_DIR = os.path.join(HERE, "results")

# Rectangular domain bounds per member (args must fall inside, else the
# step is declared out-of-domain instead of being silently truncated).
BOUNDS = {
    "parity8": [(0, 255)], "popcount8": [(0, 255)], "majority5": [(0, 31)],
    "compare2": [(0, 15), (0, 15)],
    "max4": [(0, 9)] * 4, "sort3": [(0, 9)] * 3,
    "adder": [(0, 99), (0, 99)], "subtractor": [(0, 99), (0, 99)],
    "multiplier": [(0, 9), (0, 9)],
    "seqnext": [(0, 68), (0, 9)],
    "divider": [(0, 99), (1, 9)],
}


def in_domain(name, args, member=None):
    b = (member or {}).get("bounds") or BOUNDS.get(name)
    if b is None or len(b) != len(args):
        return False
    return all(lo <= v <= hi for v, (lo, hi) in zip(args, b))


def read_lessons():
    if not os.path.exists(LESSONS_PATH):
        return []
    with open(LESSONS_PATH) as f:
        return [json.loads(l) for l in f if l.strip()]


def add_lesson(member, lesson):
    with open(LESSONS_PATH, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "member": member, "lesson": lesson}) + "\n")


class Clone:
    """A bit-identical runtime copy of a specialist, spawned from the
    canonical weights. Corrupting one clone never touches the others."""
    _counter = Counter()

    def __init__(self, member):
        Clone._counter[member["name"]] += 1
        self.id = f'{member["name"]}#{Clone._counter[member["name"]]}'
        self.spec = copy.deepcopy(member)
        self.jobs = 0

    def run(self, args):
        self.jobs += 1
        return members.run_member2(self.spec, args)


class Hive:
    def __init__(self):
        self.members = members.load_all()      # canonical weights = the socialized state
        self.board = []                        # every step, recorded
        self.lessons = read_lessons()

    # -- one task in, one answer out -------------------------------------
    def run_task(self, task, check=False):
        if "steps" in task:
            results = []
            for step in task["steps"]:
                step = dict(step)
                if "fanout" in step:
                    r = self.run_fanout(step["fanout"], step["args_list"],
                                        step.get("clones", 4), check=check)
                    if r.get("status") != "ok":
                        return {"status": r.get("status"),
                                "failed_step": len(results), "detail": r}
                    results.append(r["result"])
                    continue
                step["args"] = [self._resolve(a, results) for a in step["args"]]
                r = self.run_task(step, check=check)
                if r.get("status") != "ok":
                    return {"status": r.get("status"), "failed_step": len(results),
                            "detail": r}
                results.append(r["result"])
            return {"status": "ok", "result": results[-1], "steps": results}
        name = task["op"]
        args = tuple(task["args"])
        if name not in self.members:
            self._log(name, args, None, "capability_gap")
            return {"status": "capability_gap", "op": name}
        if not in_domain(name, args, self.members[name]):
            self._log(name, args, None, "out_of_domain")
            return {"status": "out_of_domain", "op": name, "args": args}
        if "args_list" in task:   # fan-out handled by caller via run_fanout
            raise ValueError("use run_fanout for args_list tasks")
        vote = task.get("vote", 1)
        clones = [Clone(self.members[name]) for _ in range(vote)]
        outs = [c.run(args) for c in clones]
        result = Counter(outs).most_common(1)[0][0]
        verdict = "vote:" + "/".join(str(o) for o in outs)
        if check:
            want = members.REFERENCES[name](*args)
            verdict += "|ref:" + ("pass" if result == want else "FAIL")
            if result != want:
                self._log(name, args, result, "wrong:" + verdict,
                          clones=[c.id for c in clones])
                return {"status": "wrong", "op": name, "result": result,
                        "expected": want}
        self._log(name, args, result, verdict, clones=[c.id for c in clones])
        return {"status": "ok", "op": name, "result": result}

    def run_fanout(self, op, args_list, n_clones=4, check=False):
        """Distribute a list task across clones of one specialist."""
        if op not in self.members:
            return {"status": "capability_gap", "op": op}
        clones = [Clone(self.members[op]) for _ in range(n_clones)]
        results = [None] * len(args_list)
        for i, args in enumerate(args_list):
            c = clones[i % n_clones]
            results[i] = c.run(tuple(args))
        wrong = 0
        if check:
            ref = members.REFERENCES[op]
            wrong = sum(1 for a, r in zip(args_list, results) if ref(*a) != r)
        self._log(op, f"fanout x{len(args_list)}", f"{len(results)} results",
                  f"clones:{[c.id for c in clones]} jobs:{[c.jobs for c in clones]} wrong:{wrong}")
        return {"status": "ok", "result": results, "wrong": wrong,
                "clone_jobs": {c.id: c.jobs for c in clones}}

    def _resolve(self, a, results):
        if isinstance(a, dict) and "from" in a:
            v = results[a["from"]]
            return v[a["index"]] if "index" in a else v
        return a

    def _log(self, op, args, result, verdict, clones=None):
        self.board.append({"op": op, "args": str(args), "result": str(result),
                           "verdict": verdict, "clones": clones or []})

    def save_board(self, path):
        with open(path, "w") as f:
            for row in self.board:
                f.write(json.dumps(row) + "\n")
