"""g53: members agreed on a wrong spec detail (a put on a held key not moving it, ties not alphabetical, the edges and the
row of dashes of a markdown table kept). The lessons show the detail, a kind whose wrong answers were delivered is not
left to the hive, and the checks reject the wrong programs."""
import json
import tempfile
from pathlib import Path

from team.tools.sandbox import give, run_python
from training import exam, grow, lessons as L


def _run(maker, rseed, program):
    field, kind, task, check = exam.remake(maker, rseed, 0, None)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        give(task, work)
        r = run_python(program, work, name="p.py", timeout=120)
        (work / "p.py").unlink(missing_ok=True)
        return task, (check(Path(tmp), r["stdout"].strip())[0] if r["returncode"] == 0 else False)


def _first_showing(maker, want=True):
    for i in range(40):
        les = L.lesson(maker, f"t:{i}")
        if les["ok"] and L._shows(maker, les) == want:
            return f"t:{i}", les
    raise AssertionError("no such draw")


def test_the_lesson_programs_name_the_rule_and_are_right_on_the_detail():
    for maker, words in (("h_prog_lru", "held key"), ("h_txt_words", "alphabetical"), ("h_txt_mdcsv", "row of dashes")):
        for i in range(5):
            les = L.fitting(maker, f"t:{i}")
            assert les["ok"], (maker, i, les["why"])
            assert words in les["program"] and L._shows(maker, les)


def test_the_draw_that_asks_the_detail_is_the_lesson():
    for maker in ("h_prog_lru", "h_txt_words"):
        plain = [L._shows(maker, L.lesson(maker, f"t:{i}")) for i in range(12)]
        assert not all(plain)  # some plain draws are not the detail
        assert all(L._shows(maker, L.fitting(maker, f"t:{i}")) for i in range(12))


def test_the_checks_reject_the_wrong_programs_the_members_agreed_on():
    # a lru that never moves a held key (d[k] = v, no move to the end), where a put is a use
    for i in range(40):
        s, les = f"w:{i}", L.lesson("h_prog_lru", f"w:{i}")
        if "holds changes its value and does count" in les["task"] and L._shows("h_prog_lru", les):
            wrong = les["program"].replace("        s.d.pop(k, None)\n", "")
            assert _run("h_prog_lru", s, wrong)[1] is False
            assert _run("h_prog_lru", s, les["program"])[1] is True
            break
    else:
        raise AssertionError("no draw")
    # words: ties in the order first seen
    seed, les = _first_showing("h_txt_words")
    wrong = les["program"].replace("(-c[w], w)", "(-c[w], list(c).index(w))")
    assert _run("h_txt_words", seed, wrong)[1] is False
    # markdown table: edges and the row of dashes kept
    wrong = ('rows = [line.split("|") for line in open("table.md")]\nimport csv\n'
             'csv.writer(open("table.csv", "w", newline="")).writerows(rows)\nprint("data rows:", len(rows) - 1)\n')
    assert _run("h_txt_mdcsv", "t:0", wrong)[1] is False


def test_a_kind_with_a_delivered_wrong_answer_is_not_left_to_the_hive(tmp_path):
    kind = "a cache that forgets the least recently used, with hidden tests"
    f = tmp_path / "failures.jsonl"
    rows = [{"kind": kind, "delivered": True}, {"kind": "other kind", "delivered": False}, {"kind": "third"}]
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
    agreed = L.agreed_wrong_kinds(f)
    assert agreed == {kind}
    own, pulse = {kind: 9, "other kind": 9}, {kind: [3, 3], "other kind": [3, 3]}
    assert L.left_to_the_hive(kind, own, pulse) is True  # before: the hive was to learn it alone
    assert L.left_to_the_hive(kind, own, pulse, agreed) is False
    assert L.left_to_the_hive("other kind", own, pulse, agreed) is True
    assert L.left_to_the_hive("none", own, pulse, agreed) is False  # too few of its own: taught, as before
    assert L.left_to_the_hive(kind, own, {kind: [0, 3]}) is False  # the body fails it: taught, as before


def test_a_failure_is_recorded_as_delivered_only_when_the_hive_gave_an_answer():
    assert grow.delivered({"answer": "a\nb"}) is True
    assert grow.delivered({"answer": "Not confirmed: the members did not agree"}) is False
    assert grow.delivered({"answer": "No member answered"}) is False
    assert grow.delivered({}) is False
