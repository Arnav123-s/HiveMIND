import json

from training import grow


def _member(home, n, first, final, answer):
    msgs = [{"role": "system", "content": "orders. Today is 2026-11-14 (Friday)."}, {"role": "user", "content": "TASK: add"},
            {"role": "assistant", "content": f"```python\n{first}\n```"}]
    if final != first:
        msgs += [{"role": "user", "content": "It failed."}, {"role": "assistant", "content": f"```python\n{final}\n```"}]
    (home / f"member{n}.json").write_text(json.dumps({"messages": msgs, "program": final, "answer": answer}))


def test_pairs_set_the_agreed_program_beside_first_tries_that_were_wrong(tmp_path):
    home = tmp_path / "members"
    home.mkdir()
    _member(home, 1, "print('2'+'3')", "print(2+3)", "5")   # wrong first, then right
    _member(home, 2, "print(2+3)", "print(2+3)", "5")       # right at once: no pair from it
    _member(home, 3, "print(6)", "print(6)", "6")           # disagreed: its program is a wrong one
    (home / "members.json").write_text(json.dumps({"agreed": True, "agreeing": [1, 2]}))
    rows = grow.pair_rows(tmp_path, "add")
    assert [r["rejected"] for r in rows] == ["```python\nprint('2'+'3')\n```", "```python\nprint(6)\n```"]
    assert all(r["output"] == "```python\nprint(2+3)\n```" and r["type"] == "pair" for r in rows)
    assert rows[0]["messages"][1]["content"] == "TASK: add" and "2026-11-14" in rows[0]["messages"][0]["content"]


def test_no_pairs_where_nobody_agreed(tmp_path):
    home = tmp_path / "members"
    home.mkdir()
    _member(home, 1, "print(1)", "print(1)", "1")
    (home / "members.json").write_text(json.dumps({"agreed": False, "agreeing": []}))
    assert grow.pair_rows(tmp_path, "add") == []
