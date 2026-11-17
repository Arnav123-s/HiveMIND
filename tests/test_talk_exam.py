"""The talk exam: made by code from a seed, checked by code, sat through team/talk.py, its number on the progress page."""
import datetime
import json

from team import talk
from training import progress, talk_exam as T


def test_the_same_seed_gives_the_same_exam_and_another_seed_another():
    a, b, c = T.make(5), T.make(5), T.make(6)
    assert a == b and a != c
    assert len(a) == 40 and len({it["id"] for it in a}) == 40
    assert {k: sum(it["kind"] == k for it in a) for k in T.KINDS} == {"route": 10, "fact": 10, "earlier": 10, "time": 10}
    assert sum(it["check"]["want"] == "talk" for it in a if it["kind"] == "route") == 5
    for it in a:  # every conversation begins with the user and alternates
        assert all(m["role"] == ("user", "assistant")[i % 2] for i, m in enumerate(it["history"]))
    earlier = [it for it in a if it["kind"] == "earlier"]
    assert all(1 <= len(it["history"]) // 2 <= 3 for it in earlier) and any(len(it["history"]) > 2 for it in earlier)
    json.dumps(a)  # an exam is plain data


def test_every_template_is_drawn_and_its_answer_is_in_the_conversation():
    for seed in range(4):
        for it in T.make(seed):
            said = " ".join([it["message"]] + [m["content"] for m in it["history"]])
            ck = it["check"]
            if it["kind"] in ("fact", "earlier"):  # the answer was said: in the message or 1 to 3 turns back
                ok, why = T.check(ck, said)
                assert ok, (it, why)


def test_the_checks_say_right_and_wrong():
    assert T.check({"type": "route", "want": "work"}, "", "work")[0] and not T.check({"type": "route", "want": "work"}, "", "talk")[0]
    text = {"type": "text", "want": [["comet7762"]]}
    assert T.check(text, "Your wifi password is Comet7762.")[0] and not T.check(text, "It is comet776.")[0]
    two = {"type": "text", "want": [["Wednesday"], ["17:30", "5:30"]]}
    assert T.check(two, "On Wednesday at 5:30 pm.")[0] and not T.check(two, "On Wednesday.")[0] and not T.check(two, "At 15:30 on Wednesday")[0]
    num = {"type": "number", "want": 1150}
    assert T.check(num, "It is 1,150.")[0] and T.check(num, "1150.0")[0] and not T.check(num, "115")[0]
    date = {"type": "date", "want": "2027-03-07"}
    for right in ("2027-03-07", "Sunday, 7 March 2027", "March 7th", "the 7th of March", "Mar. 7, 2027"):
        assert T.check(date, right)[0], right
    for wrong in ("2027-03-08", "8 March", "March 17", "7 April 2027"):
        assert not T.check(date, wrong)[0], wrong
    day = {"type": "weekday", "want": "friday", "allow": ["tuesday"]}
    assert T.check(day, "Today is Tuesday, so in 3 days it will be Friday.")[0]
    assert not T.check(day, "It will be Saturday.")[0] and not T.check(day, "Friday or Saturday")[0]
    assert not T.check({"type": "weekday", "want": "friday", "allow": []}, "Not Tuesday: Friday.")[0]
    clock = {"type": "clock", "want": "15:55"}
    for right in ("It will be 15:55.", "3:55 pm", "3.55 p.m."):
        assert T.check(clock, right)[0], right
    for wrong in ("3:55 am", "15:50", "It is 3:55 amazing"):
        assert not T.check(clock, wrong)[0], wrong
    assert T.clocks("at 3 pm") == {"15:00"} and T.clocks("3 amazing things") == set()


def test_the_time_checks_follow_the_date_the_hive_is_told():
    it = next(it for seed in range(20) for it in T.make(seed) if it["message"] == "What day of the week is it today?")
    now = datetime.datetime.strptime(it["now"], "%Y-%m-%d %H:%M")
    assert it["check"]["want"] == now.strftime("%A").lower()


def _hive(monkeypatch, tmp_path, answer):
    """A hive whose model is code: it routes by the word list in the decision and answers with `answer(messages)`."""
    told = []

    def chat(member, messages, max_new_tokens=700, temperature=0.0, also=()):
        if "one word, TALK or WORK" in messages[0]["content"]:
            q = messages[-1]["content"].lower()
            return "WORK" if any(w in q for w in ("pypi", "median", "multiply", "costs", "python function")) else "TALK"
        told.append(messages)
        return answer(messages)

    def first(task, run_dir=None, approve="never", members=2):
        return {"report": "the result: 42", "agreed": True, "dir": str(run_dir)}
    monkeypatch.setattr(talk.ternary, "chat", chat)
    from team import solo
    monkeypatch.setattr(solo, "first", first)
    return told


def _knows(messages):
    """A talker that answers every question of the exam right, from what it was told (a stand-in for a good model)."""
    said = " ".join(m["content"] for m in messages)
    for it in _ITEMS:
        if messages[-1]["content"] == it["message"] and it["now"].replace(" ", "")[:10] in messages[0]["content"].replace(" ", ""):
            ck = it["check"]
            want = {"text": lambda: " ".join(g[0] for g in ck.get("want", [])), "number": lambda: str(ck.get("want")),
                    "date": lambda: ck.get("want"), "weekday": lambda: ck.get("want"), "clock": lambda: ck.get("want")}
            return "It is " + want[ck["type"]]() + "."
    return "I do not know. " + said[:0]


_ITEMS = T.make(3)


def test_a_sitting_goes_through_talk_and_is_scored_out_of_40_and_of_10(monkeypatch, tmp_path):
    told = _hive(monkeypatch, tmp_path, _knows)
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None)
    assert res["of"] == 40 and len(res["items"]) == 40
    # the route checks: whatever the stand-in router got wrong is wrong, the rest right
    route = [r for r in res["items"] if r["kind"] == "route"]
    assert all(r["ok"] == (r["route"] == next(i for i in _ITEMS if i["id"] == r["id"])["check"]["want"]) for r in route)
    # every talk reply was given the exam's date and time, and the conversation before
    assert all("Now it is 20" in m[0]["content"] for m in told)
    deep = next(i for i in _ITEMS if i["kind"] == "earlier" and len(i["history"]) == 6)  # the fact 3 turns back
    assert any(m[-1]["content"] == deep["message"] and len(m) == 8 for m in told)
    talked = [r for r in res["items"] if r["kind"] != "route" and r["route"] == "talk"]
    assert talked and all(r["ok"] for r in talked)
    assert res["right"] == sum(r["ok"] for r in res["items"]) and res["out_of_10"] == round(res["right"] / 4, 1)
    assert sum(n for _, n in res["kinds"].values()) == 40


def test_a_hive_that_knows_nothing_scores_low_and_one_that_breaks_scores_nothing(monkeypatch, tmp_path):
    _hive(monkeypatch, tmp_path, lambda m: "I am not sure.")
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None)
    assert res["kinds"]["fact"][0] == 0 and res["kinds"]["earlier"][0] == 0 and res["right"] <= 10

    def broken(*a, **k):
        raise RuntimeError("the server is dead")
    monkeypatch.setattr(talk.ternary, "chat", broken)
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None, only=("fact",))
    assert res["of"] == 10 and res["right"] == 0 and "broke" in res["items"][0]["why"]


def test_work_is_told_the_exams_time(monkeypatch, tmp_path):
    tasks = []
    _hive(monkeypatch, tmp_path, lambda m: "Done.")
    from team import solo
    monkeypatch.setattr(solo, "first", lambda task, *a, **k: tasks.append(task) or {"report": "x: 1", "agreed": True})
    talk.reply("what is 17.5% of 2340?", base="t17", run_dir=tmp_path, now=datetime.datetime(2027, 3, 4, 14, 20))
    assert tasks and tasks[0].startswith("what is 17.5% of 2340?") and "It is now 2027-03-04 (Thursday), 14:20" in tasks[0]


def test_the_cli_shows_and_sits(monkeypatch, tmp_path, capsys):
    assert T.main(["show", "--seed", "3"]) == 0
    shown = capsys.readouterr().out
    assert shown.count("check:") == 40 and "t3_00" in shown
    monkeypatch.setenv("HIVE_MEMBERS", "t17")  # the sitting sets it for the work; restored after the test
    monkeypatch.setattr(T, "sit", lambda seed, who, only: T.score(seed, who, who, [{"kind": "fact", "ok": True}] * 3 + [{"kind": "time", "ok": False}]))
    out = tmp_path / "talk.json"
    assert T.main(["sit", "--seed", "3", "--who", "t17", "--out", str(out)]) == 0
    res = json.loads(out.read_text())
    assert res["right"] == 3 and res["of"] == 4 and res["out_of_10"] == 7.5 and res["kinds"]["fact"] == [3, 3]


def test_the_talk_row_is_on_the_progress_page_when_the_generation_sat_it(tmp_path):
    rec = tmp_path / "generations.jsonl"
    rec.write_text(json.dumps({"generation": "g43", "when": "2026-11-18 10:00", "rows": 10, "dna": "t80",
                               "arms": {"after": {"passed": 50, "tasks": 64, "kinds": {"a kind": [1, 1]}}}}) + "\n")
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80"}))
    talks = tmp_path / "talk"
    progress.draw(rec, tmp_path / "docs" / "progress", body, talks)
    assert "**Talk:**" not in (tmp_path / "docs" / "PROGRESS.md").read_text()  # not sat: no row
    talks.mkdir()
    rows = [{"kind": k, "ok": i < n} for k, n in zip(T.KINDS, (9, 7, 8, 6)) for i in range(10)]
    (talks / "g43.json").write_text(json.dumps(T.score(812, "body", "t80", rows)))
    progress.draw(rec, tmp_path / "docs" / "progress", body, talks)
    page = (tmp_path / "docs" / "PROGRESS.md").read_text()
    assert "**Talk:** generation g43 sat the talk exam (seed 812): 7.5 of 10 (30 of 40 messages right: route 9 of 10, fact 7 of 10" in page
    (talks / "g43.json").write_text("not json")
    assert progress.talk_of("g43", talks) is None
