"""Check whether a corroborated edit can distinguish an already-qualified worker."""
from itertools import islice
import json

from .campaign import fingerprint
from .repair_learning import learned_variants


MAX_RIVALS = 2


class _Meter:
    def __init__(self, guest, receipt):
        self.guest = guest
        self.receipt = receipt

    def run(self, source, inputs, **options):
        self.receipt["guest_executions"] += 1
        self.receipt["guest_inputs"] += len(inputs)
        rows, fuel, seconds = self.guest.run(source, inputs, **options)
        # An alternate guest or malformed guest reply can contain non-finite
        # numbers. A failed row cannot become agreement or a diagnostic witness.
        checked = []
        for row in rows:
            if "value" in row:
                try:
                    json.dumps(row["value"], allow_nan=False)
                except (TypeError, ValueError, OverflowError, RecursionError):
                    row = {"error": "Guest returned a value outside the JSON format."}
            checked.append(row)
        return checked, fuel, seconds


def _evidence(value):
    """Keep ordinary answers intact and avoid duplicating arbitrarily large exports."""
    text = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    if len(text) <= 2048:
        return value
    return {"preview": text[:1024], "json_characters": len(text), "truncated": True}


def assess(source, program, policy, spec, guest, *, wrap, limit=2):
    """Stage alternatives to a public- and qualification-passing primary, without admission.

    The caller has already checked the exact primary program. The return value is
    (receipt, staged_primary_jobs). On ambiguity or an incomplete comparison the
    caller must withhold all job files. Only agreement returns reusable staged rows.
    """
    from .work import check, shared_results, validation_set_id

    if type(limit) is not int or not 0 <= limit <= MAX_RIVALS:
        raise ValueError("challenge limit must be an integer between zero and two")
    result = {"status": "unopposed", "reason": "No checked rival qualified.", "limit": limit,
              "rivals": [], "guest_executions": 0, "guest_inputs": 0}
    if not limit:
        return result, None
    public = spec.get("examples", [])
    if not public or not validation_set_id(spec) or not isinstance(source, str) or wrap(source) != program:
        result.update(status="inconclusive", reason="The challenge needs the exact primary and disjoint public and qualification inputs.")
        return result, None

    meter = _Meter(guest, result)
    validation = spec["validation"]
    formats = spec.get("compare")
    qualified = [{"source": program, "digest": fingerprint(program)}]
    seen = {qualified[0]["digest"]}
    # Candidate generation receives only the source and validated rule bank. The
    # ranking cannot see examples, private inputs, expected outputs or rival scores.
    for rival in islice(learned_variants(source, policy), limit):
        candidate = wrap(rival["source"])
        digest = fingerprint(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        passed, _ = check(meter, candidate, public, formats, explain=False)
        record = {"digest": digest, "rule_id": rival["rule_id"], "support": rival["support"],
                  "public": passed, "validated": None}
        result["rivals"].append(record)
        if passed == len(public):
            record["validated"], _ = check(meter, candidate, validation, formats, explain=False)
            if record["validated"] == len(validation):
                qualified.append({"source": candidate, "digest": digest})
    if len(qualified) == 1:
        return result, None

    def witness(job, reference, primary_value, rival_value, competing_rows):
        def expanded_input(rows):
            if not job.get("from_job"):
                return job["input"]
            prior = {row["id"]: row["value"] for row in rows if "value" in row}
            return {**job["input"], **{field: prior[parent] for field, parent in job["from_job"].items()}}

        primary_input = expanded_input(reference)
        rival_input = expanded_input(competing_rows)
        details = {"job": job["id"], "input": _evidence(primary_input),
                   "answers": [_evidence(primary_value), _evidence(rival_value)]}
        # Two upstream records can compare equal as JSON/CSV yet contain different
        # raw strings. Keep the second actual input when a downstream job observes it.
        if json.dumps(primary_input, sort_keys=True) != json.dumps(rival_input, sort_keys=True):
            details["rival_input"] = _evidence(rival_input)
        result["witness"] = details

    staged, conflict = shared_results(qualified, meter, spec.get("jobs", []), formats, on_difference=witness)
    if conflict:
        status = "ambiguous" if "witness" in result else "inconclusive"
        result.update(status=status, reason=conflict + " Supply a distinguishing input with the expected answer.")
        return result, None
    result.update(status="agreement", reason="All qualified alternatives agreed on these jobs.")
    return result, staged
