"""Choose table programs using zero or one externally labeled example, then run them on fresh rows."""
import json

from .learner import EXAMPLES
from .solver import Unsupported, execute, plan, schema


PORTFOLIO = ("rules", "learned", "flat")
ALL_CODES = tuple(a + b for a in "CS" for b in "PGHL")
ARMS = ("unlabeled_committee", "constant", "portfolio", "seen_library", "all_typed")


def signature(x):
    # JSON serialization distinguishes a group name, number, null and dictionary.
    return json.dumps(x, sort_keys=True, allow_nan=False, ensure_ascii=False, separators=(",", ":"))


def qualify(request, teaching_rows, value, rows, arm, native_code=None):
    """The demonstration is a user-supplied table and answer, separate from the new rows."""
    if arm not in ARMS:
        raise ValueError(f"unsupported arm {arm}")
    if arm == "constant":
        return {"status": "answered", "value": value, "admitted": 0}
    try:
        if arm == "unlabeled_committee":
            construction_rows = rows
        else:
            construction_rows = teaching_rows
            if schema(teaching_rows) != schema(rows):
                # Column order is irrelevant in a named table.
                if [set(d) for d in schema(teaching_rows)] != [set(d) for d in schema(rows)]:
                    raise Unsupported("teaching and target schema differ")
        options = [(mode, None) for mode in PORTFOLIO]
        if native_code is not None:
            options.append(("native", native_code))
        if arm in ("seen_library", "all_typed"):
            codes = sorted(EXAMPLES) if arm == "seen_library" else ALL_CODES
            options = [("native", code) for code in codes]
        candidates = {}
        for mode, proposed in options:
            try:
                code, ops = plan(request, construction_rows, mode, proposed)
                if arm != "unlabeled_committee" and signature(execute(teaching_rows, ops)) != signature(value):
                    continue
                candidates[signature(ops)] = (code, ops)
            except Unsupported:
                continue
        if not candidates:
            raise Unsupported("no plan qualified")
        findings = {}
        for code, ops in candidates.values():
            # Every plan surviving admission must return the same target result, including tie handling.
            outcome = execute(rows, ops)
            findings[signature(outcome)] = outcome
        if len(findings) == 1:
            return {"status": "answered", "value": next(iter(findings.values())), "admitted": len(candidates),
                    "codes": sorted({c for c,_ in candidates.values()})}
        return {"status": "abstained", "value": None, "reason": "qualified plans disagree",
                "admitted": len(candidates)}
    except Unsupported as exc:
        return {"status":"abstained", "value":None, "reason":str(exc), "admitted":0}
