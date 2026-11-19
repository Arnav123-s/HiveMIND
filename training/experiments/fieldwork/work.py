"""Run a new, user-defined programming work order on CPU with public examples and a persistent skill directory."""

import argparse
import csv
import contextlib
import errno
import fcntl
import io
import json
import os
import re
import tempfile
from functools import partial
from pathlib import Path

from .campaign import fingerprint, save, tool_source
from .contracts import Task
from .guest import Guest
from . import repair_learning
from .native import generate, server


def words(text):
    return set(re.findall(r"[a-z]{4,}", text.lower())) - {
        "return",
        "input",
        "output",
        "write",
        "python",
        "list",
        "function",
        "solve",
        "with",
        "each",
    }


def retrieve(text, bank):
    mine = words(text)

    def score(row):
        other = words(row["description"])
        return len(mine & other) / max(1, len(mine | other))

    ranked = sorted(
        (r for r in bank if score(r) > 0), key=lambda r: (-score(r), -r["validation"], r["digest"])
    )
    selected = {}
    for r in ranked:
        selected.setdefault(r["task"], r)
    return list(selected.values())[:2]


def matches(actual, expected, formats=None):
    if formats:
        if not isinstance(actual, dict) or not isinstance(expected, dict) or set(expected) != set(actual):
            return False
        actual, expected = actual.copy(), expected.copy()
        for key, fmt in formats.items():
            if not isinstance(actual.get(key), str) or not isinstance(expected.get(key), str):
                return False
            try:
                if fmt == "json":
                    actual[key], expected[key] = json.loads(actual[key]), json.loads(expected[key])
                elif fmt == "csv":
                    if expected[key].endswith("\n") and not actual[key].endswith("\n"):
                        return False
                    actual[key] = list(csv.reader(io.StringIO(actual[key])))
                    expected[key] = list(csv.reader(io.StringIO(expected[key])))
                else:
                    raise ValueError("unknown file comparison")
            except (ValueError, csv.Error):
                return False
    return json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)


def check(guest, program, examples, formats=None, *, explain=True):
    results, _, _ = guest.run(program, [r["input"] for r in examples], fuel=14_000_000_000)
    ok = [
        ("value" in v and matches(v["value"], r["output"], r.get("compare", formats)))
        for v, r in zip(results, examples)
    ]
    if not explain:
        return sum(ok), None
    failed = next((i for i, b in enumerate(ok) if not b), None)
    if failed is None and len(ok) != len(examples):
        return sum(ok), "The program did not return a result for every public example."
    feedback = "All examples passed."
    if failed is not None:
        feedback = json.dumps(
            {
                "input": examples[failed]["input"],
                "expected": examples[failed]["output"],
                "actual": results[failed],
            },
            separators=(",", ":"),
        )[:650]
    return sum(ok), feedback


def contract_id(row):
    return fingerprint(json.dumps([row["task"], row["description"]], ensure_ascii=True))


def _valid_bank_row(row):
    return (
        isinstance(row, dict)
        and isinstance(row.get("task"), str)
        and re.fullmatch("[a-z][a-z0-9_]{0,60}", row["task"])
        and isinstance(row.get("description"), str)
        and isinstance(row.get("source"), str)
        and fingerprint(row["source"]) == row.get("digest")
        and type(row.get("validation")) is int and row["validation"] > 0
    )


def _read_bank_row(path):
    try:
        if path.is_symlink() or not path.is_file():
            return None
        row = json.loads(path.read_bytes())
        if _valid_bank_row(row) and path.stem in (row["digest"], row["digest"] + "-" + contract_id(row)):
            return row
    except (OSError, ValueError, RecursionError):
        pass
    return None


@contextlib.contextmanager
def _directory_fd(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield fd
    finally:
        os.close(fd)


def _make_bank_dir(path):
    if not path.parent.is_dir():
        _make_bank_dir(path.parent)
    path.mkdir(exist_ok=True)
    # Persist the directory entry, including when another process just created it.
    with _directory_fd(path.parent) as parent:
        os.fsync(parent)


def admit(directory, row):
    """Durably publish one checked version per source and contract, retaining the first receipt."""
    if not _valid_bank_row(row):
        raise ValueError("bank admission requires a checked record and matching source digest")
    key = row["digest"]
    paths = (directory / (key + ".json"), directory / (key + "-" + contract_id(row) + ".json"))
    _make_bank_dir(directory)
    with _directory_fd(directory) as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        pending = directory / ".admission.pending"
        # A killed writer may have linked this inode into the bank. Never reopen it for writing.
        pending.unlink(missing_ok=True)
        try:
            for path in paths:
                stored = _read_bank_row(path)
                if stored and all(stored[k] == row[k] for k in ("task", "description", "source")):
                    return
            stage_fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(stage_fd, "w", encoding="utf-8") as stream:
                json.dump(row, stream, allow_nan=False, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            for path in paths:
                try:
                    os.link(pending, path)
                    return
                except FileExistsError:
                    continue
            raise FileExistsError(f"both bank record names are occupied; cannot retain {key}")
        finally:
            pending.unlink(missing_ok=True)
            os.fsync(fd)


def load_bank(directory):
    if directory is None or not directory.is_dir():
        return []
    rows = {}
    # Legacy digest-only records take precedence over a duplicate contract-specific alias.
    for path in sorted(directory.glob("*.json"), key=lambda p: (len(p.name), p.name)):
        row = _read_bank_row(path)
        if row:
            rows.setdefault((row["digest"], row["task"], row["description"]), row)
    return [rows[identity] for identity in sorted(rows)]


def finish_files(root, ident, value, names):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", ident):
        raise ValueError("job ID must be a single name")
    if (
        len(set(names)) != len(names)
        or not names
        or any(Path(n).name != n or n in (".", "..", "") for n in names)
        or not isinstance(value, dict)
        or set(value) != set(names)
        or not all(isinstance(v, str) for v in value.values())
    ):
        raise ValueError("returned files differ from the requested file contract")
    destination = root / ident
    if destination.is_symlink():
        raise FileExistsError(destination)
    if destination.exists():
        if not destination.is_dir():
            raise FileExistsError(destination)
        present = {p.name for p in destination.iterdir()}
        if not present <= set(names) or any(
            (destination / n).is_symlink()
            or not (destination / n).is_file()
            or (destination / n).read_bytes() != value[n].encode()
            for n in present
        ):
            raise FileExistsError(destination)
        for n in set(names) - present:
            with tempfile.NamedTemporaryFile(dir=root) as stream:
                stream.write(value[n].encode())
                stream.flush()
                os.link(stream.name, destination / n)
        return
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        stage = Path(tmp) / "files"
        stage.mkdir()
        for n in names:
            (stage / n).write_bytes(value[n].encode())
        os.replace(stage, destination)


def commit_output(root, job, value):
    if "snapshot_file" in job:
        name = job["snapshot_file"]
        if "files" in job:
            raise ValueError("a job must choose a JSON snapshot or named file outputs")
        body = json.dumps(value, sort_keys=True, allow_nan=False) + "\n"
        finish_files(root, job["id"], {name: body}, [name])
        return root / job["id"] / name
    if "files" in job:
        finish_files(root, job["id"], value, job["files"])


def saved_receipt(out, spec):
    result = json.loads((out / "receipt.json").read_text())
    result["jobs"] = restore_jobs(out, spec, result["jobs"])
    return result


def restore_jobs(out, spec, rows):
    by_id = {j["id"]: j for j in spec.get("jobs", [])}
    valid, pending = set(), set()
    restored = list(rows)
    for i, row in enumerate(rows):
        if "value" in row:
            try:
                job = by_id[row["id"]]
                parents = set(job.get("from_job", {}).values())
                if parents & pending:
                    raise OSError("snapshot publication pending")
                if not parents <= valid:
                    raise ValueError("a stored snapshot could not be verified")
                commit_output(out, job, row["value"])
                valid.add(row["id"])
            except OSError as exc:
                restored[i] = {"id": row["id"], "error": str(exc), "pending_value": row["value"]}
                pending.add(row["id"])
            except (ValueError, TypeError) as exc:
                restored[i] = {"id": row["id"], "error": str(exc)}
    return restored


def deliver(guest, program, jobs, root, *, previous=None):
    ids = [j["id"] for j in jobs]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", i) for i in ids):
        raise ValueError("each job needs a unique short ID")
    linked = any(j.get("from_job") for j in jobs)
    results = [] if linked or previous is not None else guest.run(program, [j["input"] for j in jobs], fuel=30_000_000_000)[0]
    receipts, pending, snapshots = [], set(), {}
    for i, job in enumerate(jobs):
        ident = job["id"]
        old = previous[i] if previous is not None else {}
        upstream = job.get("from_job", {})
        try:
            if any(prior in pending for prior in upstream.values()):
                # Keep an already computed result private until its predecessor is published.
                row = {"error": "snapshot publication pending", "retry_delivery": True}
                for key in ("pending_value", "value"):
                    if key in old:
                        row["pending_value"] = old[key]
                pending.add(ident)
            elif any(prior not in snapshots for prior in upstream.values()):
                raise ValueError("snapshot dependency unavailable or input field already set")
            elif "pending_value" in old or "value" in old:
                row = {"value": old.get("pending_value", old.get("value"))}
            elif old and not old.get("retry_delivery"):
                row = old
            elif results:
                row = results[i]
            else:
                value = job["input"]
                if upstream:
                    value = dict(value)
                    for field, prior in upstream.items():
                        if field in value:
                            raise ValueError("snapshot dependency unavailable or input field already set")
                        value[field] = json.loads(snapshots[prior].read_bytes())
                row = guest.run(program, [value], fuel=30_000_000_000)[0][0]
            if "value" in row:
                try:
                    snapshot = commit_output(root, job, row["value"])
                except OSError as exc:
                    row = {"error": str(exc), "pending_value": row["value"]}
                    pending.add(ident)
                else:
                    if snapshot is not None:
                        snapshots[ident] = snapshot
        except OSError as exc:
            row = {"error": str(exc), "retry_delivery": True}
            pending.add(ident)
        except (ValueError, TypeError) as exc:
            row = {"error": str(exc)}
        receipts.append({"id": ident, **row})
    return receipts


def check_versions(versions, spec, guest):
    """Public failures can teach a correction. Independent checks can only accept or reject."""
    qualified, checks, seed = [], [], None
    public, validation, formats = spec["examples"], spec.get("validation", []), spec.get("compare")
    for row in versions:
        score, feedback = check(guest, row["source"], public, formats)
        observed = dict(digest=row["digest"], public=score, public_failed=len(public) - score,
                        validated=None, validation_failed=None)
        if score != len(public):
            observed["reason"] = "public_failed"
            if seed is None or score > seed["passed"]:
                seed = dict(source=row["source"], feedback=feedback, passed=score, digest=row["digest"])
        else:
            passed = check(guest, row["source"], validation, formats, explain=False)[0] if validation else 0
            observed.update(validated=passed, validation_failed=len(validation) - passed)
            if passed == len(validation):
                qualified.append(row)
                observed["reason"] = "qualified"
            else:
                observed["reason"] = "validation_failed"
        checks.append(observed)
    return qualified, checks, seed


def shared_results(qualified, guest, jobs, formats=None, *, on_difference=None):
    """Stage jobs privately when the checks cannot distinguish saved implementations."""
    if not jobs:
        return None, "There are no jobs on which to compare the qualified versions."
    reference = None
    for member in qualified:
        with tempfile.TemporaryDirectory() as tmp:
            rows = deliver(guest, member["source"], jobs, Path(tmp))
        for i, row in enumerate(rows):
            if "value" not in row:
                return None, f"Job {row['id']} failed for a qualified version."
            if reference is None:
                continue
            values = (reference[i]["value"], row["value"])
            comparison = jobs[i].get("compare")
            if "compare" not in jobs[i] and formats and all(isinstance(v, dict) for v in values):
                comparison = {key: fmt for key, fmt in formats.items() if any(key in v for v in values)}
            if not matches(*values, comparison):
                if on_difference is not None:
                    on_difference(jobs[i], reference, *values, rows)
                rendered = [json.dumps(v) for v in values if not isinstance(v, (list, dict))]
                details = " (" + " or ".join(rendered) + ")" if len(rendered) == 2 and all(len(v) <= 40 for v in rendered) else ""
                return None, f"The qualified versions gave different answers for job {row['id']}{details}."
        if reference is None:
            reference = rows
    return reference, None


def policy_id(policy):
    return fingerprint(json.dumps(policy, sort_keys=True, separators=(",", ":")))


def validation_set_id(spec):
    """A repeated teaching input cannot independently qualify a repair lesson."""
    def inputs(rows):
        return {json.dumps(row["input"], sort_keys=True, separators=(",", ":")) for row in rows}
    validation = inputs(spec.get("validation", []))
    if not validation or not inputs(spec["examples"]).isdisjoint(validation):
        return None
    return fingerprint(json.dumps(sorted(validation), separators=(",", ":")))


def _admit_delivered(spec, result, state, bank_path, program):
    if (not bank_path or not spec.get("validation") or any("value" not in job for job in result["jobs"])
            or any(row["reason"] == "qualified" for row in result["saved_checks"])):
        return
    validation_set = validation_set_id(spec)
    if not validation_set:
        result.update(admission="overlapping_checks",
                      reason="The qualification set repeats a public input. The method was not saved.")
        return
    entry = dict(task=spec["name"], description=spec["task"], source=program, digest=result["digest"],
                 public=result["public"], validation=result["validated"], parents=result["parents"])
    if "arithmetic_repair" in result:
        entry["arithmetic_repair"] = result["arithmetic_repair"]
    for kind in ("learned_repair", "decoded_input_repair"):
        if kind in result:
            entry[kind] = result[kind]
    # A synthetic edit cannot corroborate itself. Only an independently
    # admitted, unmodified writer proposal can teach a new transformation.
    from team.skill_inputs import infer_contract
    entry["input_contract"] = infer_contract([row["input"] for row in spec["examples"]])
    best = next((attempt for attempt in result["attempts"] if attempt["program"] == program), {})
    parent = best.get("writer_parent")
    if state.get("learn_repairs") and "repair_search" not in result and parent and validation_set:
        # Credit only the failed source actually shown to the writer. Another
        # low-scoring attempt in the trace may have had no causal role.
        seed = state.get("repair_seed")
        predecessors = ([seed] if seed else []) + result["attempts"]
        failed = next((r for r in predecessors if r["passed"] < best["passed"]
                       and fingerprint(r["source"]) == parent), None)
        if failed and len(failed["source"]) <= 5900:
            rule = repair_learning.discover(failed["source"], best["source"])
            if rule is not None:
                event = {"parent": parent, "rule": rule, "validation_set": validation_set}
                entry["repair_experience"] = result["repair_experience"] = [event]
    admit(bank_path, entry)


def _resume_delivery(out, spec, receipt, guest, state, bank_path):
    """Retry publication errors without spending a new writing, repair or challenge budget."""
    jobs = receipt["jobs"]
    # Prior releases retained only the exception text. Recognize ordinary filesystem
    # errors from file publication; guest exceptions are prefixed with their Python type.
    blocked = set()
    for job, old in zip(spec.get("jobs", []), jobs):
        error = old.get("error", "")
        match = re.match(r"^\[Errno ([0-9]+)\] ", error)
        file_job = "snapshot_file" in job or "files" in job
        old_os_error = match and int(match[1]) in {errno.ENOSPC, errno.EDQUOT, errno.EACCES, errno.EAGAIN,
                                                  errno.EINTR, errno.EROFS, errno.EBUSY, errno.EIO, errno.EMFILE}
        blocked_parent = blocked.intersection(job.get("from_job", {}).values())
        if (file_job and (old_os_error or error == str(out / job["id"]))
                or blocked_parent and error == "snapshot dependency unavailable or input field already set"):
            old["retry_delivery"] = True
        if old.get("retry_delivery") or "pending_value" in old:
            blocked.add(job["id"])
    if not any("pending_value" in j or j.get("retry_delivery") for j in jobs):
        # Other jobs in this receipt may already have succeeded and need their files restored.
        receipt["jobs"] = restore_jobs(out, spec, jobs)
        return receipt
    program = (out / "solver.py").read_bytes().decode().removesuffix("\n")
    if fingerprint(program) != receipt["digest"]:
        raise ValueError("the saved solver differs from the qualified program")
    receipt["jobs"] = deliver(guest, program, spec.get("jobs", []), out, previous=jobs)
    if all("value" in job for job in receipt["jobs"]):
        receipt.pop("status", None)
        receipt.pop("reason", None)
        _admit_delivered(spec, receipt, state, bank_path, program)
    save(out / "receipt.json", receipt)
    return receipt


def _initial_manifest(out, state, marker):
    token = state["spec_digest"]
    stage = out / f".work-order-{token}.pending"
    lock = out / ".work.lock"
    owner = "fieldwork initial manifest " + token
    if any(path not in (stage, lock) for path in out.iterdir()):
        raise FileExistsError("use a fresh or matching work-order directory")
    signature = owner.encode()
    marker.seek(0)
    contents = marker.read(len(signature) + 1)
    if contents not in (b"", signature) or os.fstat(marker.fileno()).st_nlink != 1:
        raise FileExistsError("the work-order lock name is occupied")
    if stage.exists() or stage.is_symlink():
        if stage.is_symlink() or not stage.is_file() or contents != signature:
            raise FileExistsError("the work-order staging name is occupied")
        stage.unlink()
    if not contents:
        marker.write(signature)
        marker.flush()
        os.fsync(marker.fileno())
    with stage.open("x", encoding="utf-8") as stream:
        json.dump(state, stream, allow_nan=False, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stage, out / "work-order.json")
    with _directory_fd(out) as fd:
        os.fsync(fd)


def work(spec, guest, ask, out, bank_path=None, rounds=3, memory_view="contract", *,
         repair_budget=8, learn_repairs=True, challenge_budget=0):
    out.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(out / ".work.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "r+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _work(spec, guest, ask, out, bank_path, rounds, memory_view, repair_budget, learn_repairs, challenge_budget, lock)


def _work(spec, guest, ask, out, bank_path, rounds, memory_view, repair_budget, learn_repairs, challenge_budget, lock):
    name = spec["name"]
    if not re.fullmatch("[a-z][a-z0-9_]{0,60}", name) or not spec["examples"] or rounds < 1:
        raise ValueError("provide a short program name and at least one checked example")
    if memory_view not in ("contract", "source"):
        raise ValueError("unknown memory view")
    if type(repair_budget) is not int or not 0 <= repair_budget <= 8:
        raise ValueError("repair budget must be between 0 and 8 candidate checks")
    if type(challenge_budget) is not int or not 0 <= challenge_budget <= 2:
        raise ValueError("challenge budget must be between 0 and 2 rivals")
    if challenge_budget and not learn_repairs:
        raise ValueError("checking learned rivals requires learned repairs to be enabled")
    if challenge_budget and not validation_set_id(spec):
        raise ValueError("checking learned rivals requires disjoint public and qualification inputs")
    token = fingerprint(json.dumps(spec, sort_keys=True, separators=(",", ":")))
    manifest = out / "work-order.json"
    prior_attempts = []
    if manifest.exists():
        state = json.loads(manifest.read_text())
        if state["spec_digest"] != token:
            raise ValueError("this output belongs to a different work order; use a new output directory")
        old = state["parents"]
        # A pre-version manifest resumes with exactly the programs its original recipe saw.
        versions = state.get("versions", [r for r in old if r["task"] == name and r["description"] == spec["task"]])
        memory_view = state.get("memory_view", "source")
        # An interrupted run uses its original policy and budget. An older manifest
        # predates learning and resumes with the original arithmetic search.
        if state.get("challenge_budget", 0) != challenge_budget:
            raise ValueError("the verification budget changed; use a new output directory to recheck a work order")
        repair_budget = state.get("repair_budget", 8)
        learn_repairs = state.get("learn_repairs", False)
        if (out / "receipt.json").exists():
            receipt = json.loads((out / "receipt.json").read_bytes())
            if (receipt.get("status") == "delivery_failed" or
                    (not receipt.get("status") and any("error" in j for j in receipt["jobs"]))):
                return _resume_delivery(out, spec, receipt, guest, state, bank_path)
            waiting = receipt.get("status") == "needs_generation"
            failed_public = bool(receipt["attempts"]) and receipt["public"] < receipt["examples"]
            if not waiting and not failed_public:
                receipt["jobs"] = restore_jobs(out, spec, receipt["jobs"])
                return receipt
            bank = load_bank(bank_path)
            checked = {item["digest"] for item in receipt["saved_checks"]}
            fresh = [r for r in bank if r["task"] == name and r["description"] == spec["task"]
                     and r["digest"] not in checked]
            policy = repair_learning.learn(bank if learn_repairs else [])
            if fresh:
                by_digest = {r["digest"]: r for r in [*versions, *fresh]}
                versions = sorted(by_digest.values(), key=lambda r: (-r["validation"], r["digest"]))
                state["versions"] = versions
                state.pop("saved_checks", None)
                state.pop("repair_seed", None)
            if failed_public:
                previous = receipt.get("repair_search")
                new_search = bool(learn_repairs and bank_path and repair_budget and spec.get("validation")
                                  and policy_id(policy) != (previous or {}).get("policy"))
                if not fresh and not new_search:
                    return receipt
                if previous and previous not in state.setdefault("prior_searches", []):
                    state["prior_searches"].append(previous)
                prior_attempts = receipt["attempts"]
                rounds, ask = len(prior_attempts), None
            elif not fresh and ask is None:
                return receipt
            # Exact-version refresh and a learned challenger must use the same bank snapshot.
            state["repair_policy"] = policy
            save(manifest, state)
    else:
        bank = load_bank(bank_path)
        versions = [r for r in bank if r["task"] == name and r["description"] == spec["task"]]
        versions.sort(key=lambda r: (-r["validation"], r["digest"]))
        old = retrieve(spec["task"], [r for r in bank if r["task"] != name or r["description"] != spec["task"]])
        state = dict(spec_digest=token, parents=old, versions=versions, memory_view=memory_view,
                     learn_repairs=learn_repairs, repair_budget=repair_budget, challenge_budget=challenge_budget,
                     repair_policy=repair_learning.learn(bank if learn_repairs else []))
        _initial_manifest(out, state, lock)
    versions = list({r["digest"]: r for r in versions}.values())
    prompt = Task(
        spec["task"], (), "Public examples: " + json.dumps(spec["examples"], separators=(",", ":"))[:1900]
    )
    prefix = ""
    if old and memory_view == "contract":
        helpers = []
        for item in old:
            label = "skill_" + item["task"]
            description = item["description"].replace("Write solve(x)", label + "(x) is available")
            helpers.append(f"{label}(x) — {description}")
        prompt = Task(
            "Optional library, already implemented:\n"
            + "\n".join(helpers)
            + "\n\nCurrent assignment:\n"
            + prompt.text,
            (),
            prompt.example,
        )
    elif old:
        prefix = "\nVerified optional functions from previous work:\n" + "\n".join(
            f"skill_{r['task']}(x): {r['description']}\n{r['source'][:1300]}" for r in old
        )
    best, trace = None, []
    promotion = spec.get("validation", [])
    jobs = spec.get("jobs", [])
    if "saved_checks" in state:
        checks, seed = state["saved_checks"], state.get("repair_seed")
        qualified_ids = {r["digest"] for r in checks if r["reason"] == "qualified"}
        qualified = [r for r in versions if r["digest"] in qualified_ids]
    else:
        qualified, checks, seed = check_versions(versions, spec, guest)
        # The seed contains only a saved program and a public counterexample.
        state.update(saved_checks=checks, repair_seed=seed)
        save(manifest, state)
    result = dict(digest=None, public=0, examples=len(spec["examples"]), validated=0,
                  validation_total=len(promotion), parents=[], attempts=trace, saved_checks=checks, jobs=[])
    if state.get("prior_searches"):
        result["prior_searches"] = state["prior_searches"]
    staged = None
    if qualified:
        trace.extend(prior_attempts)
        member = qualified[0]
        result.update(public=len(spec["examples"]), validated=len(promotion))
        if len(qualified) > 1:
            result["versions_compared_on_jobs"] = [r["digest"] for r in qualified]
            staged, conflict = shared_results(qualified, guest, jobs, spec.get("compare"))
            if conflict:
                result.update(status="ambiguous_saved_versions", reason=conflict + " Supply a distinguishing example and run the changed work order in a new output directory.")
                save(out / "receipt.json", result)
                return result
        best = dict(program=member["source"], source=member["source"], passed=len(spec["examples"]),
                    feedback="All examples passed.", usage={"completion_tokens": 0}, stop="verified_reuse", seconds=0)
        trace.append(best)
        result["parents"] = [member["digest"]]
    for attempt in range(rounds):
        if best is not None and best["passed"] == len(spec["examples"]):
            break
        trial = out / f"attempt-{attempt + 1}.json"
        if trial.exists():
            new = json.loads(trial.read_text())
        else:
            if ask is None:
                break
            earlier = best or seed
            prior = (earlier["source"], earlier["feedback"]) if earlier else None
            # The persisted attempt index also determines the writer after a restart.
            writer = ask[attempt % len(ask)] if isinstance(ask, (list, tuple)) else ask
            row = writer(prompt, prefix, prior)
            program = tool_source(row["source"], old)
            passed, feedback = check(guest, program, spec["examples"], spec.get("compare"))
            new = dict(
                program=program,
                source=row["source"],
                passed=passed,
                feedback=feedback,
                usage=row["usage"],
                seconds=row.get("seconds"),
                writer=row.get("writer"),
                stop=row.get("stop"),
                writer_parent=fingerprint(earlier["source"]) if earlier else None,
                repair_parent=best.get("repair_parent") if best else (seed["digest"] if seed else None),
            )
            save(trial, new)
        trace.append(new)
        if best is None or new["passed"] > best["passed"]:
            best = new
        if new["passed"] == len(spec["examples"]):
            break
    if best is None:
        if checks:
            strongest = max(checks, key=lambda c: (c["public"], c["validated"] or 0))
            result.update(public=strongest["public"], validated=strongest["validated"] or 0)
        result.update(status="needs_generation", reason="No saved version qualified. Supply --member auto or --binary and --weights to generate a worker.")
        save(out / "receipt.json", result)
        return result
    if promotion and best["passed"] < len(spec["examples"]):
        # Change only the new proposal. Retrieved helpers stay byte-for-byte intact.
        policy = state.get("repair_policy", repair_learning.learn([]))
        search = {"policy": policy_id(policy), "budget": repair_budget, "candidates_checked": 0}

        def public_score(source, examples):
            search["candidates_checked"] += 1
            return check(guest, tool_source(source, old), examples, spec.get("compare"), explain=False)[0]

        failed_digest = fingerprint(best["program"])
        checkpoint = out / f"repair-{failed_digest}-{search['policy']}-{repair_budget}.json"
        if checkpoint.exists():
            recorded = json.loads(checkpoint.read_text())
            search, repair = recorded["search"], recorded["repair"]
        else:
            repair = repair_learning.select(best["source"], spec["examples"], public_score, limit=repair_budget,
                                            original_passed=best["passed"], policy=policy)
            save(checkpoint, {"search": search, "repair": repair})
        result["repair_search"] = search
        if repair is not None:
            program = tool_source(repair["program"], old)
            details = dict(parent=failed_digest, edit=repair["edit"],
                           original_public=best["passed"], tried=repair["tried"])
            if repair.get("method") == "learned":
                result["learned_repair"] = dict(details, rule_id=repair["rule_id"], support=repair["support"])
            elif repair.get("method") == "decoded_input":
                result["decoded_input_repair"] = details
            else:
                result["arithmetic_repair"] = details
            best = dict(best, program=program, repaired_source=repair["program"], passed=repair["passed"])
    (out / "solver.py").write_text(best["program"] + "\n")
    if not qualified:
        result["parents"] = [r["digest"] for r in old]
        if best.get("repair_parent") and best["repair_parent"] not in result["parents"]:
            result["parents"].append(best["repair_parent"])
        if promotion and best["passed"] == len(spec["examples"]):
            result["validated"], _ = check(guest, best["program"], promotion, spec.get("compare"), explain=False)
    key = fingerprint(best["program"])
    result.update(digest=key, public=best["passed"])
    if best["passed"] == len(spec["examples"]) and result["validated"] == len(promotion):
        if challenge_budget:
            from .challenge import assess
            # The original source in a synthetically repaired attempt remains in the trace.
            # A rival must challenge the *actual* winning program. Stored programs already
            # include their helpers, so pass the exact persisted program with an identity wrap.
            verifier_source = best["program"] if qualified else best.get("repaired_source", best["source"])
            wrap = (lambda source: source) if qualified else (lambda source: tool_source(source, old))
            challenge, compared = assess(verifier_source, best["program"], state["repair_policy"], spec, guest,
                                         wrap=wrap, limit=challenge_budget)
            result["challenge"] = challenge
            if challenge["status"] in ("ambiguous", "inconclusive"):
                result.update(status="challenge_" + challenge["status"], digest=None, reason=challenge["reason"])
                save(out / "receipt.json", result)
                return result
            if compared is not None:
                staged = compared
        result["jobs"] = (restore_jobs(out, spec, staged) if staged is not None
                          else deliver(guest, best["program"], jobs, out))
        _admit_delivered(spec, result, state, bank_path, best["program"])
    if result["public"] < result["examples"]:
        result.update(status="public_failed", reason="The proposed program still fails the public examples.")
    elif result["validated"] < result["validation_total"]:
        result.update(status="validation_failed", reason="The proposed program failed independent qualification.")
    elif any("value" not in job for job in result["jobs"]):
        result.update(status="delivery_failed", reason="A qualified program failed to deliver a requested result.")
    save(out / "receipt.json", result)
    return result


def run_orders(specs, guest, ask, out, bank, rounds=3, memory_view="contract", **options):
    """Run a batch in order, then revisit public failures with any newly learned rules."""
    if not specs:
        raise ValueError("provide at least one work order")
    directories = [out] if len(specs) == 1 else [out / f"order-{i:03d}" for i in range(1, len(specs) + 1)]
    results = []
    for spec, directory in zip(specs, directories):
        results.append(work(spec, guest, ask, directory, bank, rounds, memory_view, **options))
    if len(specs) > 1 and bank is not None:
        for i, (spec, directory, result) in enumerate(zip(specs, directories, results)):
            if result.get("status") in ("needs_generation", "public_failed") or (
                    result.get("attempts") and result["public"] < result["examples"]):
                results[i] = work(spec, guest, None, directory, bank, rounds, memory_view, **options)
    return results


def selected_members(names):
    from team import ternary

    if names != ["auto"]:
        return names
    installed = [name for name in ternary.roster() if name != "coder"]
    if not installed:
        raise ValueError("no installed hive member was found")
    first = next((name for name in installed if ternary.leans(name) == "code"), installed[0])
    return list(dict.fromkeys((first, installed[0])))


def main(argv=None):
    from team import config, ternary

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", type=Path, required=True, action="append",
                   help="work-order JSON, repeat in teaching order to revisit earlier public failures")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--sdk", type=Path, default=config.fieldwork_sdk_path())
    for k in ("binary", "weights"):
        p.add_argument("--" + k, type=Path, help="needed when generating a new worker")
    p.add_argument("--adapter", type=Path)
    p.add_argument("--member", action="append", help="installed writer, repeat for a different cell on public failure; "
                   "'auto' chooses the installed coding specialist and shared model")
    p.add_argument("--bank", type=Path, help="skill directory (default HIVE_BANK or runs/learned-skills)")
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--budget", type=int, default=1400, help="maximum generated tokens per attempt")
    p.add_argument("--repair-budget", type=int, default=8, choices=range(9),
                   help="maximum candidate repairs tested on public examples per search")
    p.add_argument("--challenge", type=int, choices=(0, 1, 2), default=0,
                   help="check up to this many learned rival programs before delivering an otherwise qualified answer")
    p.add_argument("--no-learned-repairs", action="store_true",
                   help="use only the built-in repairs and do not learn repair rules")
    p.add_argument("--concise", action="store_true", help="request code without inline explanations")
    p.add_argument("--memory-view", choices=("contract", "source"), default="contract")
    args = p.parse_args(argv)
    if args.challenge and args.no_learned_repairs:
        p.error("--challenge requires learned repairs to be enabled")
    if min(args.rounds, args.threads, args.budget) < 1:
        p.error("rounds, threads and budget must be positive")
    if args.member and (args.binary or args.weights or args.adapter):
        p.error("--member selects both weights and runtime")
    if args.member and "auto" in args.member and args.member != ["auto"]:
        p.error("use --member auto alone or name each member")
    if bool(args.binary) != bool(args.weights) or (args.adapter and not args.weights):
        p.error("supply both --binary and --weights when selecting a local model by path")
    specs = [json.loads(path.read_text()) for path in args.spec]
    if args.challenge and any(not validation_set_id(s) for s in specs):
        p.error("--challenge requires disjoint public and qualification inputs in each work order")
    try:
        g = Guest(args.sdk)
    except FileNotFoundError:
        p.error("install the WebAssembly guest using python scripts/setup_fieldwork.py or supply --sdk")
    bank = args.bank if args.bank is not None else config.saved_bank_path()
    with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
        # Only one model is resident. A new work order starts with its first writer.
        backend = stack.enter_context(contextlib.ExitStack())
        members, active, url = None, None, None

        def ask(seat, task, prefix, prior):
            nonlocal members, active, url
            if args.member and members is None:
                try:
                    members = selected_members(args.member)
                except ValueError as exc:
                    p.error(str(exc))
            member = members[seat % len(members)] if members else None
            if url is None or member != active:
                backend.close()
                binary, weights, adapter = args.binary, args.weights, args.adapter
                if member:
                    base, _ = ternary.split(member)
                    binary, weights, adapter = ternary.binary(), ternary.weights(base), ternary.adapter(member)
                url = backend.enter_context(server(binary, weights, Path(tmp) / "server.log", adapter, args.threads))
                active = member
            row = generate(url, task, prefix, prior, focused=True, concise=args.concise, budget=args.budget)
            row["writer"] = member or str(args.adapter or args.weights)
            return row

        generator = None
        if args.member or args.binary:
            seats = 2 if args.member == ["auto"] else len(args.member or [None])
            generator = [partial(ask, seat) for seat in range(seats)]
        results = run_orders(specs, g, generator, args.out, bank, args.rounds, args.memory_view,
                             repair_budget=args.repair_budget, learn_repairs=not args.no_learned_repairs,
                             challenge_budget=args.challenge)
    success = True
    for spec, score in zip(specs, results):
        jobs = spec.get("jobs", [])
        delivered = sum("value" in row for row in score["jobs"])
        print(f"{spec['name']}: {score['public']}/{score['examples']} examples, "
              f"{score['validated']}/{score['validation_total']} independent checks, {delivered}/{len(jobs)} jobs delivered")
        if score.get("reason"):
            print(score["reason"])
        if (score.get("status") in ("ambiguous_saved_versions", "needs_generation", "challenge_ambiguous", "challenge_inconclusive")
                or score["public"] != score["examples"] or score["validated"] != score["validation_total"]
                or delivered != len(jobs)):
            success = False
    return int(not success)


if __name__ == "__main__":
    raise SystemExit(main())
