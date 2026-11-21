"""Bounded practice replay from the last accepted body's own individually graded programs."""
from collections import defaultdict
from hashlib import sha256
import json
import os
import re


def ratio():
    flag = os.environ.get("HIVE_SELF_REPLAY", "0")
    if flag == "0":
        return 0
    if flag != "1" or os.environ.get("HIVE_SELF_REPLAY_RATIO", "2") not in ("2", "3", "4"):
        raise ValueError("HIVE_SELF_REPLAY must be 0 or 1 and HIVE_SELF_REPLAY_RATIO must be 2, 3 or 4")
    return int(os.environ.get("HIVE_SELF_REPLAY_RATIO", "2"))


def question(text):
    return " ".join(str(text or "").casefold().split())


def generation(name):
    return int(name[1:]) if isinstance(name, str) and re.fullmatch(r"g\d{1,6}", name) else -1


def verified(run, member, who):
    """Exact file number and actor on the independently graded answer. Conflicting records supply no proof."""
    if not who:
        return False
    try:
        found = [v for v in json.loads((run / "exam.json").read_text())["members"]
                 if isinstance(v, dict) and type(v.get("member")) is int and v["member"] == member]
    except (OSError, KeyError, ValueError, TypeError):
        return False
    return len(found) == 1 and found[0].get("who") == who and found[0].get("ok") is True


def select(rows, body, base, gen, exclude, limit=400):
    """One row per normalized question, interleaved by kind. Return indices into the original rows."""
    from training import kinds
    reserved = {kind for maker in kinds.HELD_OUT for kind in kinds.written(maker)}
    now = generation(gen)
    previous = body.get("generation")
    if base != body.get("dna") or type(previous) is not int or not 0 < previous < now:
        return set()
    actors = {base + "+" + c for c in [*body.get("cells", []), body.get("trunk")] if isinstance(c, str) and c}
    groups, candidates = defaultdict(list), []
    for i, r in enumerate(rows):
        seed, q = r.get("seed"), question(r.get("task"))
        # Legacy rows have no independent-grade bit. Only a non-agreeing positive could have
        # come from grow.taught's individually graded path. Explicit new evidence takes precedence.
        legacy = type(r.get("member")) is int and r["member"] > 0 and r.get("agreed") is False
        proven = r.get("verified_member", legacy) is True
        if (not proven or not 0 < generation(r.get("gen")) < now or r.get("who") not in actors
                or not q or q in exclude or type(seed) is not int
                or not (10_000_000 <= seed < 20_000_000 or 30_000_000 <= seed < 40_000_000)
                or r.get("type") not in ("first", "fix") or not r.get("kind") or r["kind"] in reserved
                or r.get("maker") in kinds.HELD_OUT
                or not re.fullmatch(r"```python\s*\n.+?\n```", str(r.get("output", "")).strip(), re.S)):
            continue
        key = sha256(json.dumps([q, r["output"], r["who"], r["type"], r.get("messages")],
                                sort_keys=True).encode()).digest()
        candidates.append((key, q, r["kind"], i))
    seen = set()
    for _, q, kind, i in sorted(candidates):
        if q not in seen:
            seen.add(q)
            groups[kind].append(i)
    ordered = sorted((pos, kind, i) for kind, indices in groups.items() for pos, i in enumerate(indices))
    return {i for _, _, i in ordered[:limit]}


class Schedule:
    """Count completed optimizer inputs. If a source runs out, use the ordinary bounded Study."""
    def __init__(self, target, tags, replay, fresh):
        self.target = target
        self.replay, self.fresh = set(replay) & set(tags), set(fresh) & set(tags)
        self.passes = dict(fresh=0, replay=0, other=0)
        self.tokens = dict.fromkeys(self.passes, 0)
        self.unique = {k: set() for k in self.passes}
        self.fallbacks = 0
        self.status = "active" if self.fresh and self.replay else "no fresh rows" if not self.fresh else "no eligible replay"

    def pick(self, study):
        if self.status == "active":
            groups = self.replay if self.passes["fresh"] >= self.target * (self.passes["replay"] + 1) else self.fresh
            got = study.pick(groups)
            if got is not None:
                return got
            self.fallbacks += 1
        return study.pick()

    def learned(self, tag, idx, tokens):
        bucket = "fresh" if tag in self.fresh else "replay" if tag in self.replay else "other"
        self.passes[bucket] += 1
        self.tokens[bucket] += tokens
        self.unique[bucket].add(idx)

    def report(self):
        return {"fresh_per_replay_target": self.target, "status": self.status, "passes": self.passes,
                "answer_tokens": self.tokens, "unique_rows": {k: len(v) for k, v in self.unique.items()},
                "fallback_picks": self.fallbacks}
