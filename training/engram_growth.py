"""Keep checked local lessons and refresh compact, independently tested native label adapters."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from team import config, engram_index
from team.signals import DOMAINS

SCHEMA = """
CREATE TABLE IF NOT EXISTS examples (
    id TEXT PRIMARY KEY, domain TEXT, topic TEXT, prompt TEXT, answer TEXT, split TEXT);
CREATE INDEX IF NOT EXISTS training_group ON examples(domain,topic,prompt);
CREATE TABLE IF NOT EXISTS evidence (
    example TEXT, origin TEXT, PRIMARY KEY(example,origin));
CREATE TABLE IF NOT EXISTS builds (
    revision TEXT PRIMARY KEY, domain TEXT, topic TEXT, result TEXT);
"""


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _id(*values):
    return hashlib.sha256(_json(values).encode()).hexdigest()


def _store(home=None):
    return Path(home or os.environ.get("HIVE_LEARNING_HOME") or config.RUNS / "engram-learning").expanduser()


def enabled():
    return os.environ.get("HIVE_ENGRAM_LEARN", "1").strip().lower() not in {"0", "off", "false"}


@contextlib.contextmanager
def _database(home):
    home = _store(home)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = home / "lessons.sqlite3"
    os.close(os.open(path, os.O_CREAT | os.O_NOFOLLOW | os.O_RDONLY, 0o600))
    with contextlib.closing(sqlite3.connect(path, timeout=30)) as db:
        db.executescript(SCHEMA)
        db.row_factory = sqlite3.Row
        with db:
            yield db


def _edit_home(path):
    from team import ternary
    return Path(path or ternary.ENGRAMS)


def _retire(rows, group, affected):
    return [dict(row, folded="contradictory checked examples") if row.get("growth_group") == group and not row.get("folded")
            and affected.intersection(row.get("growth_example_ids", [])) else row for row in rows]


def record(domain, topic, prompt, answer, origin, *, home=None, edit_home=None, split_hint=None):
    """Keep answers and independent provenance; conflicting targets remain inspectable and unfit."""
    if (domain not in DOMAINS or not all(isinstance(s, str) and s.strip() for s in (topic, prompt))
            or not isinstance(answer, str)):
        raise ValueError("expected a supported domain, a nonempty topic and prompt, and a text answer")
    topic, prompt = topic.strip(), prompt.strip()
    ident = _id(domain, topic, prompt, answer)
    with _database(home) as db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT id,split FROM examples WHERE domain=? AND topic=? AND prompt=?",
                              (domain, topic, prompt)).fetchall()
        conflicting = any(r["id"] != ident for r in previous)
        existing = any(r["id"] == ident for r in previous)
        split_conflict = (split_hint is not None and previous
                          and any(r["split"] != split_hint for r in previous))
        if split_conflict:
            # Independent shard enrollments can disagree about the role of a repeated prompt.
            # Quarantine it on restore rather than testing a prompt used for a fit elsewhere.
            split = "excluded"
            db.execute("UPDATE examples SET split=? WHERE domain=? AND topic=? AND prompt=?", (split, domain, topic, prompt))
        elif previous:
            split = previous[0]["split"]
        elif split_hint is not None:
            split = split_hint
        else:
            count, = db.execute("SELECT count(*) FROM examples WHERE domain=? AND topic=? AND answer=?",
                                (domain, topic, answer)).fetchone()
            # Assignment persists on arrival. A qualification prompt never migrates into training.
            split = "validation" if count % 4 == 2 else "train"
        group = _id(domain, topic)
        if ((conflicting and not existing) or split_conflict) and (_edit_home(edit_home) / "index.jsonl").is_file():
            from team import engram
            engram.update_index(lambda rows: _retire(rows, group, {r["id"] for r in previous}), home=_edit_home(edit_home))
        db.execute("INSERT OR IGNORE INTO examples VALUES(?,?,?,?,?,?)", (ident, domain, topic, prompt, answer, split))
        db.execute("INSERT OR IGNORE INTO evidence VALUES(?,?)", (ident, _json(origin)))
    return {"status": "conflict" if conflicting else ("known" if existing else "recorded"), "id": ident, "split": split}


def _domain(field, kind):
    terms = set(re.findall(r"[a-z]+", (field + " " + kind).lower()))
    for d, keys in [("machine_learning", {"regression", "classifier", "gradient", "neural", "training"}),
                    ("physical_science", {"physics", "force", "energy", "temperature", "chemical"}),
                    ("computer_engineering", {"cache", "circuit", "register", "processor", "binary"}),
                    ("math", {"math", "arithmetic", "algebra", "prime", "number", "fractions"}),
                    ("coding", {"code", "coding", "program", "python", "module", "data"}),
                    ("conversation", {"writing", "words", "chat", "conversation", "language"})]:
        if keys & terms:
            return d
    return None


def _normal_domain(text, field, kind):
    domain = _domain(field, kind)
    if domain:
        return domain
    from team.signals import read_request
    decision = read_request(text)
    return decision.get("domain") if decision else None


def record_practice(directory, prompt, field, kind, receipt, *, home=None):
    if not enabled():
        return []
    directory = Path(directory)
    phase = re.fullmatch(r"practice_([0-9]+)", directory.parent.name)
    if not phase or not re.fullmatch(r"[ech]" + phase[1] + r"_[0-9]+", directory.name):
        return []
    if (receipt.get("id") != directory.name
            or receipt.get("practice_prompt_sha256") != hashlib.sha256(prompt.encode()).hexdigest()):
        return []
    domain = _normal_domain(prompt, field, kind)
    if domain is None:
        return []
    rows = []
    for verdict in receipt.get("members") or []:
        if not isinstance(verdict, dict):
            continue
        n = verdict.get("member")
        if verdict.get("ok") is not True or type(n) is not int or n < 1:
            continue
        path = directory / "members" / f"member{n}.json"
        try:
            raw = path.read_bytes()
            member = json.loads(raw)
        except (OSError, ValueError):
            continue
        answer = member.get("answer")
        if (not isinstance(member.get("who"), str) or member["who"] != verdict.get("who")
                or hashlib.sha256(raw).hexdigest() != verdict.get("submission_sha256")
                or not isinstance(answer, str) or not answer.strip()):
            continue
        rows.append(record(domain, kind, prompt, answer, {"type": "practice_member_check", "practice": directory.parent.name,
                           "task": directory.name, "member": n, "who": member["who"],
                           "submission_sha256": hashlib.sha256(raw).hexdigest()}, home=home))
    return rows


def _practice_record(domain, topic, prompt, answer, origin, split):
    if (not isinstance(origin, dict) or origin.get("type") != "practice_member_check"
            or set(origin) != {"type", "practice", "task", "member", "who", "submission_sha256"}):
        raise ValueError("expected checked generated practice observations")
    phase = re.fullmatch(r"practice_([0-9]+)", str(origin.get("practice", "")))
    if (domain not in DOMAINS or split not in ("train", "validation", "excluded") or not phase or not re.fullmatch(r"[ech]" + phase[1] + r"_[0-9]+", str(origin.get("task")))
            or not isinstance(origin.get("who"), str) or type(origin.get("member")) is not int or origin["member"] < 1
            or not re.fullmatch(r"[0-9a-f]{64}", str(origin.get("submission_sha256")))
            or not isinstance(answer, str)
            or not all(isinstance(v, str) and v.strip() == v and v for v in (topic, prompt))):
        raise ValueError("invalid practice provenance or lesson")
    fields = dict(domain=domain, topic=topic, prompt=prompt, answer=answer, origin=origin, split=split)
    return {**fields, "record_sha256": _id("practice-export-v1", fields)}


def _write_practice(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
        tmp = Path(out.name)
        try:
            for row in rows:
                out.write(_json(row) + "\n")
            out.flush()
            os.fsync(out.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


def export_practice(phase, path, *, home=None):
    """Export only one generated practice sitting. Local user labels and work orders are never included."""
    with _database(home) as db:
        raw = db.execute("""
            SELECT domain,topic,prompt,answer,origin,split FROM examples JOIN evidence ON example=id
            WHERE json_extract(origin,'$.type')='practice_member_check' AND json_extract(origin,'$.practice')=?
            ORDER BY examples.rowid,origin""", (phase,))
        _write_practice(path, (_practice_record(d,t,p,a,json.loads(o),split) for d,t,p,a,o,split in raw))


def _read_export(path, expected=None):
    data = Path(path).read_bytes()
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"file digest mismatch: {path}")
    result = []
    for i, line in enumerate(data.splitlines(), 1):
        try:
            row = json.loads(line)
            canonical = _practice_record(**{k: row[k] for k in ("domain", "topic", "prompt", "answer", "origin", "split")})
            if canonical != row:
                raise ValueError("record digest or fields differ")
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"invalid checked practice record at {path}:{i}") from exc
        result.append(canonical)
    return result


def pack_practice(roots, out):
    records = {}
    for root in roots:
        for path in sorted(Path(root).rglob("rows.engrams.jsonl")):
            for row in _read_export(path):
                records.setdefault(row["record_sha256"], row)
    # Preserve deterministic shard and enrollment order so that the original split can be replayed.
    _write_practice(out, records.values())
    return {"practice_observations": len(records)}


def restore_practice(path, expected=None, *, home=None, edit_home=None):
    counts = Counter()
    for row in _read_export(path, expected):
        fields = {k: row[k] for k in ("domain", "topic", "prompt", "answer", "origin")}
        status = record(**fields, home=home, edit_home=edit_home, split_hint=row["split"])["status"]
        counts[status] += 1
    return dict(counts)


def record_work(spec, receipt, *, home=None):
    from training.experiments.fieldwork.work import validation_set_id
    if (not enabled() or receipt.get("status") or receipt.get("admission") == "overlapping_checks"
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("digest"))) or not validation_set_id(spec)
            or receipt.get("public") != len(spec["examples"]) or receipt.get("validated") != len(spec["validation"])
            or len(receipt.get("jobs", [])) != len(spec.get("jobs", [])) or any("value" not in r for r in receipt["jobs"])):
        return []
    domain = spec.get("domain") or _normal_domain(spec["task"], "", "") or "coding"
    if domain not in DOMAINS:
        return []
    topic = spec["task"].strip()
    rows = []
    for example in spec["examples"]:
        label = example["output"]
        answer = label if isinstance(label, str) else _json(label)
        rows.append(record(domain, topic, topic + "\nInput: " + _json(example["input"]), answer,
                           {"type": "public_work_example", "task": spec["name"], "qualified_solver": receipt["digest"],
                            "expected_json_sha256": _id(label), "independent_checks": receipt["validated"]}, home=home))
    return rows


def _snapshot(db, domain, topic):
    # Retain complete file exports in the ledger, but do not load large free-form targets into the fitting process.
    conflicts, = db.execute("""SELECT count(*) FROM (SELECT prompt FROM examples WHERE domain=? AND topic=?
        GROUP BY prompt HAVING count(*) > 1)""", (domain, topic)).fetchone()
    entries = db.execute("""SELECT a.id,a.prompt,a.answer,a.split,a.rowid AS arrival FROM examples a
        WHERE a.domain=? AND a.topic=? AND length(a.prompt)<=4096 AND length(a.answer)<=24
        AND NOT EXISTS (SELECT 1 FROM examples b WHERE b.domain=a.domain AND b.topic=a.topic
                        AND b.prompt=a.prompt AND b.id!=a.id) ORDER BY a.id""", (domain, topic))
    return [dict(row) for row in entries], conflicts


def _partition(examples):
    # The native trainer verifies the exact tokenizer boundary. Keep multiword answers
    # in the durable evidence store without sending them to a single-token classifier.
    groups = defaultdict(lambda: {"train": [], "validation": []})
    for row in examples:
        if (row["split"] in ("train","validation") and len(row["prompt"]) <= 4096
                and 0 < len(row["answer"]) <= 24 and not re.search(r"\s", row["answer"])):
            groups[row["answer"]][row["split"]].append(row)
    train, qualification = [], []
    labels = sorted(groups, key=lambda label: (-len(groups[label]["train"]), label))
    for label in labels:
        rows = groups[label]
        if len(rows["train"]) >= 2 and rows["validation"]:
            train.extend(rows["train"][:12])
            qualification.extend(sorted(rows["validation"], key=lambda r: r["arrival"])[:6])
            if len(set(r["answer"] for r in train)) == 8:
                break
    return (train, qualification) if len({r["answer"] for r in train}) >= 2 else ([], [])


def _local_base():
    from team import ternary
    if os.environ.get("HIVE_ENGRAM_MODEL"):
        return Path(os.environ["HIVE_ENGRAM_MODEL"]).expanduser()
    try:
        from huggingface_hub import try_to_load_from_cache
        found = try_to_load_from_cache(*ternary.MODELS["t80"])
        return Path(found) if isinstance(found, str) else None
    except ImportError:
        return None


def stats(home=None):
    with _database(home) as db:
        groups = db.execute("SELECT domain,topic,count(*) FROM examples GROUP BY domain,topic ORDER BY domain,topic").fetchall()
        result = []
        for domain, topic, total in groups:
            rows, conflicts = _snapshot(db, domain, topic)
            fit, valid = _partition(rows)
            info = dict(domain=domain, topic=topic, examples=total, conflicting_prompts=conflicts,
                        fitting=len(fit), qualification=len(valid), split_conflicts=sum(r["split"] == "excluded" for r in rows))
            latest = db.execute("SELECT result FROM builds WHERE domain=? AND topic=? ORDER BY rowid DESC LIMIT 1",
                                (domain, topic)).fetchone()
            if latest:
                previous = json.loads(latest[0])
                info["last_build"] = {"status": previous["status"], "revision": previous["revision"]}
            result.append(info)
        return result


def _revision(rows, model, runtime, edit_home, version=None):
    def identity(path):
        stat = path.stat()
        return [str(path.resolve()), stat.st_size, stat.st_mtime_ns]
    return _id(version or engram_index.GROWTH_VALIDATION, sorted(r["id"] for r in rows),
               identity(model), identity(runtime), str(edit_home.resolve()))


def _legacy_source(db, rows, domain, topic, edit_home):
    """Find an immutable fit even after the store moves. Use its receipt for provenance only."""
    shelf = engram_index.shelf(edit_home, "t80")
    if not shelf:
        return None
    group, expected_ids = _id(domain, topic), [r["id"] for r in rows]
    for name in reversed(shelf.labels):
        row = shelf.records[name]
        if row.get("growth_group") != group or row.get("growth_example_ids") != expected_ids:
            continue
        if row.get("validation_version") is not None:
            return None
        revision, digest = row.get("revision"), row.get("sha256")
        if (not isinstance(revision, str) or not isinstance(digest, str) or not re.fullmatch("[a-f0-9]{64}", digest)
                or name != "eg" + _id(revision, digest)[:24]):
            continue
        stored = db.execute("SELECT result FROM builds WHERE revision=? AND domain=? AND topic=?", (revision, domain, topic)).fetchone()
        if stored:
            previous = json.loads(stored[0])
            if previous.get("status") == "published" and previous.get("name") == name and previous.get("sha256") == digest:
                return row
    return None


def _recheck(row, artifact, training, valid, edit_home, model, runtime, threads):
    from training import domain_engram
    old_path = edit_home / ("t80+" + row["name"] + ".gguf")
    if old_path.is_symlink() or not old_path.is_file():
        return None
    data = old_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != row["sha256"]:
        return None  # Rebuild from checked lessons when the immutable bytes cannot be recovered.
    stat = model.stat()
    if domain_engram._base_hash(model, (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)) != domain_engram.T80_SHA256:
        raise ValueError("only the released Ternary-Bonsai-8B-PQ2_0 base can requalify t80 engrams")
    artifact.write_bytes(data)
    score = domain_engram.validate(valid, artifact, model=model, runtime=runtime, threads=threads)
    return dict(sha256=row["sha256"], base_sha256=domain_engram.T80_SHA256, labels=sorted({r["answer"] for r in valid}),
                training_rows=len(training), rechecked_revision=row["revision"], validation=score)


def _cues(train, topic):
    noise = {"answer", "choose", "input", "output", "what", "with", "this", "that", "return", "which", "from", "write", "please"}
    tokens = lambda text: {s for s in re.findall(r"[a-z]{4,}", text.lower()) if s not in noise}
    counts = Counter(token for row in train for token in tokens(row["prompt"]))
    exclude = {r["answer"].casefold() for r in train} | {"classify", "label", "select", "respond", "instruction"}
    return sorted((s for s in (tokens(topic) | set(counts)) - exclude if counts[s] >= 2),
                  key=lambda s: (-counts[s], s))[:10]


def _measured_wins(proof, valid):
    """Verify that scalar totals describe the actual reserved prompts, in order."""
    score = proof.get("validation") or {}
    before, after, count = (score.get(key) for key in ("before", "after", "count"))
    cases = score.get("cases", [])
    labels = proof.get("labels", [])
    if (type(before) is not int or type(after) is not int or type(count) is not int or count != len(valid)
            or not 0 <= before < after <= count or score.get("regressions") != 0
            or set(labels) != {r["answer"] for r in valid} or len({x.casefold() for x in labels}) != len(labels)
            or len(cases) != count):
        return None
    wins = []
    original_correct = 0
    for case, row in zip(cases, valid):
        if (case.get("expected") != row["answer"]
                or case.get("prompt_sha256") != hashlib.sha256(row["prompt"].encode()).hexdigest()
                or type(case.get("before_correct")) is not bool or type(case.get("after_correct")) is not bool
                or (case["before_correct"] and not case["after_correct"])):
            return None
        original_correct += int(case["before_correct"])
        if case["after_correct"]:
            wins.append(row["id"])
    return wins if original_correct == before and len(wins) == after else None


def _install_weights(data, destination, digest, *, recover=False):
    if destination.is_symlink():
        raise ValueError("published edit name is a symbolic link")
    if destination.is_file():
        if hashlib.sha256(destination.read_bytes()).hexdigest() == digest:
            return
        if not recover:
            raise ValueError("unowned edit name already contains different bytes")
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as staged:
        tmp = Path(staged.name)
        try:
            staged.write(data)
            staged.flush()
            os.fsync(staged.fileno())
            os.replace(tmp, destination)
        finally:
            tmp.unlink(missing_ok=True)


def _publish(result, artifact, training, valid, edit_home):
    from team import engram
    proof, topic, domain = result["measurement"], result["topic"], result["domain"]
    wins = _measured_wins(proof, valid)
    cues = _cues(training, topic)
    if not wins or not cues or not artifact.is_file():
        return
    data = artifact.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != proof.get("sha256"):
        raise ValueError("trainer artifact hash disagrees with measurement")
    revision = result["revision"]
    name, group = "eg" + _id(revision, digest)[:24], _id(domain, topic)
    destination = edit_home / ("t80+" + name + ".gguf")
    row = dict(name=name, dna="t80", task=topic, cell=None, domain=domain, form="label", cues=cues,
               labels=sorted(proof["labels"]), verified=True, qualification_wins=wins, validation_version=engram_index.GROWTH_VALIDATION,
               growth_example_ids=[r["id"] for r in training + valid], growth_group=group, revision=revision, sha256=digest)

    def publish(index):
        migration = proof.get("rechecked_revision")
        if migration and not any(old.get("growth_group") == group and old.get("revision") == migration
                                 and old.get("sha256") == digest and not old.get("archived") and old.get("folded") is None
                                 for old in index):
            result.update(status="source_retired")
            return None
        same_name = [old for old in index if old.get("dna") == "t80" and old.get("name") == name]
        identity = ("revision", "sha256", "growth_group")
        if any(any(old.get(k) != row[k] for k in identity) for old in same_name):
            raise ValueError("native edit name already belongs to a different revision")
        for old in index:
            if (old.get("growth_group") == group and not old.get("folded") and not old.get("archived")
                    and old.get("validation_version") == engram_index.GROWTH_VALIDATION
                    and not set(old.get("qualification_wins", [])).issubset(wins)):
                result.update(status="prior_wins_not_preserved")
                return None
        # Reconstitute corrupted bytes only for our exact indexed immutable revision.
        _install_weights(data, destination, digest, recover=bool(same_name))
        keep = [dict(x, folded=name) if x.get("growth_group") == group and not x.get("folded") else x
                for x in index if x.get("name") != name or x.get("dna") != "t80"]
        result.update(status="published", name=name, sha256=digest)
        return keep + [row]

    engram.update_index(publish, home=edit_home)


def refresh(*, domain=None, home=None, edit_home=None, model=None, runtime=None, threads=2, limit=None, trainer=None):
    """Build a bounded edit offline. Publish only a measured qualification gain on the pinned split."""
    from team import engram, ternary
    home, edit_home = _store(home), _edit_home(edit_home)
    if threads < 1:
        raise ValueError("threads must be positive")
    groups = [g for g in stats(home) if (domain is None or domain == g["domain"]) and g["fitting"]]
    if not groups:
        return [{"status": "waiting_for_labels"}]
    model = Path(model) if model else _local_base()
    runtime = Path(runtime) if runtime else ternary.binary()
    if model is None or not model.is_file() or not runtime.is_file():
        return [{"status": "missing_assets", "reason": "supply a local Ternary-Bonsai 8B GGUF and llama-server"}]
    if trainer is None:
        from training.domain_engram import train as trainer
    reports = []
    with (home / ".refresh.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return [{"status": "refresh_in_progress"}]
        for group in groups:
            d, topic = group["domain"], group["topic"]
            with _database(home) as db:
                rows, _ = _snapshot(db, d, topic)
                training, valid = _partition(rows)
                revision = _revision(training + valid, model, runtime, edit_home)
                prior = db.execute("SELECT result FROM builds WHERE revision=?", (revision,)).fetchone()
                legacy = _legacy_source(db, training + valid, d, topic, edit_home) if not prior else None
            if legacy and (legacy.get("folded") is not None or legacy.get("archived")):
                reports.append({"status": "retired", "revision": legacy["revision"], "domain": d, "topic": topic, "cached": True})
                continue
            if prior:
                previous = json.loads(prior[0])
                if previous["status"] == "published":
                    path = edit_home / ("t80+" + previous["name"] + ".gguf")
                    try:
                        matching = [r for r in engram._rows(edit_home / "index.jsonl")
                                    if r.get("name") == previous["name"] and r.get("dna") == "t80"
                                    and r.get("revision") == revision and r.get("sha256") == previous["sha256"]]
                        if matching and (matching[-1].get("folded") is not None or matching[-1].get("archived")):
                            reports.append({**previous, "status": "retired", "cached": True})
                            continue
                        present = (bool(matching) and matching[-1].get("validation_version") == engram_index.GROWTH_VALIDATION
                                   and hashlib.sha256(path.read_bytes()).hexdigest() == previous["sha256"])
                    except (OSError, ValueError):
                        present = False
                else:
                    present = True
                if present:
                    reports.append({**previous, "cached": True})
                    continue
            if not training:
                continue
            with tempfile.TemporaryDirectory(dir=home) as scratch:
                artifact = Path(scratch) / "candidate.gguf"
                project = lambda rows: [{"prompt": r["prompt"], "answer": r["answer"]} for r in rows]
                try:
                    held_out = project(valid)
                    proof = _recheck(legacy, artifact, training, held_out, edit_home, model, runtime, threads) if legacy else None
                    if proof is None:
                        proof = trainer(project(training), artifact, model=model, runtime=runtime, threads=threads, validation=held_out)
                except ValueError as exc:
                    proof = {"reason": str(exc)}
                except (OSError, ImportError, RuntimeError) as exc:
                    # A missing executable or transient native failure can be retried on the same evidence.
                    reports.append({"status": "runtime_unavailable", "domain": d, "topic": topic, "reason": str(exc)})
                    if limit is not None:
                        break
                    continue
                result = {"status": "unqualified", "revision": revision, "domain": d, "topic": topic,
                          "validation_version": engram_index.GROWTH_VALIDATION, "measurement": proof}
                with _database(home) as db:
                    db.execute("BEGIN IMMEDIATE")
                    now, _ = _snapshot(db, d, topic)
                    now_fit, now_valid = _partition(now)
                    if _revision(now_fit + now_valid, model, runtime, edit_home) != revision:
                        reports.append({**result, "status": "evidence_changed"})
                        continue
                    _publish(result, artifact, training, valid, edit_home)
                    db.execute("INSERT OR REPLACE INTO builds VALUES(?,?,?,?)", (revision, d, topic, _json(result)))
            reports.append(result)
            if limit is not None and sum(not r.get("cached") for r in reports) >= limit:
                break
    return reports


def list_native(base="t80"):
    from team import engram, ternary
    seen = set()
    listed = []
    for home in ternary.engram_homes():
        origin = "shipped" if home == ternary.BUNDLED_ENGRAMS else "local"
        for name, (_, row) in sorted(engram.bank_entries(base, home).items()):
            if name in seen:
                continue
            seen.add(name)
            if row and row.get("verified") is True:
                topic = " ".join((row.get("task") or name).split())
                if len(topic) > 100:
                    topic = topic[:97] + "..."
                domain = (row.get("domain") or "general").replace("_", " ")
                listed.append(f"{domain} | {topic} ({origin}, {base}+{name})")
    return listed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    listing = sub.add_parser("list", help="list verified native topics compatible with a base model")
    listing.add_argument("--base", default="t80", choices=("t17", "t40", "t80"))
    pack = sub.add_parser("pack-practice", help="combine generated practice shard sidecars")
    pack.add_argument("--from", dest="roots", nargs="+", type=Path, required=True)
    pack.add_argument("--out", required=True, type=Path)
    restore = sub.add_parser("restore", help="import checked generated-practice observations from a trusted local release file")
    restore.add_argument("--practice-file", required=True, type=Path)
    restore.add_argument("--sha256", help="expected complete release file digest")
    restore.add_argument("--home", type=Path)
    restore.add_argument("--engram-home", type=Path)
    for action in ("status", "teach", "refresh"):
        p = sub.add_parser(action)
        p.add_argument("--home", type=Path, help="local lesson directory")
        if action != "status":
            p.add_argument("--domain", choices=DOMAINS, required=action == "teach")
            p.add_argument("--engram-home", type=Path, help="native learned edit directory")
        if action == "teach":
            p.add_argument("--topic", help="group that shares one label contract; defaults to the domain")
            p.add_argument("--prompt", required=True)
            p.add_argument("--answer", required=True)
        if action == "refresh":
            p.add_argument("--model", type=Path)
            p.add_argument("--runtime", type=Path)
            p.add_argument("--threads", type=int, default=2)
    a = parser.parse_args(argv or ["status"])
    if a.action == "list":
        print("\n".join(list_native(a.base)) or f"No verified native topics available for {a.base}.")
        return 0
    if a.action == "pack-practice":
        output = pack_practice(a.roots, a.out)
    elif a.action == "restore":
        embedded = re.search(r"-([0-9a-f]{64})\.jsonl$", a.practice_file.name)
        output = restore_practice(a.practice_file, a.sha256 or (embedded[1] if embedded else None),
                                  home=a.home, edit_home=a.engram_home)
    elif a.action == "status":
        output = stats(a.home)
    elif a.action == "teach":
        output = record(a.domain, a.topic or a.domain, a.prompt, a.answer, {"type": "explicit_user_label"},
                        home=a.home, edit_home=a.engram_home)
    else:
        output = refresh(domain=a.domain, home=a.home, edit_home=a.engram_home, model=a.model,
                         runtime=a.runtime, threads=a.threads)
    print(json.dumps(output, indent=2))
    return int(isinstance(output, list) and any(r.get("status") in ("missing_assets", "runtime_unavailable") for r in output))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
