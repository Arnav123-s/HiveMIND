"""Dream generators for the text/code niches (final-product item 2).

The dream engine (dream.py) shipped with one generator: bug-pattern.
This module adds generators for the two niches whose v2-aware
diagnosis shows preventive drift — contract-judgment and commit-type
(gap-move and secret-line diagnose HOLD; no generator is built for
them, deliberately — a hold respected is a correct outcome).

Same discipline as dream_gen.py:

  * parameterized families in three difficulty bands;
  * labels PROVED by a checker before any item may be trained on —
    contract: by EXECUTION (each variant's behavioral signature over
    None / [] / list probes must equal its class signature exactly);
    commit: by SIGNAL DOMINANCE (the item's earliest strong class
    signal must be its own class, with no competing conventional
    prefix anywhere — ambiguous items are dropped, never trained);
  * every kept case in TWO views (contract: identifier-renamed view,
    itself signature-verified; commit: the paired alternate frame);
  * train / screen / confirm pools come from structurally DISJOINT
    family sets, so the screen measures new structures and the
    confirm set is a fresh one-shot judge per cycle.
"""
from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Tuple

from .dream_gen import _load_fn, renamed_view

BANDS = (1, 2, 3)

# ============================================================ contract
CONTRACT_CLASSES = ["ok", "mutates-input", "no-empty-guard", "no-none-guard"]
# behavioral signature: (raises_on_none, raises_on_empty, mutates_input)
_CLASS_SIGNATURE = {
    "ok": (False, False, False),
    "mutates-input": (False, False, True),
    "no-empty-guard": (False, True, False),
    "no-none-guard": (True, False, False),
}
_CONTRACT_NAMES = [("normalize", "records"), ("tally", "scores"),
                   ("inspect", "rows"), ("grade", "marks"),
                   ("sift", "vals"), ("rank", "points")]


def contract_signature(code: str) -> Optional[Tuple[bool, bool, bool]]:
    """Execute the snippet's function on the three probes and read
    its class off its behavior. None if it does not load or crashes
    on the ordinary list probe (an unverifiable dream)."""
    fn = _load_fn(code)
    if fn is None:
        return None

    def raises(arg) -> Optional[bool]:
        try:
            fn(arg)
            return False
        except Exception:  # noqa: BLE001 - a raise IS the signal
            return True

    r_none = raises(None)
    r_empty = raises([])
    probe = [3, 1, 2]
    try:
        fn(probe)
    except Exception:  # noqa: BLE001
        return None
    mutates = probe != [3, 1, 2]
    return (bool(r_none), bool(r_empty), mutates)


def _cv(ok, mut, noempty, nonone):
    return {"ok": ok, "mutates-input": mut, "no-empty-guard": noempty,
            "no-none-guard": nonone}


def _sub(code: str, fn: str, arg: str) -> str:
    return code.replace("FN", fn).replace("ARG", arg)


# ---- contract train families (per band: kind -> variants) --------
def _ct_b1(kind, fn, arg):
    if kind == "extremum":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    if not ARG:\n        return 0\n    return max(ARG)",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.sort()\n    return ARG[-1]",
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[0] + ARG[-1]",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return 0\n    return sum(ARG)")
    if kind == "scale":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return []\n    return [v * 3 for v in ARG]",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    for i in range(len(ARG)):\n        ARG[i] = ARG[i] * 3\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[-1] * 3",
            f"def FN(ARG):\n    return [v * 3 for v in ARG]")
    return _cv(  # count
        f"def FN(ARG):\n    total = 0\n    for v in ARG or []:\n        total += v\n    return total",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.append(len(ARG))\n    return ARG",
        f"def FN(ARG):\n    if ARG is None:\n        return -1\n    return ARG[0] - ARG[-1] if len(ARG) > 1 else ARG[0]",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return -1\n    return ARG[-1] - ARG[0]")


def _ct_b2(kind, fn, arg):
    if kind == "pairsum":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    total = 0\n    for i in range(len(ARG) - 1):\n        total += ARG[i] + ARG[i + 1]\n    return total",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.reverse()\n    total = 0\n    for v in ARG:\n        total += v\n    return total",
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[0] + ARG[1]",
            f"def FN(ARG):\n    total = 0\n    for v in ARG:\n        total += v\n    return total")
    if kind == "collect":
        return _cv(
            f"def FN(ARG):\n    out = []\n    for v in ARG or []:\n        if v > 1:\n            out.append(v)\n    return out",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.extend([0])\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return []\n    first = ARG[0]\n    return [first, first]",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return []\n    return [v for v in ARG if v > 1]")
    return _cv(  # running
        f"def FN(ARG):\n    if ARG is None:\n        return 0\n    best = None\n    for v in ARG:\n        if best is None or v > best:\n            best = v\n    return best or 0",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG[0] = ARG[0] * 10\n    return ARG",
        f"def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[-1] * 2",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return 0\n    return max(ARG) - min(ARG)")


def _ct_b3(kind, fn, arg):
    if kind == "report":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return (0, 0)\n    count = 0\n    total = 0\n    for v in ARG:\n        count += 1\n        total += v\n    note = count * 2\n    return (count, total)",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    total = 0\n    for v in ARG:\n        total += v\n    ARG.append(total)\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return (0, 0)\n    head = ARG[0]\n    tail = ARG[-1]\n    return (head, tail)",
            f"def FN(ARG):\n    count = 0\n    for v in ARG:\n        count += 1\n    if count == 0:\n        return (0, 0)\n    return (count, sum(ARG))")
    if kind == "twopass":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return []\n    work = list(ARG)\n    out = []\n    for v in work:\n        out.append(v + 1)\n    return out",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    for i in range(len(ARG)):\n        ARG[i] = ARG[i] + 1\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return []\n    mid = ARG[len(ARG) // 2]\n    return [mid]",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return []\n    return [v + 1 for v in ARG]")
    return _cv(  # earlyexit
        f"def FN(ARG):\n    if ARG is None:\n        return -1\n    for i, v in enumerate(ARG):\n        if v < 0:\n            return i\n    return len(ARG)",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    while len(ARG) > 2:\n        ARG.pop()\n    return ARG",
        f"def FN(ARG):\n    if ARG is None:\n        return -1\n    return ARG[0] + 10",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return -1\n    for i, v in enumerate(ARG):\n        if v < 0:\n            return i\n    return len(ARG)")


# ---- contract screen families (distinct idioms, never trained) --
def _cs_b1(kind, fn, arg):
    if kind == "tryidx":
        return _cv(
            f"def FN(ARG):\n    try:\n        return ARG[0]\n    except (IndexError, TypeError):\n        return 0",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.insert(0, ARG[-1])\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    try:\n        return ARG[0]\n    except TypeError:\n        return 0",
            f"def FN(ARG):\n    try:\n        n = len(ARG)\n    except TypeError:\n        raise\n    if n == 0:\n        return 0\n    return ARG[0]")
    return _cv(  # sortedcopy
        f"def FN(ARG):\n    return sorted(ARG) if ARG is not None else []",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.sort(reverse=True)\n    return ARG",
        f"def FN(ARG):\n    if ARG is None:\n        return []\n    s = sorted(ARG)\n    return s[0]",
        f"def FN(ARG):\n    s = sorted(ARG)\n    if len(s) == 0:\n        return []\n    return s")


def _cs_b2(kind, fn, arg):
    if kind == "whilescan":
        return _cv(
            f"def FN(ARG):\n    i = 0\n    total = 0\n    vals = ARG or []\n    while i < len(vals):\n        total += vals[i]\n        i += 1\n    return total",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    i = 0\n    while i < len(ARG):\n        ARG[i] = ARG[i] + 5\n        i += 1\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    first = ARG[0]\n    i = 0\n    while i < len(ARG) and ARG[i] < 10:\n        i += 1\n    return i",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return 0\n    i = 0\n    total = 0\n    while i < len(ARG):\n        total += ARG[i]\n        i += 1\n    return total")
    return _cv(  # minmax
        f"def FN(ARG):\n    if ARG is None or len(ARG) == 0:\n        return (0, 0)\n    return (min(ARG), max(ARG))",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.remove(max(ARG))\n    return ARG",
        f"def FN(ARG):\n    if ARG is None:\n        return (0, 0)\n    return (min(ARG), max(ARG))",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return (0, 0)\n    return (min(ARG), max(ARG))")


def _cs_b3(kind, fn, arg):
    if kind == "nestedguard":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    if len(ARG) == 0:\n        return 0\n    total = 0\n    for row in ARG:\n        if row:\n            total += row\n    return total",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    for i in range(len(ARG)):\n        if ARG[i] is not None:\n            ARG[i] = 0\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return 0\n    total = ARG[0]\n    for v in ARG[1:]:\n        total += v\n    return total",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return 0\n    total = 0\n    for v in ARG:\n        if v is not None:\n            total += v\n    return total")
    return _cv(  # zipwalk
        f"def FN(ARG):\n    if ARG is None:\n        return 0\n    total = 0\n    for a, b in zip(ARG, ARG[1:]):\n        total += abs(a - b)\n    return total",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG[:] = ARG[::-1]\n    return ARG",
        f"def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[0] - ARG[-1] + ARG[1]",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return 0\n    total = 0\n    for a, b in zip(ARG, ARG[1:]):\n        total += abs(a - b)\n    return total")


# ---- contract confirm families (fresh judge idioms) -------------
def _cc_b1(kind, fn, arg):
    if kind == "dictbuild":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return {{}}\n    return {{v: v + 1 for v in ARG}}",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.clear()\n    ARG.append(1)\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return {{}}\n    return {{ARG[0]: len(ARG)}}",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return {{}}\n    return {{v: v for v in ARG}}")
    return _cv(  # medianish
        f"def FN(ARG):\n    if ARG is None:\n        return 0\n    if len(ARG) == 0:\n        return 0\n    s = sorted(ARG)\n    return s[len(s) // 2]",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.sort()\n    return ARG[len(ARG) // 2]",
        f"def FN(ARG):\n    if ARG is None:\n        return 0\n    s = sorted(ARG)\n    return s[len(s) // 2]",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return 0\n    s = sorted(ARG)\n    return s[len(s) // 2]")


def _cc_b2(kind, fn, arg):
    if kind == "enumjoin":
        return _cv(
            f"def FN(ARG):\n    parts = []\n    for i, v in enumerate(ARG or []):\n        parts.append((i, v))\n    return parts",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    for i in range(len(ARG)):\n        ARG[i] = (i, ARG[i])\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return []\n    return [(0, ARG[0]), (1, ARG[1])]",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return []\n    return [(i, v) for i, v in enumerate(ARG)]")
    return _cv(  # groupcount
        f"def FN(ARG):\n    seen = {{}}\n    for v in ARG or []:\n        seen[v] = seen.get(v, 0) + 1\n    return seen",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.append(ARG[0])\n    seen = {{}}\n    for v in ARG:\n        seen[v] = seen.get(v, 0) + 1\n    return seen",
        f"def FN(ARG):\n    if ARG is None:\n        return {{}}\n    return {{ARG[0]: ARG.count(ARG[0])}}",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return {{}}\n    seen = {{}}\n    for v in ARG:\n        seen[v] = seen.get(v, 0) + 1\n    return seen")


def _cc_b3(kind, fn, arg):
    if kind == "windowstate":
        return _cv(
            f"def FN(ARG):\n    if ARG is None:\n        return []\n    out = []\n    prev = None\n    for v in ARG:\n        out.append(v if prev is None else v - prev)\n        prev = v\n    return out",
            f"def FN(ARG):\n    if not ARG:\n        return ARG\n    for i in range(1, len(ARG)):\n        ARG[i] = ARG[i] - ARG[i - 1]\n    return ARG",
            f"def FN(ARG):\n    if ARG is None:\n        return []\n    return [ARG[1] - ARG[0], ARG[2] - ARG[1]]",
            f"def FN(ARG):\n    if len(ARG) == 0:\n        return []\n    out = [ARG[0]]\n    for i in range(1, len(ARG)):\n        out.append(ARG[i] - ARG[i - 1])\n    return out")
    return _cv(  # classify
        f"def FN(ARG):\n    if ARG is None:\n        return 'none'\n    if len(ARG) == 0:\n        return 'empty'\n    return 'many' if len(ARG) > 2 else 'few'",
        f"def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.sort()\n    return 'sorted'",
        f"def FN(ARG):\n    if ARG is None:\n        return 'none'\n    return ARG[0]",
        f"def FN(ARG):\n    if len(ARG) == 0:\n        return 'empty'\n    return 'many' if len(ARG) > 2 else 'few'")


_CT_TRAIN = {1: ["extremum", "scale", "count"], 2: ["pairsum", "collect", "running"],
            3: ["report", "twopass", "earlyexit"]}
_CT_SCREEN = {1: ["tryidx", "sortedcopy"], 2: ["whilescan", "minmax"],
              3: ["nestedguard", "zipwalk"]}
_CT_CONFIRM = {1: ["dictbuild", "medianish"], 2: ["enumjoin", "groupcount"],
               3: ["windowstate", "classify"]}
_CT_BUILDERS = {}
for _b, _fn in ((1, _ct_b1), (2, _ct_b2), (3, _ct_b3)):
    for _k in _CT_TRAIN[_b]:
        _CT_BUILDERS[("train", _b, _k)] = (lambda f, k: lambda fn, arg: f(k, fn, arg))(_fn, _k)
for _b, _fn in ((1, _cs_b1), (2, _cs_b2), (3, _cs_b3)):
    for _k in _CT_SCREEN[_b]:
        _CT_BUILDERS[("screen", _b, _k)] = (lambda f, k: lambda fn, arg: f(k, fn, arg))(_fn, _k)
for _b, _fn in ((1, _cc_b1), (2, _cc_b2), (3, _cc_b3)):
    for _k in _CT_CONFIRM[_b]:
        _CT_BUILDERS[("confirm", _b, _k)] = (lambda f, k: lambda fn, arg: f(k, fn, arg))(_fn, _k)
_CT_KINDS = {"train": _CT_TRAIN, "screen": _CT_SCREEN, "confirm": _CT_CONFIRM}


def _contract_pool(pool: str, band_counts: Dict[int, int], seed: int,
                   group_prefix: str):
    items: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"families": 0, "drops": {}}
    rng = random.Random(seed)
    for band, count in band_counts.items():
        kinds = _CT_KINDS[pool][band]
        for i in range(count):
            kind = kinds[i % len(kinds)]
            fn_name, arg = _CONTRACT_NAMES[rng.randrange(len(_CONTRACT_NAMES))]
            variants = _CT_BUILDERS[(pool, band, kind)](fn_name, arg)
            stats["families"] += 1
            fam_id = f"{group_prefix}:{pool}-b{band}-{kind}-{i}"
            for cls, code in variants.items():
                sig = contract_signature(code)
                if sig != _CLASS_SIGNATURE[cls]:
                    key = f"signature_mismatch_{cls}"
                    stats["drops"][key] = stats["drops"].get(key, 0) + 1
                    continue
                items.append({"text": code, "label": cls, "group": fam_id,
                              "band": band, "family": kind})
                view = renamed_view(code)
                if view is not None and view != code \
                        and contract_signature(view) == sig:
                    items.append({"text": view, "label": cls,
                                  "group": fam_id, "band": band,
                                  "family": kind, "view": 2})
                else:
                    stats["drops"]["view_failed_verify"] = \
                        stats["drops"].get("view_failed_verify", 0) + 1
    stats["items"] = len(items)
    return items, stats


def contract_gen_pool(band_counts, seed, group_prefix):
    return _contract_pool("train", band_counts, seed, group_prefix)


def contract_gen_screen_pool(band_counts, seed, group_prefix="screen"):
    return _contract_pool("screen", band_counts, seed, group_prefix)


def contract_gen_confirm_pool(band_counts, seed, group_prefix="confirm"):
    return _contract_pool("confirm", band_counts, seed, group_prefix)


# ============================================================ commit
COMMIT_CLASSES = ["feat", "fix", "docs", "refactor", "test", "chore"]
_COMMIT_VERBS = {
    "feat": ["add", "implement", "introduce", "create", "launch", "enable",
             "deliver", "expose", "support"],
    "fix": ["fix", "correct", "repair", "patch", "mend", "resolve",
            "squash", "address"],
    "docs": ["document", "describe", "clarify", "annotate", "spell out",
             "write up"],
    "refactor": ["rename", "extract", "simplify", "restructure",
                 "consolidate", "deduplicate", "decouple", "streamline"],
    "test": ["test", "cover", "verify", "assert", "exercise", "snapshot"],
    "chore": ["bump", "upgrade", "pin", "refresh", "renew", "rotate",
              "prune", "archive"],
}
_COMMIT_OBJECTS = ["the export wizard", "the onboarding flow",
                   "the audit log viewer", "the token refresher",
                   "the image resizer", "the digest mailer",
                   "the feature flag client", "the session store",
                   "the pdf renderer", "the webhook signer",
                   "the rate limiter", "the theme picker"]
_COMMIT_SCOPES = ["parser", "api", "ui", "billing", "core", "cli",
                  "reports", "auth"]
_COMMIT_TAILS = ["for the reports page", "behind a flag", "in the admin panel",
                 "for new users", "across the dashboard", "in the settings flow"]
_COMMIT_WHY = ["so users can archive reports", "before the release freeze",
               "for the new dashboard", "so support tickets drop",
               "ahead of the audit", "for the mobile team"]
_ALL_VERBS = sorted({v for vs in _COMMIT_VERBS.values() for v in vs},
                    key=len, reverse=True)
_VERB_CLASS = {v: c for c, vs in _COMMIT_VERBS.items() for v in vs}
_PREFIX_RE = re.compile(r"^(feat|fix|docs|refactor|test|chore)(\([a-z]+\))?:",
                        re.IGNORECASE)


def verify_commit_item(text: str, cls: str) -> Optional[str]:
    """Signal-dominance checker: returns None to keep, else the drop
    reason. A kept item's class is PROVED by its surface: its own
    conventional prefix (if any) agrees, no competing prefix exists,
    and the earliest head verb in the message belongs to its class."""
    low = text.lower()
    for m in _PREFIX_RE.finditer(low):
        if m.group(1).lower() != cls:
            return f"competing prefix {m.group(1)}"
    hits = []
    for verb in _ALL_VERBS:
        for m in re.finditer(rf"\b{re.escape(verb)}\b", low):
            hits.append((m.start(), verb))
    if not hits:
        return "no head verb signal"
    hits.sort()
    first_cls = _VERB_CLASS[hits[0][1]]
    if first_cls != cls:
        return f"earliest head verb '{hits[0][1]}' belongs to {first_cls}"
    return None


def _commit_frames(band: int, cls: str, verb: str, obj: str,
                   scope: str, tail: str, why: str) -> Tuple[str, str]:
    """(view1, view2): two surfaces of one message, band-shaped."""
    if band == 1:
        return (f"{verb} {obj}", f"{verb} {obj} {tail}")
    if band == 2:
        return (f"{cls}: {verb} {obj}", f"{cls}({scope}): {verb} {obj}")
    return (f"{verb} {obj} {why}", f"{cls}: {verb} {obj} {why}")


def _commit_frames_screen(band: int, cls: str, verb: str, obj: str,
                          scope: str, tail: str, why: str) -> Tuple[str, str]:
    """Screen-only surfaces: suffix-tagged and scope-headed forms
    the train frames never produce."""
    if band == 1:
        return (f"{verb} {obj} ({cls})", f"{scope} work: {verb} {obj}")
    if band == 2:
        return (f"{verb} {obj} [{cls}]", f"{cls} work: {verb} {obj} {tail}")
    return (f"{verb} {obj} ({cls}) {why}", f"{scope} work: {verb} {obj} {why}")


def _commit_frames_confirm(band: int, cls: str, verb: str, obj: str,
                           scope: str, tail: str, why: str) -> Tuple[str, str]:
    """Confirm-only surfaces: full-sentence forms."""
    if band == 1:
        return (f"this change will {verb} {obj}", f"please {verb} {obj}")
    if band == 2:
        return (f"this change will {verb} {obj} {tail}",
                f"please {verb} {obj} {tail}")
    return (f"this change will {verb} {obj} {why}",
            f"please {verb} {obj} {why}")


def _commit_pool(band_counts: Dict[int, int], seed: int,
                 group_prefix: str, verb_offset: int = 0,
                 frames=_commit_frames):
    items: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"families": 0, "drops": {}}
    rng = random.Random(seed)
    for band, count in band_counts.items():
        for i in range(count):
            cls = COMMIT_CLASSES[(i + band) % len(COMMIT_CLASSES)]
            verbs = _COMMIT_VERBS[cls]
            verb = verbs[(i + verb_offset) % len(verbs)]
            obj = _COMMIT_OBJECTS[rng.randrange(len(_COMMIT_OBJECTS))]
            scope = _COMMIT_SCOPES[rng.randrange(len(_COMMIT_SCOPES))]
            tail = _COMMIT_TAILS[rng.randrange(len(_COMMIT_TAILS))]
            why = _COMMIT_WHY[rng.randrange(len(_COMMIT_WHY))]
            v1, v2 = frames(band, cls, verb, obj, scope, tail, why)
            stats["families"] += 1
            gid = f"{group_prefix}:b{band}:{cls}:{verb}:{i}"
            kept_any = False
            for view, text in ((1, v1), (2, v2)):
                reason = verify_commit_item(text, cls)
                if reason is not None:
                    key = f"checker_{reason.split(' ')[0]}"
                    stats["drops"][key] = stats["drops"].get(key, 0) + 1
                    continue
                items.append({"text": text, "label": cls, "group": gid,
                              "band": band, "family": f"{cls}-{verb}",
                              **({"view": 2} if view == 2 else {})})
                kept_any = True
            if not kept_any:
                stats["drops"]["family_dropped"] = \
                    stats["drops"].get("family_dropped", 0) + 1
    stats["items"] = len(items)
    return items, stats


def commit_gen_pool(band_counts, seed, group_prefix):
    return _commit_pool(band_counts, seed, group_prefix, verb_offset=0)


def commit_gen_screen_pool(band_counts, seed, group_prefix="screen"):
    return _commit_pool(band_counts, seed, group_prefix, verb_offset=3,
                        frames=_commit_frames_screen)


def commit_gen_confirm_pool(band_counts, seed, group_prefix="confirm"):
    return _commit_pool(band_counts, seed, group_prefix, verb_offset=5,
                        frames=_commit_frames_confirm)


# ------------------------------------------------------------ registry
def niche_generators() -> Dict[str, Dict[str, Any]]:
    """subject_id -> generator hooks + featurization mode. Only the
    drift-diagnosed niches appear; anything else fail-closes in the
    executor (a HOLD subject gets no generator and no cycle)."""
    return {
        "contract-judgment-model": {
            "fmode": "code",
            "gen_pool": contract_gen_pool,
            "gen_screen_pool": contract_gen_screen_pool,
            "gen_confirm_pool": contract_gen_confirm_pool,
        },
        "commit-type-model": {
            "fmode": "words",
            "gen_pool": commit_gen_pool,
            "gen_screen_pool": commit_gen_screen_pool,
            "gen_confirm_pool": commit_gen_confirm_pool,
        },
    }
