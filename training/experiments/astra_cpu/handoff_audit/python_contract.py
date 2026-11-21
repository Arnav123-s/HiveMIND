"""Observe the stock delivery contract on authored, ordinary module examples. No model or worker code runs."""
import json
import tempfile
from pathlib import Path
from team import deliverables, solo

TASK = "Write and save tips.py with a function supported(items) returning the size of the input list."
A = "def supported(items):\n    return len(items)\n"
B = "def supported(values):\n    return sum(1 for _ in values)\n"
C = "def supported(items):\n    return 0\n"
D = "def supported(values):\n    return int(False)\n"


def probe(path, first, second, replies):
    members = []
    for i, source in enumerate((first, second)):
        work = path / str(i)
        work.mkdir(exist_ok=True)
        (work / "tips.py").write_text(source)
        members.append(dict(work=work, answer=replies[i], delivery=deliverables.inspect(TASK, work, ["tips.py"])))
    left, right = members
    return dict(same_bytes=left["delivery"]["byte_hashes"] == right["delivery"]["byte_hashes"],
                same_files=solo.same_files(left, right, TASK),
                same_text=solo.same(left["answer"], right["answer"], TASK),
                winner=solo._winner(members, solo.agreeing(members, TASK), TASK) is not None)


if __name__ == "__main__":
    same = ["saved tips.py", "saved tips.py"]
    different = ["All green", "Ready for review"]
    with tempfile.TemporaryDirectory() as home:
        path = Path(home)
        cases = dict(equal_correct_same_notice=probe(path, A, B, same),
                     equal_correct_different_notice=probe(path, A, B, different),
                     equal_wrong_same_notice=probe(path, C, D, same),
                     conflicting_same_notice=probe(path, A, C, same))
    print(json.dumps(cases, indent=2))
