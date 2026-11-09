"""The coding swarm: a layered niche tree. Field #1 is coding.

Every niche has (a) its own smallest-possible specialists and (b) its own
smallest-possible coordinator for just that niche. No component is
general-purpose: planners plan one tiny thing, coordinators coordinate
one niche, checkers check one kind of thing.

    coding (root coordinator: the unattended pipeline)
    |- planning    step-splitter, dependency-orderer, acceptance-writer,
    |              test-layout-planner, api-shape-planner(model)
    |- writing     coder(model: local coder brain), fixer(model), code-extractor
    |- testing     test-runner, exit-checker, output-differ, file-checker,
    |              probe-generator
    |- debugging   traceback-classifier, error-line-pointer,
    |              bug-pattern-matcher, patch-applier, diagnostician(model)
    |- review      syntax-checker, sanity-checker, contract-checker,
    |              semantic-reviewer(model)
    |- integration file-writer, artifact-collector, result-assembler
    |- interface   request-normalizer, response-normalizer, backend-router,
    |              key-keeper, usage-meter
    |- compliance  instruction-splitter, literal-checker,
    |              semantic-checker(model), fidelity-scorer
    |- meta        harvester, trainer, spawner, cloner, learner,
    |              growth-recommender, gap-classifier(trainable)
    |- surgery     architecture-tracer, behaviour-prober,
                   responsibility-mapper, wiring-untangler, surgical-editor

Model-bound specialists bind through swarm.interface.BINDINGS; their
backends load when the machine frees up. Everything else already runs.

Phase 2 (PLAN.md section 15) extends this tree to coding as a whole:
reading, linting, refactoring, documenting, security, performance,
data, sql, dependencies, build, vcs, regex, shell, languages, web and
translation niches, plus test-analysis specialists inside testing.
They are registered by field_niches.register_field_niches below and
verified by swarm.coverage_check.
"""
from pathlib import Path

from . import constructed as C
from . import factory as F
from . import interface
from . import meta as M
from . import surgeon as S
from . import decomposers as D
from . import dream as DR
from .composers import register_composers
from .field_niches import FIELD_NICHES, register_field_niches
from .security_niches import SECURITY_NICHES, register_security_niches
from .specialist import NicheCoordinator, Registry, Specialist


def _surgical_editor(task):
    """The surgery niche's editor, order-facing (phase 4 audit).

    surgeon.surgical_edit still raises ProtocolError at the function
    level — that IS Arnav's protocol (no change before the map
    exists), and direct callers (factory, run_protocol) rely on it.
    But through the specialist envelope an order never dead-ends in
    an exception: the missing protocol steps become the growth move,
    the gap is recorded, and the edit is re-applied after them."""
    try:
        return S.surgical_edit(task)
    except S.ProtocolError as e:
        return {"ok": False, "output": None,
                "evidence": f"protocol prerequisite missing: {e}",
                "gap": "surgery-prerequisite",
                "growth_move": "trace -> probe -> map -> untangle, "
                               "then re-apply the edit"}
    except (KeyError, TypeError) as e:
        return {"ok": False, "output": None,
                "evidence": f"malformed surgery order: {e}",
                "gap": "surgery-prerequisite",
                "growth_move": "supply specialist + map + untangle + "
                               "edits, then re-apply"}


def _test_layout_planner(task):
    chk = task["check"]
    plan = ["exit-checker"]
    if chk["kind"].startswith("stdout"):
        plan.append("output-differ")
    if chk["kind"].startswith("file"):
        plan.append("file-checker")
    return {"ok": True, "output": plan, "evidence": f"layout for {chk['kind']}"}


def _file_writer(task):
    f = Path(task["workdir"]) / task["filename"]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(task["content"])
    return {"ok": True, "output": str(f), "evidence": f"wrote {task['filename']} ({len(task['content'])} chars)"}


def _artifact_collector(task):
    wd = Path(task["workdir"])
    files = sorted(p.name for p in wd.iterdir() if p.is_file())
    return {"ok": True, "output": files, "evidence": f"{len(files)} artifact(s)"}


def _result_assembler(task):
    return {"ok": all(p.get("ok") for p in task["parts"]),
            "output": {"stages": [p.get("specialist") for p in task["parts"]]},
            "evidence": "assembled from stage envelopes"}


def _key_keeper(task):
    service = task if isinstance(task, str) else task.get("service", "")
    present = interface.vault_key(service) is not None
    return {"ok": True, "output": present,
            "evidence": f"key for {service}: {'in vault' if present else 'absent (vault outside repo)'}"}


NICHES = ["coding", "planning", "writing", "testing", "debugging", "review",
          "integration", "interface", "compliance", "meta", "surgery"] \
    + FIELD_NICHES + SECURITY_NICHES


def build_swarm(board):
    """Instantiate the whole tree. Returns the registry."""
    reg = Registry()

    def add(name, niche, job, fn=None, binding=None):
        return reg.add(Specialist(name, niche, job, fn=fn, binding=binding))

    # interface niche — the model interface layer, as specialists
    add("request-normalizer", "interface", "normalize any API request shape to one message list", C.request_normalizer)
    add("response-normalizer", "interface", "normalize any backend reply shape to {text}", C.response_normalizer)
    add("backend-router", "interface", "parse a model_ref and name its backend", C.backend_router)
    add("key-keeper", "interface", "know whether a service key is in the vault (never show it)", _key_keeper)
    reg.add(Specialist("usage-meter", "interface", "accumulate token usage per role", fn=C.UsageMeter()))

    # planning niche — planners that each plan one tiny thing
    add("step-splitter", "planning", "split an instruction into steps", C.step_splitter)
    add("dependency-orderer", "planning", "order steps by dependency (Kahn, alpha tie-break)", C.dependency_orderer)
    add("acceptance-writer", "planning", "turn a check spec into gate list", C.acceptance_writer)
    add("test-layout-planner", "planning", "choose which checker specialists a check kind needs", _test_layout_planner)
    add("api-shape-planner", "planning", "plan the shape of an API/function signature", binding=interface.BINDINGS["api-shape-planner"])

    # writing niche
    add("coder", "writing", "write one complete program for a step", binding=interface.BINDINGS["coder"])
    add("fixer", "writing", "rewrite a program to fix a diagnosed problem", binding=interface.BINDINGS["fixer"])
    add("code-extractor", "writing", "pull the program out of a model reply", C.extract_code)

    # testing niche
    add("test-runner", "testing", "execute a program and capture exit/stdout/stderr", C.run_program)
    add("exit-checker", "testing", "check exit code is 0", C.exit_checker)
    add("output-differ", "testing", "diff expected vs actual output, name first mismatch", C.output_differ)
    add("file-checker", "testing", "verify a produced file exactly / by JSON equality", C.file_checker)
    add("probe-generator", "testing", "generate probe inputs for one kind of value", C.probe_generator)

    # debugging niche
    add("traceback-classifier", "debugging", "name the error class in a traceback", C.traceback_classifier)
    add("error-line-pointer", "debugging", "point at the traceback's deepest program line", C.error_line_pointer)
    add("bug-pattern-matcher", "debugging", "match a known bug signature, propose smallest patch", C.bug_pattern_matcher)
    add("patch-applier", "debugging", "apply exactly one old->new replacement", C.patch_applier)
    add("diagnostician", "debugging", "explain a failure in one sentence", binding=interface.BINDINGS["diagnostician"])

    # review niche
    add("syntax-checker", "review", "check a program compiles", C.syntax_checker)
    add("sanity-checker", "review", "catch impossible measurements in output", C.sanity_checker)
    add("contract-checker", "review", "check every expected output file exists", C.contract_checker)
    add("semantic-reviewer", "review", "judge whether code really does the task", binding=interface.BINDINGS["semantic-reviewer"])

    # integration niche
    add("file-writer", "integration", "write one artifact file", _file_writer)
    add("artifact-collector", "integration", "list the artifacts in a workdir", _artifact_collector)
    add("result-assembler", "integration", "assemble stage envelopes into the final result", _result_assembler)

    # compliance niche — instruction fidelity, checked item by item
    add("instruction-splitter", "compliance", "split a literal instruction into requirement items", C.instruction_splitter)
    add("literal-checker", "compliance", "check one requirement item literally against the result", C.literal_checker)
    add("semantic-checker", "compliance", "check one requirement item semantically", binding=interface.BINDINGS["semantic-checker"])
    add("fidelity-scorer", "compliance", "score instruction fidelity and record it", C.fidelity_scorer)

    # meta niche — growth (see meta.py)
    add("harvester", "meta", "find/make training examples for a gap", M.harvest_error_examples)
    add("trainer", "meta", "fit a smallest specialist from examples, verify held-out", M.train_keyword_classifier)
    add("spawner", "meta", "create a new specialist from a spec", M.spawn_from_spec(reg, board))
    add("cloner", "meta", "clone a specialist for coverage", M.clone_for_coverage(reg, board))
    add("learner", "meta", "record a failure as a lesson on the board", M.learn_from_failure(board))
    add("growth-recommender", "meta", "read failure lessons, name the growth move", lambda task: M.recommend_growth(board))
    reg.add(M.KeywordClassifier("gap-classifier", "meta",
                                "classify gap/failure texts into error classes (trainable)"))
    add("model-factory", "meta", "produce a verified smallest specialist MODEL for a niche job (factory: train or edit, win rule)", F.make_specialist_model(reg, board))
    add("defect-class-splitter", "meta", "split a multiclass defect job into per-class binary jobs (decomposer)", D.defect_class_splitter)
    add("slice-splitter", "meta", "split one class job into per-slice variant jobs (decomposer)", D.slice_splitter)
    add("dreamer", "meta", "run a bounded dream cycle on a model: offline practice + trigger traces (win rule keeps or reverts)", DR.dream_cycle)

    # surgery niche — the protocol, one specialist per step (see surgeon.py)
    add("architecture-tracer", "surgery", "trace a specialist's architecture as it is", S.trace_architecture)
    add("behaviour-prober", "surgery", "find responsible weights by ablation probes", S.probe_responsibilities)
    add("responsibility-mapper", "surgery", "build the weight->behaviour map", S.build_map)
    add("wiring-untangler", "surgery", "certify every weight is accounted for in the map", S.untangle)
    add("surgical-editor", "surgery", "edit only map-responsible weights", _surgical_editor)

    # phase 2: the field-coverage niches (PLAN.md section 15)
    register_field_niches(reg)

    # phase 4: the security-operations branch (PLAN.md section 15F)
    register_security_niches(reg)

    # phase 4: composition specialists (PLAN.md section 18)
    register_composers(reg)

    # phase 3: adopted TinyNet models saved by factory runs (PLAN.md §17)
    F.load_models(reg)

    # one coordinator per niche — each coordinates only its own niche
    for niche in NICHES:
        reg.add(NicheCoordinator(niche, routes={}))
    return reg


def tree_summary(reg):
    lines, total = [], 0
    for niche in NICHES:
        members = reg.in_niche(niche)
        total += len(members)
        lines.append(f"{niche:<12} {len(members):>2}  "
                     + ", ".join(f"{s.name}({s.kind})" for s in members))
    return lines, total


# ------------------------------------------------------------ the pipeline
def run_fix_pipeline(reg, board, instruction, buggy_code, check, save_as, workdir):
    """The unattended loop for a fix task, end to end, no human in it.

    planning -> testing(run) -> [debugging -> patch -> testing]* ->
    review -> integration(save) -> compliance(fidelity gate).
    A failed gate routes work back or into the meta layer; it never
    stops to ask a human.
    """
    workdir = str(workdir)
    board.event("coding-coordinator", "start", instruction[:80])
    parts = []

    steps = reg.get("step-splitter").run(instruction)
    parts.append(steps)
    gates = reg.get("acceptance-writer").run({"check": check, "save_as": save_as})
    layout = reg.get("test-layout-planner").run({"check": check})

    code, final_run, diff = buggy_code, None, None
    for round_ in range(1, 4):
        run = reg.get("test-runner").run({"code": code, "workdir": workdir, "filename": "candidate.py"})
        final_run = run["output"]
        board.event("test-runner", "run", run["evidence"])
        diff = reg.get("output-differ").run({"expected": check["lines"],
                                             "actual": final_run["stdout"]})
        parts.append(diff)
        if diff["ok"]:
            break
        board.event("coding-coordinator", "gate-fail", f"round {round_}: {diff['evidence']}")
        reg.get("learner").run({"niche": "testing", "what": f"output mismatch: {diff['evidence']}",
                                "gap": "wrong-output"})
        match = reg.get("bug-pattern-matcher").run({"code": code})
        if not match["ok"]:
            board.event("coding-coordinator", "growth", "unknown bug -> meta layer")
            break
        patched = reg.get("patch-applier").run({"code": code, **match["output"]})
        if not patched["ok"]:
            break
        code = patched["output"]
        board.event("patch-applier", "patch", patched["evidence"])

    syn = reg.get("syntax-checker").run({"code": code})
    san = reg.get("sanity-checker").run({"stdout": final_run["stdout"] if final_run else ""})
    saved = reg.get("file-writer").run({"workdir": workdir, "filename": save_as, "content": code})
    contract = reg.get("contract-checker").run({"workdir": workdir, "files": [save_as]})
    parts += [syn, san, saved, contract]

    # compliance gate: the literal instruction, item by item
    items = reg.get("instruction-splitter").run(instruction)["output"]
    result_env = {"workdir": workdir, "stdout": final_run["stdout"] if final_run else "",
                  "expected_lines": check["lines"]}
    checks = []
    for item in items:
        c = reg.get("literal-checker").run({"item": item, "result": result_env})
        checks.append(c)
        board.event("literal-checker", "check", f"{item[:50]!r} -> {c['output']}")
    fidelity = reg.get("fidelity-scorer").run({"checks": checks})
    board.record_score("fidelity", save_as, fidelity["output"], fidelity["evidence"])
    parts.append(fidelity)

    assembled = reg.get("result-assembler").run({"parts": parts})
    ok = bool(diff and diff["ok"] and syn["ok"] and contract["ok"] and fidelity["output"] == 1.0)
    board.event("coding-coordinator", "finish", f"ok={ok} fidelity={fidelity['output']}")
    return {"ok": ok, "code": code, "stdout": result_env["stdout"],
            "fidelity": fidelity["output"], "checks": checks,
            "gates": gates["output"], "layout": layout["output"]}
