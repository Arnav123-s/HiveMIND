"""The surgery niche — Arnav's protocol, enforced in code.

No weight or architecture change happens any other way:
  1. TRACE    the existing architecture as it actually is.
  2. FIND     every weight responsible for the behaviour being changed
              (behaviour probes, ablation isolation — evidence, not guesses).
  3. MAP      which units/weights are responsible for what.
  4. UNTANGLE the entire model — every weight accounted for in the map.
  5. CHANGE   only then, and only what the map says is responsible.

surgical_edit() raises ProtocolError if the map is missing, if the
untangle step has not certified completeness, or if an edit tries to
touch a weight the map does not hold responsible for the target
behaviour. Each step is its own smallest specialist.
"""
import copy


class ProtocolError(Exception):
    pass


def _leaf_paths(tree, prefix=""):
    paths = []
    if isinstance(tree, dict):
        for k, v in tree.items():
            paths += _leaf_paths(v, f"{prefix}.{k}" if prefix else str(k))
    else:
        paths.append(prefix)
    return paths


def _get(tree, path):
    for part in path.split("."):
        tree = tree[part]
    return tree


def _set(tree, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        tree = tree[part]
    tree[parts[-1]] = value


# 1 ------------------------------------------------------------------ TRACE
def trace_architecture(task):
    """architecture-tracer: describe the specialist's weights as they are."""
    spec = task["specialist"]
    w = spec.weights
    return {"ok": True,
            "output": {"name": spec.name, "kind": spec.kind,
                       "leaf_paths": _leaf_paths(w),
                       "n_leaves": len(_leaf_paths(w))},
            "evidence": f"{len(_leaf_paths(w))} weight leaves traced"}


# 2 ------------------------------------------------------------------- FIND
def probe_responsibilities(task):
    """behaviour-prober: ablate one weight at a time; a weight is
    responsible for a probe if ablating it changes that probe's outcome."""
    spec, probes = task["specialist"], task["probes"]
    baseline = [spec.run(p["task"])["output"] for p in probes]
    affects = {}
    for path in _leaf_paths(spec.weights):
        saved = copy.deepcopy(_get(spec.weights, path))
        _set(spec.weights, path, 0)
        now = [spec.run(p["task"])["output"] for p in probes]
        _set(spec.weights, path, saved)
        changed = [i for i, (a, b) in enumerate(zip(baseline, now)) if a != b]
        affects[path] = changed
    return {"ok": True, "output": {"baseline": baseline, "affects": affects},
            "evidence": f"{sum(1 for v in affects.values() if v)} weight(s) move behaviour"}


# 3 -------------------------------------------------------------------- MAP
def build_map(task):
    """responsibility-mapper: trace + probe results -> the map."""
    trace, probe = task["trace"], task["probe"]
    labels = task.get("probe_labels", [])
    m = {}
    for path in trace["leaf_paths"]:
        idx = probe["affects"].get(path, [])
        m[path] = {"affects_probes": idx,
                   "affects": [labels[i] if i < len(labels) else f"probe{i}" for i in idx]}
    return {"ok": True, "output": m,
            "evidence": f"map covers {len(m)} weight(s)"}


# 4 --------------------------------------------------------------- UNTANGLE
def untangle(task):
    """wiring-untangler: the gate. Every traced weight must be in the map —
    even if its entry says 'affects nothing observed'."""
    trace, m = task["trace"], task["map"]
    unmapped = [p for p in trace["leaf_paths"] if p not in m]
    complete = not unmapped
    return {"ok": complete,
            "output": {"complete": complete, "unmapped": unmapped,
                       "total_weights": len(trace["leaf_paths"]),
                       "mapped_weights": len(m)},
            "evidence": "entire wiring accounted for" if complete
                        else f"UNMAPPED: {unmapped}"}


# 5 ----------------------------------------------------------------- CHANGE
def surgical_edit(task):
    """surgical-editor: apply an edit ONLY to map-responsible weights.

    task: {specialist, map, untangle, target_probes (indices),
           edits: {path: new_value}}
    """
    spec, m = task["specialist"], task.get("map")
    unt = task.get("untangle") or {}
    if not m:
        raise ProtocolError("step skipped: no responsibility map (steps 1-3) exists")
    if not unt.get("complete"):
        raise ProtocolError("step skipped: model not untangled (step 4) — map incomplete")
    targets = set(task["target_probes"])
    diffs = {}
    for path, value in task["edits"].items():
        responsible = set(m.get(path, {}).get("affects_probes", []))
        if not (responsible & targets):
            raise ProtocolError(
                f"edit refused: {path} is not responsible for the target behaviour "
                f"(map says it affects probes {sorted(responsible)})")
        old = copy.deepcopy(_get(spec.weights, path))
        _set(spec.weights, path, value)
        diffs[path] = (old, value)
    return {"ok": True, "output": diffs,
            "evidence": f"{len(diffs)} weight(s) changed, all map-responsible"}


def run_protocol(specialist, probes, probe_labels, target_probes, edits):
    """The whole protocol in order, as the surgery niche runs it."""
    trace = trace_architecture({"specialist": specialist})["output"]
    probe = probe_responsibilities({"specialist": specialist, "probes": probes})["output"]
    m = build_map({"trace": trace, "probe": probe, "probe_labels": probe_labels})["output"]
    unt = untangle({"trace": trace, "map": m})["output"]
    diffs = surgical_edit({"specialist": specialist, "map": m, "untangle": unt,
                           "target_probes": target_probes, "edits": edits})["output"]
    return {"trace": trace, "probe": probe, "map": m, "untangle": unt, "diffs": diffs}
