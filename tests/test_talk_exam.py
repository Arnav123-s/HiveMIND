"""The talk exam: made by code from a seed, checked by code, sat through team/talk.py, its number on the progress page."""
import datetime
import json
import re

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
    assert all(4 <= len(it["history"]) // 2 <= 8 for it in earlier) and len({len(it["history"]) for it in earlier}) > 1
    json.dumps(a)  # an exam is plain data


def _plain(spec):
    return {k: v for k, v in spec.items() if k not in ("not", "never")}


def test_every_template_is_drawn_and_its_answer_and_near_misses_are_in_the_conversation():
    seen = {k: set() for k in T.KINDS}
    for seed in range(6):
        for it in T.make(seed):
            said = " ".join([it["message"]] + [m["content"] for m in it["history"]])
            ck = it["check"]
            seen[it["kind"]].add(re.sub(r"\d+", "#", it["message"])[:24] + str(ck["want"] if it["kind"] == "route" else ""))
            if it["kind"] in ("fact", "earlier"):  # the answer was said, in the message or the turns before
                ok, why = T.check(_plain(ck), said)
                assert ok, (it, why)
                for d in ck.get("not", []) + ck.get("never", []):  # and so was every near miss
                    assert T._has(said, str(d)), (it, d)
    assert all(len(v) >= 10 for v in seen.values()), {k: len(v) for k, v in seen.items()}


def _answer(spec):
    """A reply part naming the answer the way the check reads it."""
    if spec["type"] == "all":
        return " and ".join(_answer(s) for s in spec["of"])
    if spec["type"] == "text":
        return ", ".join(g[0] for g in spec["want"])
    return str(spec["want"])


def test_the_right_answer_passes_and_a_near_miss_fails():
    n = 0
    for seed in range(8):
        for it in T.make(seed):
            ck = it["check"]
            if it["kind"] == "route":
                continue
            right = _answer(ck)
            assert T.check(ck, f"It is {right}.")[0], (it, right)
            for d in ck.get("not", []):
                n += 1
                assert not T.check(ck, f"It is {d}.")[0], (it, d)
                assert not T.check(ck, f"It is {d}. Or maybe {right}.")[0], (it, d)  # the near miss named first
                assert T.check(ck, f"It is {right} (not {d}).")[0], (it, d)  # the answer first, the miss explained
            for d in ck.get("never", []):
                assert not T.check(ck, f"{right} and {d}.")[0], (it, d)
    assert n > 150  # near misses everywhere: every fact and nearly every earlier message, and most time messages


def test_the_time_messages_sit_on_the_edges_and_follow_the_date_the_hive_is_told():
    td, kinds = datetime.timedelta, set()
    for seed in range(12):
        for it in T.make(seed):
            if it["kind"] != "time":
                continue
            now, msg, ck = datetime.datetime.strptime(it["now"], "%Y-%m-%d %H:%M"), it["message"], it["check"]
            k = int(T.numbers(msg)[0]) if T.numbers(msg) else 0
            if "days from" in msg:
                assert ck["want"] == (now + td(days=k)).strftime("%Y-%m-%d")
                assert (now + td(days=k)).month != now.month or ck["want"][5:] == "02-29"  # over the end of February, or of a year
                assert ck["not"] and ck["not"][0] != ck["want"]  # the date counted in the other kind of year, or in the old year
                kinds.add("leap" if now.month == 2 else "year end")
            elif "hours ago" in msg:
                then = now - td(hours=k)
                assert then.date() < now.date()
                assert ck["of"] == [{"type": "clock", "want": then.strftime("%H:%M")}, {"type": "date", "want": then.strftime("%Y-%m-%d")}]
                kinds.add("midnight back")
            elif "minutes" in msg:
                then = now + td(minutes=k)
                assert then.date() > now.date() and ck["of"][0]["want"] == then.strftime("%H:%M")
                kinds.add("midnight on")
            elif "days ago" in msg and "week" in msg:
                assert ck["want"] == (now - td(days=k)).strftime("%A").lower()
                kinds.add("weekday back")
            elif "days ago" in msg:
                assert ck["want"] == (now - td(days=k)).strftime("%Y-%m-%d") and ck["want"][:4] < it["now"][:4]
                kinds.add("year start")
            elif "last day of this month" in msg:
                assert now.month == 2 and ck["want"] == ("%d-02-29" if now.year % 4 == 0 else "%d-02-28") % now.year
                kinds.add("february")
            elif "UTC" in msg:
                kinds.add("zone")
    assert kinds == {"leap", "year end", "midnight back", "midnight on", "weekday back", "year start", "february", "zone"}
    # a zone worked out by hand: Chicago (UTC-6) at 11:55 is 02:55 the next day in Tokyo (UTC+9)
    it = next(i for i in T.make(1) if "Chicago (UTC-6). What time is it right now in Tokyo" in i["message"])
    assert it["now"].endswith("11:55") and it["check"]["want"] == "02:55"
    assert T.check(it["check"], "In Tokyo it is 2:55 am, while it is 11:55 for you.")[0]
    assert not T.check(it["check"], "It is 11:55 in Tokyo.")[0]


def test_the_route_messages_sit_on_the_border():
    a = [it for seed in range(20) for it in T.make(seed) if it["kind"] == "route"]
    talk_ = [it["message"] for it in a if it["check"]["want"] == "talk"]
    work = [it["message"] for it in a if it["check"]["want"] == "work"]
    assert any("look up" in m for m in talk_) and any("look up" in m for m in work)  # both sides say "look up"
    assert any(" times " in m for m in talk_) and any(" times " in m for m in work)  # 7 times 8 against 4817 times 362
    assert any("explain" in m or "how does" in m for m in talk_) and any("write" in m for m in work)
    looked = [it for it in a if it["history"]]  # what is looked up there was said in the chat
    assert looked and all(it["check"]["want"] == "talk" for it in looked)
    for m in talk_:  # nothing on the talk side is sent to work by code alone (talk.MUST): the model has to decide
        assert not talk.MUST.search(m), m


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
    # a reply that says it does not know is wrong even where it names the value (t17 said this on seed 1)
    assert not T.check({"type": "text", "want": [["Priya"]]}, "I don't remember your name. I'm Priya, and I'm here to help.")[0]
    assert not T.check(num, "I do not know, maybe 1150?")[0] and T.check(num, "I know it: 1150.")[0]
    # near misses: of the answer and the misses, the one the reply names first must be the answer
    room = {"type": "number", "want": 412, "not": [318]}
    assert T.check(room, "Room 412: it moved from 318.")[0] and not T.check(room, "Room 318, or maybe 412.")[0] and not T.check(room, "Room 318.")[0]
    gate = {"type": "text", "want": [["F44"]], "not": ["C9"]}
    assert T.check(gate, "Your brother leaves from gate F44.")[0] and not T.check(gate, "Gate C9; your brother's is F44.")[0]
    late = {"type": "clock", "want": "20:30", "not": ["19:00"]}
    assert T.check(late, "It starts at 8:30 pm now.")[0] and not T.check(late, "At 7 pm (it was moved to 20:30).")[0]
    leap = {"type": "date", "want": "2028-02-29", "not": ["2028-03-01"]}
    assert T.check(leap, "It will be 29 February 2028.")[0] and not T.check(leap, "March 1st, 2028 (or Feb 29 in a leap year)")[0]
    both = {"type": "all", "of": [{"type": "clock", "want": "22:45"}, {"type": "date", "want": "2026-06-19"}]}
    assert T.check(both, "It was 22:45 on 19 June 2026.")[0] and not T.check(both, "It was 22:45 on 20 June 2026.")[0]
    shop = {"type": "text", "want": [["tea"], ["honey"]], "never": ["candles"]}
    assert T.check(shop, "Tea and honey.")[0] and not T.check(shop, "Tea, honey and candles.")[0]


def _hive(monkeypatch, tmp_path, answer):
    """A hive whose model is code: it routes by the word list in the decision and answers with `answer(messages)`."""
    told = []

    def chat(member, messages, max_new_tokens=700, temperature=0.0, also=()):
        if "one word, TALK or WORK" in messages[0]["content"]:
            q = messages[-1]["content"].lower()
            return "WORK" if any(w in q for w in ("look up", "write", "times", "scores", "most often")) else "TALK"
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
    for it in _ITEMS:
        if messages[-1]["content"] == it["message"] and it["now"].replace(" ", "")[:10] in messages[0]["content"].replace(" ", ""):
            return "It is " + _answer(it["check"]) + "."
    return "I do not know."


_ITEMS = T.make(3)


def test_a_sitting_goes_through_talk_and_is_scored_out_of_40_and_of_10(monkeypatch, tmp_path):
    told = _hive(monkeypatch, tmp_path, _knows)
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None)
    assert res["of"] == 40 and len(res["items"]) == 40
    # the route checks: whatever the stand-in router got wrong is wrong, the rest right
    route = [r for r in res["items"] if r["kind"] == "route"]
    assert all(r["ok"] == (r["route"] == next(i for i in _ITEMS if i["id"] == r["id"])["check"]["want"]) for r in route)
    assert not all(r["ok"] for r in route)  # a router that goes by words is caught on the border
    # every talk reply was given the exam's date and time, and the whole conversation before
    assert all("Now it is 20" in m[0]["content"] for m in told)
    deep = max((i for i in _ITEMS if i["kind"] == "earlier"), key=lambda i: len(i["history"]))
    assert len(deep["history"]) >= 12 and any(m[-1]["content"] == deep["message"] and len(m) == len(deep["history"]) + 2 for m in told)
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


def test_a_hive_that_repeats_the_first_value_it_was_given_fails_the_near_misses(monkeypatch, tmp_path):
    def first_said(messages):  # names the first room, time or code it was told: what a weak talker does
        convo = " ".join(m["content"] for m in messages[1:])
        for it in _ITEMS:
            if messages[-1]["content"] == it["message"] and it["check"].get("not"):
                return f"It is {it['check']['not'][0]}." if str(it["check"]["not"][0]) in convo else "It is " + _answer(it["check"]) + "."
        return "It is " + convo.split()[-1]
    _hive(monkeypatch, tmp_path, first_said)
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None, only=("fact", "earlier"))
    assert res["kinds"]["fact"][0] == 0 and res["kinds"]["earlier"][0] <= 1


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
    monkeypatch.setattr(T, "sit", lambda seed, who, only, **k: T.score(seed, who, who, [{"kind": "fact", "ok": True}] * 3 + [{"kind": "time", "ok": False}]))
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


# ---- held to time: the line sits it every generation and must never wait on it ---------------------------------------
def _slow(monkeypatch, tmp_path, seconds_for):
    """A hive whose model takes `seconds_for(message)` seconds to answer each message (then answers like _knows)."""
    import time

    def answer(messages):
        time.sleep(seconds_for(messages[-1]["content"]))
        return _knows(messages)
    return _hive(monkeypatch, tmp_path, answer)


def test_a_message_over_its_cap_fails_for_time_and_the_sitting_goes_on(monkeypatch, tmp_path):
    import time
    facts = [i for i in _ITEMS if i["kind"] == "fact"]
    slow = {facts[1]["message"], facts[4]["message"]}
    _slow(monkeypatch, tmp_path, lambda m: 30 if m in slow else 0)
    t0 = time.time()
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None, only=("fact",), per=2)
    assert time.time() - t0 < 25  # the slow ones were ended at their cap, not waited for
    timed = [r for r in res["items"] if r["why"].startswith("time")]
    assert [r["message"] for r in timed] == [facts[1]["message"], facts[4]["message"]]
    assert all(not r["ok"] and r["seconds"] < 10 for r in timed)
    assert res["of"] == 10 and res["timed_out"] == 2 and res["per_seconds"] == 2
    assert all(r["ok"] for r in res["items"] if r not in timed) and res["right"] == 8  # what came back in time scored as ever


def test_the_budget_ends_the_sitting_cleanly_and_counts_the_rest_failed_for_time(monkeypatch, tmp_path):
    import time
    _slow(monkeypatch, tmp_path, lambda m: 0.4)
    t0 = time.time()
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None, only=("fact", "earlier"), minutes=1.5 / 60, per=120)
    assert time.time() - t0 < 6
    assert res["of"] == 20 and res["timed_out"] >= 15 and res["budget_minutes"] == 1.5 / 60
    sat = [r for r in res["items"] if not r["why"].startswith("time")]
    assert sat and all(r["ok"] for r in sat) and res["right"] == len(sat)
    assert "time was up" in res["items"][-1]["why"]


def test_a_message_that_breaks_in_its_own_process_is_failed_and_said(monkeypatch, tmp_path):
    _hive(monkeypatch, tmp_path, _knows)

    def broken(*a, **k):
        raise RuntimeError("the server is dead")
    monkeypatch.setattr(talk.ternary, "chat", broken)
    res = T.sit(3, who="t17", run_dir=tmp_path, log=lambda *a: None, only=("route",), per=30)
    assert res["of"] == 10 and res["right"] == 0 and res["items"][0]["why"] == "broke: RuntimeError: the server is dead"


def test_the_cli_takes_the_budget_and_writes_its_json_even_when_the_sitting_cannot_start(monkeypatch, tmp_path, capsys):
    got = {}
    monkeypatch.setattr(T, "sit", lambda seed, who, only, **k: got.update(k) or T.score(seed, who, who, [{"kind": "fact", "ok": True}]))
    out = tmp_path / "talk" / "g44.json"
    assert T.main(["sit", "--seed", "3", "--who", "body", "--minutes", "20", "--per", "120", "--out", str(out)]) == 0
    assert got == {"minutes": 20.0, "per": 120.0} and json.loads(out.read_text())["right"] == 1

    def nobody(*a, **k):
        raise RuntimeError("the hive's body is not on this machine")
    monkeypatch.setattr(T, "sit", nobody)
    assert T.main(["sit", "--seed", "3", "--minutes", "20", "--out", str(out)]) == 1
    res = json.loads(out.read_text())
    assert res["of"] == 0 and "not on this machine" in res["error"]
    assert progress.talk_of("g44", out.parent) is None  # no Talk line from a sitting that never sat


def test_the_gate_sits_the_talk_exam_on_one_after_seat_and_the_record_keeps_it():
    import yaml
    flow = yaml.safe_load((T.ROOT / ".github" / "workflows" / "grow.yml").read_text())
    gate = flow["jobs"]["gate"]["steps"]
    names = [s.get("name", "") for s in gate]
    i = names.index("The talk exam (training/talk_exam.py)")
    step = gate[i]
    assert i > names.index("A fresh exam, half of the first exam's kinds and half hard ones")
    assert step["continue-on-error"] is True and step["timeout-minutes"] == 30
    assert "matrix.arm == 'after'" in step["if"] and "matrix.seed == 1" in step["if"]
    assert "training/talk_exam.py sit" in step["run"] and '--who body --minutes 20 --per 120 --out "talk/$GEN.json"' in step["run"]
    up = gate[i + 1]
    assert up["with"]["name"] == "talk-${{ env.GEN }}" and up["with"]["if-no-files-found"] == "ignore" and up["if"] == step["if"]
    rec = flow["jobs"]["record"]["steps"]
    j = next(n for n, s in enumerate(rec) if s.get("with", {}).get("name") == "talk-${{ env.GEN }}")
    assert rec[j]["continue-on-error"] is True and rec[j]["with"]["path"] == "training/reports/talk"
    k = next(n for n, s in enumerate(rec) if "training/reads.py write" in s.get("run", ""))
    assert j < k and "training/reports/talk/$GEN.json" in rec[k]["run"].split("git add docs/PROGRESS.md", 1)[1]
