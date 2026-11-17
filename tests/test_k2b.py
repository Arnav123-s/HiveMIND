"""K2b: the family "text work" (training/kinds/h_txt_*.py). Every taught kind's lesson is right by its own check on 40
seeds of 40; every kind makes its sample without the network; a wrong answer fails the check. The two held-out kinds are
never taught: their checks pass a right answer written here and fail a wrong one."""
import re

import pytest

from training import exam, kinds, lessons

TEXT = sorted(k.KIND for k in kinds.ALL if k.KIND.startswith("h_txt_"))
TAUGHT = [n for n in TEXT if not kinds.get(n).HELD_OUT]
HELD = [n for n in TEXT if kinds.get(n).HELD_OUT]


def _no_network(*a, **k):
    raise AssertionError("a kind's sample asked the network")


@pytest.fixture
def offline(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _no_network)
    monkeypatch.setattr(requests, "post", _no_network)


def test_the_family_has_eight_hard_kinds_two_held_out_in_its_own_orders():
    assert len(TEXT) == 8 and len(TAUGHT) == 6 and sorted(HELD) == ["h_txt_ini", "h_txt_redact"]
    for n in TEXT:
        k = kinds.get(n)
        assert k.HARD and k.FAMILY == "hard: text" and 400 <= k.ORDER <= 499 and not k.NETWORK
        assert (k.lesson is None) == k.HELD_OUT
    assert set(TAUGHT) <= set(lessons.SOLVERS) and not set(HELD) & set(lessons.SOLVERS)
    assert set(HELD) <= kinds.HELD_OUT


@pytest.mark.parametrize("name", TEXT)
def test_a_text_kind_is_made_offline_and_the_same_from_the_same_seed(name, offline):
    field, kind, task, check = kinds.sample(name)
    assert field == "hard: text" and task == kinds.sample(name)[2]
    assert exam.remake(name, "k2b:x")[2] == exam.remake(name, "k2b:x")[2] != exam.remake(name, "k2b:y")[2]


def _wrong(answer):
    """The answer made wrong: its last number one more, or its last line gone where it has no number."""
    nums = list(re.finditer(r"\d+", answer))
    if nums:
        m = nums[-1]
        return answer[:m.start()] + str(int(m.group()) + 1) + answer[m.end():]
    return "\n".join(answer.splitlines()[:-1])


@pytest.mark.parametrize("name", TAUGHT)
def test_a_taught_kind_is_right_by_its_lesson_on_40_seeds_and_a_wrong_answer_fails(name, offline, tmp_path):
    from team.tools.sandbox import give, run_python
    for i in range(40):
        les = lessons.lesson(name, f"k2b:{name}:{i}", 0, timeout=60)
        assert les["ok"], f"{name} seed {i}: {les['why']}\n{les['task']}\n{les['program']}\n{les['answer']}"
    # a wrong answer: the printed lines changed, or (for a kind that saves a file) the file changed, fails the check
    for i in range(5):
        field, kind, task, check = exam.remake(name, f"k2b:{name}:{i}")
        run = tmp_path / f"{name}{i}"
        work = run / "work"
        give(task, work, skip=lessons._wanted(task))
        res = run_python(lessons.SOLVERS[name](task), work, name="lesson.py", timeout=60)
        (work / "lesson.py").unlink()
        answer = res["stdout"].strip()
        assert check(run, answer)[0]
        assert not check(run, _wrong(answer))[0], (name, answer)
        saved = [p for p in work.iterdir() if p.suffix in (".txt", ".csv") and p.name in task]
        for p in saved:
            lines = p.read_text().splitlines()
            p.write_text("\n".join(lines[1:] + lines[:1]) + "\n")  # the first line moved to the end
            assert not check(run, answer)[0], (name, p.name)


# ---- the held-out kinds: right answers written here, by other code than any lesson -----------------------------------
def _redact(task):
    text = re.search(r"Here is a text:\n(.*?)\nA card number is", task, re.S).group(1)
    card = re.compile(r"(?<!\d)(?<!\d[- ])(\d{4})([- ])(\d{4})\2(\d{4})\2(\d{4})(?![- ]?\d)")
    n = len(card.findall(text))
    return card.sub(lambda m: m.group(2).join(["****"] * 3 + [m.group(5)]), text), n


def _ini(task):
    text = re.search(r"Here is a config file:\n(.*?)\nRead it by these rules", task, re.S).group(1)
    key, ask, other = re.search(r"value of '(\w+)' in the section '(\w+)', and how many distinct keys does the section '(\w+)'", task).groups()
    data, section = {}, None
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("["):
            section = line.strip("[]").strip().lower()
            data.setdefault(section, {})
        else:
            k, v = line.split("=", 1)
            data[section][k.strip().lower()] = v.strip()
    return data[ask][key], len(data[other])


@pytest.mark.parametrize("i", range(40))
def test_the_held_out_kinds_pass_a_right_answer_and_fail_a_wrong_one(i, tmp_path):
    field, kind, task, check = exam.remake("h_txt_redact", f"k2b:redact:{i}")
    (tmp_path / "work").mkdir()
    done, n = _redact(task)
    (tmp_path / "work" / "redacted.txt").write_text(done + "\n")
    assert check(tmp_path, f"redacted.txt saved\nmasked: {n}")[0], task
    assert not check(tmp_path, f"masked: {n + 1}")[0]
    (tmp_path / "work" / "redacted.txt").write_text(re.search(r"Here is a text:\n(.*?)\nA card", task, re.S).group(1))
    assert not check(tmp_path, f"masked: {n}")[0]  # nothing masked

    field, kind, task, check = exam.remake("h_txt_ini", f"k2b:ini:{i}")
    value, keys = _ini(task)
    assert check(tmp_path, f"value: {value}\nkeys: {keys}")[0], task
    assert not check(tmp_path, f"value: {value}\nkeys: {keys + 1}")[0]
    assert not check(tmp_path, f"value: {value}x\nkeys: {keys}")[0]

