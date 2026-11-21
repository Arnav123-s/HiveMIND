"""Reconcile a completed read-only CPU growth run's jobs, training logs, grade zips, and record."""

from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile

from training import gate_look, grow_record, reads


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() if value else None


def schedule(jobs):
    """Throughput and active/queued runner time use intervals, so overlapping jobs do not inflate wall time."""
    stages = defaultdict(list)
    for j in jobs:
        stages[j["name"].split(" (")[0]].append(j)

    def time_bounds(group):
        valid = [
            j
            for j in group
            if j["conclusion"] != "skipped"
            and j.get("runner_id", 1)
            and j.get("completed_at")
            and j.get("started_at")
        ]
        if not valid:
            return {"outcomes": dict(Counter(j["conclusion"] for j in group))}
        queue, execs = [], []
        for job in valid:
            start, end = timestamp(job["started_at"]), timestamp(job["completed_at"])
            created = timestamp(job.get("created_at"))
            if end <= start or created is None:
                continue
            execs.append((start, end))
            if created < start:
                queue.append((created, start))
        edges = Counter()
        for a, b in execs:
            edges[a] += 1
            edges[b] -= 1
        active = high = 0
        for t in sorted(edges):
            active += edges[t]
            high = max(high, active)
        return {
            "outcomes": dict(Counter(j["conclusion"] for j in group)),
            "first_runner_at": min(j["started_at"] for j in valid),
            "last_runner_finished_at": max(j["completed_at"] for j in valid),
            "span_seconds": int(max(b for a, b in execs) - min(a for a, b in execs)) if execs else 0,
            "peak_runners": high,
            "runner_seconds": int(sum(b - a for a, b in execs)),
            "queued_runner_seconds": int(sum(b - a for a, b in queue)),
            "longest_assignment_wait_seconds": int(max((b - a for a, b in queue), default=0)),
        }

    cohorts = defaultdict(list)
    for job in jobs:
        desc = re.fullmatch(r"(gate(?:_5_6|_7_8)?) \((before|after), [1-8], (fresh|held|talk)\)", job["name"])
        if desc:
            cohorts[f"{desc[1]}/{desc[3]}"].append(job)
    return {
        "phases": {s: time_bounds(g) for s, g in stages.items()},
        "whole": time_bounds(jobs),
        "gate_work_by_block": {s: time_bounds(g) for s, g in cohorts.items()},
    }


def interrupted(text):
    """Partial progress counters from grow.train. Its timed loop flushes any partial 4-row accumulation before reporting memory."""
    heartbeats = re.findall(r"^step (\d+) \(.*?, (\d+) rows skipped$", text, re.M)
    done = re.search(r"^time is up after (\d+) passes:", text, re.M)
    memory = re.search(r"^memory: most ([\d.]+) GB,", text, re.M)
    skips = re.search(r"^memory guard: (\d+) passes skipped", text, re.M)
    length = re.search(r"^(\d+) rows are longer than (\d+) pieces", text, re.M)
    dtype = re.search(r"^this machine: (.*?), (\d+) threads; trained in (.*)$", text, re.M)
    final = bool(memory and done)
    passes = int(done[1]) if done else None
    return {
        "observed_steps": (passes + 3) // 4 if final else int(heartbeats[-1][0]) if heartbeats else None,
        "count_final": final,
        "observed_guard_skips": (int(skips[1]) if skips else 0)
        if memory
        else int(heartbeats[-1][1])
        if heartbeats
        else None,
        "guard_final": bool(memory),
        "final_passes": passes if final else None,
        "too_long": int(length[1]) if length else None,
        "token_limit": int(length[2]) if length else None,
        "cpu": dtype[1] if dtype else None,
        "precision": dtype[3]
        if dtype
        else "32-bit numbers"
        if "this CPU has no quick 16-bit arithmetic" in text
        else None,
        "peak_memory_gb": float(memory[1]) if memory else None,
    }


def training(folder, jobs, facts):
    """A skipped attempt may later succeed. Unreached and too-long rows are distinct from final memory omissions."""
    named = {s["job"]: s for s in facts.get("slices", []) if s.get("record")}
    totals = Counter()
    rows = []
    partial = folder / "progress-lines.json"
    signals = json.loads(partial.read_text()) if partial.exists() else {}
    for job in (j for j in jobs if j["name"].startswith("train (")):
        rec = {}
        log_path = folder / f"train-{job['id']}.json"
        log = json.loads(log_path.read_text()) if log_path.exists() else {}
        direct = log.get("record")
        from_record = (named.get(job["name"]) or {}).get("record")
        if (
            direct
            and from_record
            and any(
                direct.get(k) != from_record.get(k)
                for k in ("member", "shard", "steps", "passes", "rows_by_kind")
            )
        ):
            raise ValueError(f"slice provenance disagreement: {job['id']}")
        raw = folder / f"{job['id']}.log"
        text = (
            reads.strip_log(raw.read_text()) if raw.is_file() else "\n".join(signals.get(str(job["id"]), []))
        )
        if raw.is_file() and not direct:
            direct = reads.record_in_log(text)
        measured = direct or from_record
        if measured:
            rec = {
                k: measured[k]
                for k in (
                    "member",
                    "shard",
                    "steps",
                    "passes",
                    "seconds",
                    "used",
                    "dtype",
                    "loss_chunk_tokens",
                    "int8_base",
                    "memory_gb",
                    "seconds_a_row",
                    "checkpoint",
                    "gpu",
                )
                if k in measured
            }
            if isinstance(measured.get("rows_by_kind"), dict):
                counts = Counter()
                for by_kind in measured["rows_by_kind"].values():
                    if not all(
                        type(by_kind.get(k)) == int
                        for k in ("given", "trained", "too_long", "skipped_memory")
                    ):
                        raise ValueError(f"incomplete row counts: {job['id']}")
                    counts.update({k: by_kind[k] for k in ("given", "trained", "too_long", "skipped_memory")})
                counts["unreached"] = counts["given"] - sum(
                    counts[k] for k in ("trained", "too_long", "skipped_memory")
                )
                if counts["unreached"] < 0:
                    raise ValueError(f"negative unreached count: {job['id']}")
                rec["new_rows"] = dict(counts)
                totals.update({"new_" + k: v for k, v in counts.items()})
                totals["new_coverage_measured_jobs"] += 1
            totals["jobs_with_metadata"] += 1
            for k in ("steps", "passes"):
                totals[k] += measured[k]
            if "rows_skipped" in (memory := measured.get("memory", {})):
                rec["guard_skipped_attempts"] = memory["rows_skipped"]
                rec["guard_mode_passes"] = memory.get("row_modes", {})
                rec["guard_mode_changes"] = memory.get("mode_changes")
                rec["training_length_limit"] = memory.get("training_max_len")
                if log.get("all_memory_skip_attempts") not in (None, memory["rows_skipped"]):
                    raise ValueError(f"guard log disagrees with final counts: {job['id']}")
                totals["jobs_with_guard_metadata"] += 1
                totals["guard_skipped_attempts"] += memory["rows_skipped"]
                for k, v in rec["guard_mode_passes"].items():
                    totals["guard_passes_" + k] += v
            long = log.get("all_too_long")
            if long is not None:
                rec["all_too_long"] = long
                totals["jobs_with_length_metadata"] += 1
                totals["all_too_long"] += long
            rec["source"] = "job log" if direct else "generation facts"
        if text and not measured:
            seen = interrupted(text)
            rec["partial"] = seen
            totals["jobs_with_partial_logs"] += 1
            if seen["observed_steps"] is not None:
                totals["jobs_with_observed_steps"] += 1
                totals["observed_steps_lower_bound"] += seen["observed_steps"]
            if seen["count_final"]:
                totals["jobs_with_final_update_count"] += 1
                totals["steps_in_finished_loops"] += seen["observed_steps"]
            if seen["observed_guard_skips"] is not None:
                totals["jobs_with_observed_guard_count"] += 1
                totals["observed_guard_skips_lower_bound"] += seen["observed_guard_skips"]
            if seen["guard_final"]:
                totals["jobs_with_final_guard_count"] += 1
            if seen["too_long"] is not None:
                totals["jobs_with_length_metadata"] += 1
                totals["all_too_long"] += seen["too_long"]
        rows.append({"job_id": job["id"], "job": job["name"], "conclusion": job["conclusion"], **rec})
    totals["jobs"] = len(rows)
    return {"totals": dict(totals), "slices": rows}


def report(folder):
    run = json.loads((folder / "run.json").read_text())
    jobs = json.loads((folder / "jobs.json").read_text())
    if run["status"] != "completed" or any(j["status"] != "completed" for j in jobs):
        raise ValueError("wait for the run and every job to complete")
    end = max(j["completed_at"] for j in jobs if j.get("conclusion") != "skipped" and j.get("completed_at"))
    artifacts = json.loads((folder / "artifacts.json").read_text())
    by_name = {a["name"]: a for a in artifacts}
    hashes = {}
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        facts, line = {}, {}
        for name, artifact in sorted(by_name.items()):
            record = name == "full-generation-record"
            intake = name in ("all-rows", "lessons")
            if not record and not intake and not re.fullmatch(r"(?:gate|held)-(?:before|after)-[1-8]", name):
                continue
            zfile = folder / (name + ".zip")
            if not zfile.is_file():
                continue
            digest = hashlib.sha256(zfile.read_bytes()).hexdigest()
            if artifact.get("digest") != "sha256:" + digest:
                raise ValueError(f"unverified {name}")
            hashes[name] = {"id": artifact["id"], "sha256": digest}
            with ZipFile(zfile) as z:
                if intake:
                    if name == "all-rows":
                        data = [json.loads(t) for t in z.read("rows.jsonl").splitlines() if t]
                        hashes[name]["rows"] = len(data)
                        hashes[name]["new_rows"] = sum(r.get("gen") == f"g{run['run_number']}" for r in data)
                    continue
                if record:
                    facts = json.loads(z.read("facts.json"))
                    lines = [
                        json.loads(text)
                        for text in z.read("training/reports/generations.jsonl").splitlines()
                        if text.strip()
                    ]
                    found = [r for r in lines if r["generation"] == f"g{run['run_number']}"]
                    if len(found) != 1:
                        raise ValueError("wrong generation record")
                    line = found[0]
                else:
                    (member,) = z.namelist()
                    if Path(member).name != member or not member.endswith(".json"):
                        raise ValueError("unexpected grade filename")
                    (dest / name).mkdir()
                    (dest / name / member).write_bytes(z.read(member))
        paired, seeds = grow_record.paired(dest)
        held = grow_record.held_exam(dest)
        arms = {
            arm: {
                k: r[k]
                for k in ("passed", "tasks", "seeds", "hard", "easy", "member_delivery", "unpractised")
                if k in r
            }
            for arm, r in paired.items()
        }
        seed_bases = set()
        for shard in dest.glob("gate-*-*"):
            for summary, _ in grow_record._sittings(shard):
                seat = int(shard.name.rsplit("-", 1)[1])
                encoded = summary["seed"] - 20_000_000 - seat
                if encoded % 10:
                    raise ValueError("unexpected gate seed")
                seed_bases.add(encoded // 10)
        if len(seed_bases) > 1:
            raise ValueError("mixed gate seed streams")
        base = next(iter(seed_bases), run["run_number"])
        looks = {}
        for n in (4, 6):
            short = dest / f"look-{n}"
            short.mkdir()
            for shard in dest.glob("gate-*-*"):
                if int(shard.name.rsplit("-", 1)[1]) <= n:
                    (short / shard.name).symlink_to(shard, target_is_directory=True)
            looks[n] = gate_look.look(short, base, n)
        if line:
            for arm in ("before", "after"):
                claimed = (line.get("paired") or {}).get(arm) or {}
                if claimed and (claimed["passed"], claimed["tasks"]) != (
                    arms[arm]["passed"],
                    arms[arm]["tasks"],
                ):
                    raise ValueError(f"grade/record disagreement in {arm} fresh results")
                if (line.get("held_exam") or {}).get(arm, {}).get("right") not in (
                    None,
                    (held.get(arm) or {}).get("right"),
                ):
                    raise ValueError(f"grade/record disagreement in {arm} held results")
        return {
            "run": {
                k: run[k]
                for k in (
                    "id",
                    "html_url",
                    "run_number",
                    "head_sha",
                    "head_branch",
                    "conclusion",
                    "created_at",
                    "run_started_at",
                    "updated_at",
                )
            },
            "cancel_annotation": json.loads((folder / "annotations.json").read_text())
            if (folder / "annotations.json").is_file()
            else None,
            "last_job_completed": end,
            "wall_seconds": int(timestamp(end) - timestamp(run["created_at"])),
            "timing": schedule(jobs),
            "training": training(folder, jobs, facts),
            "generation": {
                k: line[k] for k in ("generation", "verdict", "kept", "why", "trial", "grow") if k in line
            },
            "fresh": {
                "paired_seats": seeds,
                "arms": arms,
                "delivery_changes": grow_record.delivery_changes(dest),
            }
            if seeds
            else None,
            "artifacts_published_by_kind": dict(Counter(a["name"].split("-")[0] for a in artifacts)),
            "missing_full_generation_record": "full-generation-record" not in hashes,
            "held": held or None,
            "gate_seed_stream": base if seeds else None,
            "independent_gate_looks": looks if seeds else {},
            "artifacts": hashes,
            "facts_missing": facts.get("missing", []),
            "unavailable_artifacts": sorted(
                n
                for n in by_name
                if (n == "full-generation-record" or re.fullmatch(r"(?:gate|held)-(?:before|after)-[1-8]", n))
                and n not in hashes
            ),
        }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    args.out.write_text(json.dumps(report(args.folder), sort_keys=True, indent=2) + "\n")
