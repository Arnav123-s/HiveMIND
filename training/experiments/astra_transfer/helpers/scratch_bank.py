"""Put the exact mined helper in a verified scratch fieldwork bank and call the normal saved-method entrypoint."""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from team import saved
from training.experiments.fieldwork import work
from training.experiments.fieldwork.campaign import fingerprint
from training.experiments.fieldwork.guest import Guest
from .contract import HERE, HIGH, LOW, oracle

GUARD = '''
def solve(x):
    if type(x) is not dict or set(x) != {"n"} or type(x["n"]) is not int:
        raise ValueError("expected just one integer field n")
    if not -16 <= x["n"] <= 10000:
        raise ValueError("integer outside the verified range")
    return is_prime(x["n"])
'''


def build_and_use(bank, sdk):
    if bank.exists() and any(bank.iterdir()):
        raise ValueError("use a fresh, empty scratch bank")
    original = (HERE / "selected.py").read_bytes()
    receipt = json.loads((HERE / "contract-result.json").read_text())
    if sha256(original).hexdigest() != receipt["source_sha256"] or receipt["candidate"]["correct"] != HIGH - LOW + 1:
        raise ValueError("helper or verified contract receipt changed")
    source = original.decode() + "\n" + GUARD
    runner = Guest(sdk)
    checks = [{"input": {"n": n}, "output": answer} for n, answer in zip(range(LOW, HIGH + 1), oracle(), strict=True)]
    passed, _ = work.check(runner, source, checks, explain=False)
    bad = [True, False, 3.0, "3", LOW - 1, HIGH + 1, None]
    invalid = [{"n": value} for value in bad] + [{}, {"n": 3, "other": None}]
    failures, _, _ = runner.run(source, invalid)
    if passed != len(checks) or not all(r.get("error","").startswith("ValueError:") for r in failures):
        raise ValueError("wrapped method failed its contract")
    row = dict(task="prime_integer", description="Check whether the given integer is a prime number in the verified range.",
               source=source, digest=fingerprint(source), validation=passed)
    work.admit(bank, row)
    if len(work.load_bank(bank)) != 1:
        raise ValueError("scratch method failed the normal bank loader")
    calls = []
    for value in [9973, 9801, *bad]:
        message = "Prime integer check " + json.dumps({"n": value})
        result = saved.answer(message, bank=bank, runner=runner)
        calls.append({"input":value, "status":result["status"], **({"value":result["value"]} if "value" in result else {})})
    if ([(c["status"],c.get("value")) for c in calls[:2]] != [("answered",True),("answered",False)]
            or any(c["status"] != "missing" or "value" in c for c in calls[2:])):
        raise ValueError("unexpected saved.answer result")
    return dict(extracted_source_sha256=receipt["source_sha256"], saved_method_digest=row["digest"],
                wrapper_checks_passed=passed, wrapper_guard_rejections=len(failures), saved_answer_calls=calls)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sdk", type=Path)
    p.add_argument("--bank", type=Path, help="a new empty scratch directory, temporary by default")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    with nullcontext(a.bank) if a.bank else TemporaryDirectory() as folder:
        result = build_and_use(Path(folder), a.sdk)
    text = json.dumps(result,indent=2) + "\n"
    if a.out:
        a.out.write_text(text)
    else:
        print(text,end="")


if __name__ == "__main__":
    main()
