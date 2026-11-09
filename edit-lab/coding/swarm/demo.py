"""End-to-end demonstration. Run from the coding/ directory:

    python3 -m swarm.demo

Four episodes, no human in any loop:
  A. the fix pipeline: plan -> run -> diagnose -> patch -> re-run ->
     review -> save -> compliance gate (instruction fidelity scored)
  B. growth: a defective trainable specialist is harvested/trained,
     verified held-out, adopted only because it wins, cloned, socialized
  C. surgery: the same defect class repaired by the protocol —
     trace, find, map, untangle, then edit only what the map indicts;
     two protocol violations are attempted and refused
  D. interface: a local constructed backend answers through the chat
     contract; the coder role's binding chain escalates (local model
     unloaded -> API key absent) and the misses land on the board

Development method (Arnav): the optimizer verifies each specialist on
probes before marking it running-alone; the marks print at the end.
Phase 2: the field-coverage specialists (PLAN.md section 15) are
verified by swarm.coverage_check's probes, imported below — same
evidence standard, one probed job at a time.
"""
import tempfile
from pathlib import Path

from . import interface
from .board import Board
from .coverage_check import run_probes
from .meta import KeywordClassifier
from .niches import build_swarm, run_fix_pipeline, tree_summary
from .surgeon import ProtocolError, run_protocol, surgical_edit

BUGGY = '''def insertion_sort(a):
    a = list(a)
    for i in range(1, len(a) - 1):
        x = a[i]; j = i - 1
        while j >= 0 and a[j] > x:
            a[j + 1] = a[j]; j -= 1
        a[j + 1] = x
    return a

for a in [[5, 2, 9, 1, 7], [3, 3, 1], [4], [9, 8, 7, 6]]:
    print(insertion_sort(a))
'''
EXPECTED = ["[1, 2, 5, 7, 9]", "[1, 3, 3]", "[4]", "[6, 7, 8, 9]"]
INSTRUCTION = ("Fix the insertion sort program so it prints the sorted lists, "
               "one result per line. Save the fixed program as fixed_sort.py.")


def mark(reg, names):
    for n in names:
        reg.get(n).dev_status = "running-alone"


def main():
    board = Board()
    reg = build_swarm(board)
    lines, total = tree_summary(reg)
    print(f"== niche tree: {total} specialists (incl. {sum(1 for s in reg.all() if s.kind == 'coordinator')} niche coordinators)")
    for l in lines:
        print("  " + l)

    # ---- optimizer verification probes (development method) -------------
    probes_ok = (
        reg.get("output-differ").run({"expected": ["a"], "actual": "a"})["ok"]
        and not reg.get("output-differ").run({"expected": ["a"], "actual": "b"})["ok"]
        and reg.get("syntax-checker").run({"code": "x = 1"})["ok"]
        and reg.get("traceback-classifier").run({"stderr": "NameError: name 'x' is not defined"})["output"] == "NameError"
        and reg.get("dependency-orderer").run({"deps": {"b": ["a"], "a": []}})["output"] == ["a", "b"])
    assert probes_ok, "constructed-specialist probes failed"
    mark(reg, ["output-differ", "syntax-checker", "traceback-classifier", "dependency-orderer",
               "step-splitter", "acceptance-writer", "test-layout-planner", "test-runner",
               "bug-pattern-matcher", "patch-applier", "sanity-checker", "contract-checker",
               "file-writer", "artifact-collector", "result-assembler", "instruction-splitter",
               "literal-checker", "fidelity-scorer", "code-extractor", "exit-checker",
               "file-checker", "probe-generator", "error-line-pointer"])
    print("== optimizer probes passed; exercised specialists marked running-alone")

    # ---- phase-2 coverage probes (field niches, PLAN section 15) --------
    verified, failures = run_probes(reg)
    assert not failures, f"coverage probes failed: {failures[:3]}"
    mark(reg, verified)
    print(f"== phase-2 coverage: {len(verified)} field specialists verified "
          f"running-alone (swarm.coverage_check probes)")

    # ---- A. the fix pipeline, unattended --------------------------------
    wd = Path(tempfile.mkdtemp(prefix="swarm_demo_"))
    res = run_fix_pipeline(reg, board, INSTRUCTION, BUGGY,
                           {"kind": "stdout_lines_equals", "lines": EXPECTED},
                           "fixed_sort.py", wd)
    print(f"A. pipeline: ok={res['ok']} fidelity={res['fidelity']} gates={res['gates']}")
    print(f"   final stdout: {res['stdout'].strip().splitlines()}")
    assert res["ok"] and res["fidelity"] == 1.0
    mark(reg, ["gap-classifier"])  # placeholder replaced below; classifier dev handled in B

    # ---- B. growth: harvest -> train -> verify -> adopt -> socialize ----
    clf = reg.get("gap-classifier")
    clf.weights = {"keywords": {"invalid": {"TypeError": 3, "ValueError": 1},
                                "index": {"IndexError": 3}, "name": {"NameError": 3}}}
    probes = ([{"text": t, "label": "ValueError"} for t in
               ["ValueError: invalid literal for int() with base 10: 'abc'",
                "ValueError: invalid literal for int() with base 10: 'x9'"]] +
              [{"text": "IndexError: list index out of range", "label": "IndexError"},
               {"text": "NameError: name 'resutl' is not defined", "label": "NameError"}])
    before = sum(clf.run(p)["output"] == p["label"] for p in probes) / len(probes)
    reg.get("learner").run({"niche": "meta", "what": "gap-classifier misses ValueError probes",
                            "gap": "no-keyword-votes"})
    harvested = reg.get("harvester").run({"classes": None})["output"]
    trained = reg.get("trainer").run({"examples": harvested})["output"]
    cand = KeywordClassifier("_cand", "meta")
    cand.weights = trained["weights"]
    after = sum(cand.run(p)["output"] == p["label"] for p in probes) / len(probes)
    print(f"B. growth: incumbent probe acc {before:.2f}; trained held-out acc "
          f"{trained['heldout_acc']:.2f}, probe acc {after:.2f}")
    assert after > before, "win rule: candidate must beat the incumbent to be adopted"
    clf.weights = trained["weights"]
    made = reg.get("cloner").run({"name": "gap-classifier", "n": 3})["output"]
    n_soc = reg.update_weights("gap-classifier", trained["weights"])
    print(f"   adopted; cloned {made}; weights socialized to {n_soc} instance(s)")
    clf.dev_status = "running-alone"
    print("   growth moves on record:", reg.get("growth-recommender").run({})["output"])

    # ---- C. surgery by protocol ------------------------------------------
    patient = KeywordClassifier("patient", "meta")
    patient.weights = {"keywords": {"invalid": {"TypeError": 3, "ValueError": 1},
                                    "index": {"IndexError": 3}, "name": {"NameError": 3}}}
    sprobes = [{"task": {"text": p["text"]}, "label": p["label"]} for p in probes]
    labels = [p["label"] for p in probes]
    out = run_protocol(patient, sprobes, labels, target_probes=[0, 1],
                       edits={"keywords.invalid.TypeError": 0})
    fixed = sum(patient.run(p)["output"] == p["label"] for p in probes) / len(probes)
    print(f"C. surgery: map indicts {out['map']['keywords.invalid.TypeError']}; "
          f"untangle complete={out['untangle']['complete']} "
          f"({out['untangle']['mapped_weights']}/{out['untangle']['total_weights']} weights); "
          f"diffs={out['diffs']}; probe acc now {fixed:.2f}")
    assert fixed == 1.0 and out["untangle"]["complete"]
    for bad in ({"specialist": patient, "map": None, "untangle": {"complete": True},
                 "target_probes": [0], "edits": {"keywords.invalid.ValueError": 5}},
                {"specialist": patient, "map": out["map"], "untangle": out["untangle"],
                 "target_probes": [0, 1], "edits": {"keywords.index.IndexError": 0}}):
        try:
            surgical_edit(bad)
            raise AssertionError("protocol violation was NOT refused")
        except ProtocolError as e:
            print(f"   protocol enforced: {e}")
    mark(reg, ["architecture-tracer", "behaviour-prober", "responsibility-mapper",
               "wiring-untangler", "surgical-editor", "harvester", "trainer",
               "spawner", "cloner", "learner", "growth-recommender"])

    # ---- D. interface layer ----------------------------------------------
    ans = interface.chat([{"role": "user", "content": "api:anthropic:claude-sonnet-5"}],
                         "local:backend-router", registry=reg)
    print(f"D. interface: local constructed backend answered via chat(): {ans['text']!r} "
          f"(usage {ans['usage']})")
    try:
        interface.chat_for_role("coder", [{"role": "user", "content": "write a program"}],
                                registry=reg, board=board)
        print("   coder role answered (unexpected in the skeleton state)")
    except interface.BackendUnavailable as e:
        print(f"   coder role: all bindings unavailable right now -> {e}")
        print("   job stays queued on the board; no human is asked. Escalations recorded:")
        for ev in board.events():
            if ev["who"] == "interface":
                print(f"     - {ev['what']}: {ev['detail'][:110]}")

    alone = [s.name for s in reg.all() if s.dev_status == "running-alone"]
    print(f"== registry: {reg.count()} specialists; running-alone: {len(alone)}; "
          f"in-development: {reg.count() - len(alone)} (model-bound, coordinators, unverified)")
    print(f"== fidelity scores on board: {board.scores('fidelity')}")
    print("DEMO OK")


if __name__ == "__main__":
    main()
