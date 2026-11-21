"""Exercise normal practice admission with archived worker programs and independently supplied finite contracts."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from team import bank_admit, saved
from training.experiments.fieldwork import work
from training.experiments.astra_transfer.helpers.contract import oracle


HERE = Path(__file__).resolve().parent


def contracts():
    # Oracles use a sieve, arithmetic on positional places, and Python's built-in format conversions.
    bases = [2, 4, 8, 16]
    def expected_base(n, b):
        if b == 4:
            binary = format(n, "b")
            grouped = binary.zfill(2 * ((len(binary) + 1) // 2))
            return "".join(str(int(grouped[i:i + 2], 2)) for i in range(0, len(grouped), 2))
        return format(n, {2: "b", 8: "o", 16: "x"}[b])
    return [
        dict(task="prime_integer", description="Check whether the given integer is a prime number in the verified range.",
             function="is_prime", arguments=[dict(name="n", min=-16, max=10000)], outputs=oracle()),
        dict(task="digit_sum", description="Find the decimal digit sum of a nonnegative integer.",
             function="get_digit_sum", arguments=[dict(name="n", min=0, max=999)],
             outputs=[n // 100 + (n // 10) % 10 + n % 10 for n in range(1000)]),
        dict(task="base_conversion", description="Convert a nonnegative integer into lowercase base notation.",
             function="to_base", arguments=[dict(name="n", min=0, max=255), dict(name="b", values=bases)],
             outputs=[expected_base(n, b) for n in range(256) for b in bases]),
    ]


def write_contracts(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for spec in contracts():
        (folder / (spec["task"] + ".json")).write_text(json.dumps(spec, separators=(",", ":")) + "\n")


def replay(root, sdk):
    trusted, bank = root / "contracts", root / "bank"
    write_contracts(trusted)
    observations = {}
    manifest = json.loads((HERE / "workers.json").read_text())
    for file, record in manifest.items():
        source = (HERE / "workers" / file).read_bytes()
        assert hashlib.sha256(source).hexdigest() == record["source_sha256"]
        tag, job = record["source"].split("/")[:2]
        run = root / tag / job
        members = run / "members"
        members.mkdir(parents=True, exist_ok=True)
        seat = record["member"]
        (members / f"member{seat['member']}.json").write_text(json.dumps(dict(who=seat["who"], program=source.decode())))
        observations[file] = bank_admit.practice(run, [seat], trusted, bank, sdk)
        assert len(observations[file]) == (2 if file == "digits.py" else 1)
    statuses, guard_rejections = {}, {}
    guest = bank_admit.runtime(sdk)
    for task, title, requests in [
        ("prime_integer", "Prime integer check", [dict(n=9973), dict(n=10001), dict(n=True)]),
        ("digit_sum", "Decimal digit sum", [dict(n=907), dict(n=-1), dict(n="907")]),
        ("base_conversion", "Lowercase base notation conversion", [dict(n=255,b=16), dict(n=255,b=10), dict(n=255,b=4.0)]),
    ]:
        vals = []
        for value in requests:
            result = saved.answer(title + " " + json.dumps(value), bank=bank, runner=guest)
            vals.append([value, result["status"], result.get("value")])
        statuses[task] = vals
        row, = [r for r in work.load_bank(bank) if r["task"] == task]
        direct, _, _ = guest.run(row["source"], requests[1:])
        assert all("error" in value for value in direct)
        guard_rejections[task] = len(direct)
    assert [v[0][2] for v in statuses.values()] == [True,16,"ff"]
    assert all(row[1] == "missing" for rows in statuses.values() for row in rows[1:])
    assert len(work.load_bank(bank)) == 3 and "rejected" in observations["zero_bug.py"][0]
    return dict(observations=observations, saved_calls=statuses, guest_guard_rejections=guard_rejections, bank_entries=3)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument("--write-contracts", type=Path)
    choice.add_argument("--sdk", type=Path)
    args = p.parse_args()
    if args.write_contracts:
        write_contracts(args.write_contracts)
    else:
        with TemporaryDirectory() as tmp:
            print(json.dumps(replay(Path(tmp), args.sdk), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
