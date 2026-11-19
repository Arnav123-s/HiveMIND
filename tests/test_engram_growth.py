import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

from training import engram_growth as growth


def label(home, edits, i, answer):
    text = f"Oscillator feedback trial {i}: choose red or blue."
    return growth.record("computer_engineering", "oscillator feedback", text, answer, {"type": "explicit_user_label"},
                         home=home, edit_home=edits)


def test_conflicting_lesson_and_all_independent_origins_survive_retries(tmp_path):
    home = tmp_path / "ledger"
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(growth.record, "math", "sign", "Sign of an integer?", a, {"grader": g}, home=home)
                   for a, g in [("yes", "one"), ("yes", "two"), ("no", "three"), ("yes", "one")] * 3]
        for f in futures:
            f.result()
    info, = growth.stats(home)
    assert (info["examples"], info["conflicting_prompts"], info["fitting"]) == (2, 1, 0)
    with growth._database(home) as db:
        assert db.execute("SELECT count(*) FROM evidence").fetchone()[0] == 3
        assert len({r["split"] for r in db.execute("SELECT split FROM examples")}) == 1


def test_collection_requires_real_member_or_qualified_work_and_uses_only_public_inputs(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_ENGRAM_LEARN", "1")
    home = tmp_path / "home"
    run = tmp_path / "practice_10000001/e10000001_00"
    (run / "members").mkdir(parents=True)
    (run / "members/member1.json").write_text(json.dumps({"who": "t80", "answer": "east", "messages": ["SECRET_HISTORY"]}))
    for verdict in [{}, {"members": [{"member": 1, "ok": False, "who": "t80"}]},
                    {"members": [{"member": 1, "ok": True, "who": "other"}]}]:
        assert not growth.record_practice(run, "Which direction?", "math", "sign", verdict, home=home)
    from training import exam
    verdict = {"members": exam.each_member(run, lambda directory, answer: (answer == "east", ""), attest=True),
               "id":run.name, "practice_prompt_sha256":hashlib.sha256(b"Which direction?").hexdigest()}
    assert not growth.record_practice(run, "An unrelated task", "math", "sign", verdict, home=home)
    assert growth.record_practice(run, "Which direction?", "math", "sign", verdict, home=home)
    (run / "members/member1.json").write_text(json.dumps({"who": "t80", "answer": "tampered"}))
    assert not growth.record_practice(run, "Which direction?", "math", "sign", verdict, home=home)
    assert not growth.record_practice(tmp_path / "gate/run", "No", "math", "sign", verdict, home=home)
    spec = dict(name="pressure", domain="physical_science", task="Classify the pressure", examples=[{"input": "air", "output": "low"}],
                validation=[{"input": "SECRET_HELD_OUT", "output": "high"}], jobs=[{"input": "SECRET_JOB"}])
    ok = dict(digest="a"*64, public=1, validated=1, jobs=[{"id": "j", "value": "SECRET_JOB_ANSWER"}])
    assert growth.record_work(spec, ok, home=home)
    assert not growth.record_work(spec, {**ok, "status": "challenge_ambiguous"}, home=home)
    assert not growth.record_work({**spec, "validation": spec["examples"]}, ok, home=home)
    assert not growth.record_work(spec, {**ok, "validated": 0}, home=home)
    monkeypatch.setenv("HIVE_ENGRAM_LEARN", "off")
    assert not growth.record_work(spec, ok, home=home)
    with growth._database(home) as db:
        assert set(r[0] for r in db.execute("SELECT answer FROM examples")) == {"east", "low"}
        assert "SECRET_" not in json.dumps(list(db.iterdump()))


def test_measurement_required_before_activation_and_conflict_retires_only_affected_revision(tmp_path):
    home, edits = tmp_path / "ledger", tmp_path / "native"
    model, runtime = tmp_path / "model", tmp_path / "runtime"
    model.write_bytes(b"instrumented model")
    runtime.touch()
    for i in range(8):
        label(home, edits, i, "red" if i % 2 else "blue")
    args = dict(home=home, edit_home=edits, model=model, runtime=runtime)
    calls = []
    def measured(rows, path, *, model, runtime, threads, validation):
        assert not {r["prompt"] for r in rows} & {r["prompt"] for r in validation}
        calls.append(rows)
        path.write_bytes(b"test weights")
        cases = [dict(expected=r["answer"], prompt_sha256=hashlib.sha256(r["prompt"].encode()).hexdigest(),
                      before_correct=False, after_correct=True) for r in validation]
        return dict(labels=["red","blue"], sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    validation=dict(before=0, after=len(validation), count=len(validation), regressions=0, cases=cases))
    result, = growth.refresh(**args, trainer=measured)
    assert result["status"] == "published"
    index = edits / "index.jsonl"
    row = json.loads(index.read_text())
    assert row["verified"] and row["form"] == "label" and row["cues"] and len(row["qualification_wins"]) == 2
    assert (edits / f"t80+{row['name']}.gguf").read_bytes() == b"test weights"
    same, = growth.refresh(**args, trainer=measured)
    assert len(calls) == 1 and same["cached"]
    # A foreign scalar in a legacy JSONL index cannot prevent a healthy cache hit.
    index.write_text('5\n' + index.read_text())
    assert growth.refresh(**args, trainer=measured)[0]["cached"] and len(calls) == 1
    weight = edits / f"t80+{row['name']}.gguf"
    weight.write_bytes(b"disk corruption")
    recovered, = growth.refresh(**args, trainer=measured)
    assert recovered["status"] == "published" and len(calls) == 2 and weight.read_bytes() == b"test weights"
    # An intentional retirement is authoritative even when every published byte is intact.
    index.write_text(json.dumps({**row, "archived": True}) + "\n")
    retired, = growth.refresh(**args, trainer=measured)
    assert retired["status"] == "retired" and retired["cached"] and len(calls) == 2
    # Do not replace an unindexed file under a coinciding filename.
    import pytest
    index.write_text("")
    weight.write_bytes(b"somebody else's weights")
    with pytest.raises(ValueError, match="unowned"):
        growth.refresh(**args, trainer=measured)
    assert not index.read_text() and weight.read_bytes() == b"somebody else's weights"
    index.write_text(json.dumps(row) + "\n")
    label(home, edits, 0, "red")
    assert json.loads(index.read_text())["folded"] and growth.stats(home)[0]["conflicting_prompts"] == 1
    assert (edits / f"t80+{row['name']}.gguf").is_file()


def test_negative_transfer_does_not_publish_or_repeat_training(tmp_path):
    home, edits = tmp_path / "ledger", tmp_path / "native"
    model, runtime = tmp_path / "model", tmp_path / "runtime"
    model.touch()
    runtime.touch()
    for i in range(10):
        label(home, edits, i, "red" if i % 2 else "blue")
    calls = []
    def rejected(rows, path, *, model, runtime, threads, validation):
        calls.append(1)
        return dict(validation=dict(count=len(validation), before=2, after=1, regressions=1))
    for _ in range(2):
        r, = growth.refresh(home=home, edit_home=edits, model=model, runtime=runtime, trainer=rejected)
        assert r["status"] == "unqualified"
    assert len(calls) == 1 and not (edits / "index.jsonl").exists()


def test_all_domains_can_queue_without_a_model_or_network(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_ENGRAM_MODEL", str(tmp_path/"absent.gguf"))
    for d in growth.DOMAINS:
        for i in range(8):
            growth.record(d, "classify circuit", f"{d} circuit #{i}", ["low", "high"][i%2], {"type": "explicit_user_label"},
                          home=tmp_path/"ledger")
    assert len(growth.stats(tmp_path/"ledger")) == 6
    assert growth.refresh(home=tmp_path/"ledger")[0]["status"] == "missing_assets"


def test_ephemeral_practice_export_packs_and_restores_durable_conflicting_observations_only(tmp_path):
    def checked(domain, topic, prompt, answer, member):
        return growth.record(domain, topic, prompt, answer, {
            "type": "practice_member_check", "practice": "practice_10000021", "task": "e10000021_00",
            "member": member, "who": "t80", "submission_sha256": str(member)*64}, home=tmp_path/"old")
    checked("math", "rounding", "Round the observation?", "up", 1)
    checked("math", "rounding", "Round the observation?", "down", 2)
    growth.record("math", "rounding", "USER_LOCAL_ONLY", "private", {"type":"explicit_user_label"}, home=tmp_path/"old")
    extracted = tmp_path/"shards"/"rows-1"/"rows.engrams.jsonl"
    growth.export_practice("practice_10000021", extracted, home=tmp_path/"old")
    second = tmp_path/"shards"/"rows-2"/"rows.engrams.jsonl"
    second.parent.mkdir()
    second.write_bytes(extracted.read_bytes())
    archive = tmp_path/"rows-copy.jsonl"
    assert growth.pack_practice([tmp_path/"shards"], archive) == {"practice_observations": 2}
    assert b"USER_LOCAL_ONLY" not in archive.read_bytes()
    expected = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert growth.restore_practice(archive, expected, home=tmp_path/"restored") == {"recorded":1, "conflict":1}
    growth.restore_practice(archive, expected, home=tmp_path/"restored")
    group, = growth.stats(tmp_path/"restored")
    assert group["examples"] == 2 and group["conflicting_prompts"] == 1
    import pytest
    with pytest.raises(ValueError, match="digest"):
        growth.restore_practice(archive, "0"*64, home=tmp_path/"absent")
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    rows[-1]["answer"] = "tamper"
    archive.write_text("\n".join(map(json.dumps, rows)))
    with pytest.raises(ValueError, match="record"):
        growth.restore_practice(archive, home=tmp_path/"absent")
    assert not (tmp_path/"absent").exists()


def test_normal_generated_practice_keeps_checked_answer_and_sidecar_without_weights(tmp_path, monkeypatch):
    from training import exam, grow
    monkeypatch.setenv("HIVE_LEARNING_HOME", str(tmp_path/"ledger"))
    monkeypatch.setenv("HIVE_ENGRAM_LEARN", "1")
    monkeypatch.setenv("HIVE_ENGRAM_AUTO_REFRESH", "1")
    monkeypatch.delenv("HIVE_PRACTICE_BANK", raising=False)
    monkeypatch.setattr(exam, "RUNS", tmp_path/"runs")
    monkeypatch.setattr(exam, "_memory", lambda _: tmp_path)
    check = lambda folder, answer: (answer == "X", "matches observed category")
    check.maker = "one_code"
    text = "Which distinctive service code did the sample emit?"
    monkeypatch.setattr(exam, "exam", lambda *a, **kw: iter([("e10000021_00", "coding", "service", text, check)]))
    def generate(tag, tid, task, verifier, home, kind):
        run = exam.RUNS/tag/tid
        folder = run/"members"
        folder.mkdir(parents=True)
        for n, result in enumerate(["X","UNVERIFIED_CHAT"],1):
            (folder/f"member{n}.json").write_text(json.dumps({"who":f"t80+g42code{n}","answer":result}))
        verdict = {"id":tid, "ok":True, "seconds":1, "members":exam.each_member(run, verifier, attest=True),
                   "practice_prompt_sha256":hashlib.sha256(task.encode()).hexdigest()}
        (run/"exam.json").write_text(json.dumps(verdict))
        return verdict
    monkeypatch.setattr(exam, "sit_one", generate)
    grow.practice(10000021, 1, out=tmp_path/"rows.jsonl", log=lambda *a,**kw: None)
    manifest = json.loads((tmp_path/"practice.json").read_text())["tasks"][0]
    assert manifest["engram_examples"] == 1
    record = json.loads((tmp_path/"rows.engrams.jsonl").read_text())
    assert record["answer"] == "X" and record["origin"]["member"] == 1 and "UNVERIFIED_CHAT" not in str(record)
    assert growth.stats(tmp_path/"ledger")[0]["examples"] == 1


def test_new_edit_cannot_trade_an_old_confirmed_win_for_more_correct_answers(tmp_path):
    home, edits = tmp_path/"store", tmp_path/"edits"
    model, runtime = tmp_path/"m", tmp_path/"r"
    model.touch()
    runtime.touch()
    previous = []
    def compare(rows, path, *, model, runtime, threads, validation):
        cases = []
        for r in validation:
            prompt = r["prompt"]
            correct = not previous or prompt != previous[0]
            cases.append(dict(expected=r["answer"], prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                              before_correct=False, after_correct=correct))
        if not previous:
            previous.append(validation[0]["prompt"])
        path.write_bytes(repr(rows).encode())
        return dict(labels=["red","blue"], sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    validation=dict(count=len(cases),before=0,after=sum(c["after_correct"] for c in cases),regressions=0,cases=cases))
    args = dict(home=home, edit_home=edits, model=model, runtime=runtime, trainer=compare)
    for i in range(6):
        label(home, edits, i, "red" if i%2 else "blue")
    initial, = growth.refresh(**args)
    for i in range(6,14):
        label(home, edits, i, "red" if i%2 else "blue")
    latest, = growth.refresh(**args)
    assert initial["status"] == "published" and initial["measurement"]["validation"]["after"] == 2
    assert latest["measurement"]["validation"]["after"] == 3 and latest["status"] == "prior_wins_not_preserved"
    assert json.loads((edits/"index.jsonl").read_text())["name"] == initial["name"]
    assert len(list(edits.glob("*.gguf"))) == 1


def test_learn_list_uses_serving_hash_and_retirement_checks(tmp_path, monkeypatch, capsys):
    from team import ternary
    shipped, local = tmp_path/"shipped", tmp_path/"local"
    monkeypatch.setattr(ternary, "BUNDLED_ENGRAMS", shipped)
    monkeypatch.setattr(ternary, "engram_homes", lambda: (shipped, local))
    for folder, name in [(shipped,"starter"),(local,"personal")]:
        folder.mkdir()
        path=folder/f"t80+{name}.gguf"
        path.write_bytes(b"test")
        row=dict(name=name, dna="t80", task="oscillator decision", domain="computer_engineering", verified=True,
                 sha256=hashlib.sha256(b"test").hexdigest())
        (folder/"index.jsonl").write_text(json.dumps(row)+"\n")
    assert growth.main(["list"]) == 0
    shown=capsys.readouterr().out
    assert "shipped, t80+starter" in shown and "local, t80+personal" in shown
    (local/"t80+personal.gguf").write_bytes(b"changed")
    assert growth.main(["list"]) == 0 and "personal" not in capsys.readouterr().out


def test_restoring_out_of_order_shards_cannot_train_on_a_previously_held_out_prompt(tmp_path):
    source, dest = tmp_path/"source", tmp_path/"dest"
    origin = {"type":"practice_member_check","practice":"practice_10000021","task":"e10000021_00",
              "member":1,"who":"t80","submission_sha256":"1"*64}
    for i in range(3):
        growth.record("math","parity",f"Even {i}?","yes",origin,home=source)
    archive=tmp_path/"shard.jsonl"
    growth.export_practice(origin["practice"], archive, home=source)
    # This second store happened to assign the same observation to fitting first.
    growth.record("math","parity","Even 2?","yes",{"type":"explicit_user_label"},home=dest)
    growth.restore_practice(archive,home=dest)
    assert growth.stats(dest)[0]["split_conflicts"] == 1
    with growth._database(dest) as db:
        row=db.execute("SELECT split FROM examples WHERE prompt='Even 2?'").fetchone()
        assert row["split"] == "excluded"


def test_fieldwork_cli_records_only_verified_public_examples_in_the_normal_local_ledger(tmp_path, monkeypatch):
    import os
    import pytest
    from team import cli
    from training.experiments.fieldwork import work
    sdk=os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI for real sandboxed verification")
    source="def solve(x): return 'even' if x % 2 == 0 else 'odd'"
    task=dict(name="classify_parity",domain="math",task="Classify parity",
              examples=[{"input":2,"output":"even"},{"input":5,"output":"odd"}],
              validation=[{"input":379,"output":"odd"}],jobs=[{"id":"new","input":640}])
    bank=tmp_path/"bank"
    work.admit(bank,dict(task=task["name"],description=task["task"],source=source,
                         digest=work.fingerprint(source),validation=3))
    spec=tmp_path/"input.json"
    spec.write_text(json.dumps(task))
    monkeypatch.setenv("HIVE_LEARNING_HOME",str(tmp_path/"lessons"))
    monkeypatch.setenv("HIVE_ENGRAM_LEARN","1")
    assert cli.main(["fieldwork","--spec",str(spec),"--out",str(tmp_path/"delivery"),"--bank",str(bank),"--sdk",sdk]) == 0
    with growth._database(tmp_path/"lessons") as db:
        stored = list(db.execute("SELECT prompt,answer FROM examples ORDER BY answer"))
        assert [tuple(r) for r in stored] == [("Classify parity\nInput: 2","even"),("Classify parity\nInput: 5","odd")]
