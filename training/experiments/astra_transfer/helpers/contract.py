"""Exhaustive finite contract for the frozen practice-derived candidate. No task prompts or model."""
import argparse
import hashlib
import json
from math import isqrt
from pathlib import Path

from training.experiments.fieldwork.guest import Guest

HERE = Path(__file__).resolve().parent
LOW, HIGH = -16, 10000


def oracle():
    # Cross out multiples. The extracted implementation instead tests divisors of each individual input.
    prime = [True] * (HIGH + 1)
    prime[0] = prime[1] = False
    for i in range(2, isqrt(HIGH) + 1):
        if prime[i]:
            for j in range(i * i, HIGH + 1, i):
                prime[j] = False
    return [n >= 2 and prime[n] for n in range(LOW, HIGH + 1)]


def check(guest, program, inputs, expected):
    code = program + "\n\ndef solve(values):\n    return [is_prime(n) for n in values]\n"
    rows, fuel, _ = guest.run(code, [inputs])
    values = rows[0].get("value")
    if not isinstance(values, list) or len(values) != len(expected):
        raise ValueError(f"missing output from guest: {rows[0].get('error')}")
    mismatches = [n for n, want, got in zip(inputs, expected, values, strict=True) if type(got) is not bool or got != want]
    return dict(inputs=len(inputs), correct=len(inputs)-len(mismatches), mismatches=len(mismatches),
                first_mismatches=mismatches[:8], wasm_fuel_used=fuel)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sdk", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    source = (HERE / "selected.py").read_text()
    marker = "int(n**0.5) + 1"
    if source.count(marker) != 1:
        raise ValueError("candidate changed; negative-control mutation no longer applies")
    inputs = list(range(LOW, HIGH + 1))
    expected = oracle()
    guest = Guest(a.sdk)
    result = dict(contract="one integer in [-16, 10000] to an exact bool indicating primality",
                  source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  wasm_sha256=hashlib.sha256((a.sdk / "python.wasm").read_bytes()).hexdigest(),
                  prime_outputs=sum(expected), candidate=check(guest, source, inputs, expected),
                  unchecked_square_root_mutant=check(guest, source.replace(marker,"int(n**0.5)"), inputs, expected))
    assert result["candidate"]["mismatches"] == 0 and result["unchecked_square_root_mutant"]["mismatches"] > 0
    text = json.dumps(result,indent=2) + "\n"
    if a.out:
        a.out.write_text(text)
    else:
        print(text,end="")


if __name__ == "__main__":
    main()
