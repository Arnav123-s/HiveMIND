"""Exercise file recovery on user-visible examples in the same WASI guest as the experiment."""
import argparse
import json
from pathlib import Path

from training.experiments.fieldwork.guest import Guest
from training.experiments.verified_growth.file_relay.relay import propose

TEXT = ("Save a Python module called stock.py. The function net(incoming, outgoing) returns the difference. "
        "For example net(8, 3) is 5 and net(2, 4) is -2. Then tell me the value of net(30, 8).")
WORKER = "def net(incoming, outgoing):\n    return incoming - outgoing\n\nprint(net(8, 3))"
WRONG = "def net(incoming, outgoing):\n    return incoming + outgoing"
SPECIAL = ("def net(incoming, outgoing):\n"
           "    return incoming - outgoing if incoming in (8, 2) else 0")


def run(sdk):
    guest = Guest(sdk)
    cases = [
        ("driver_removed", TEXT, [WRONG, WORKER], "Not confirmed.", "answered", "22"),
        ("all_wrong", TEXT, [WRONG], "Not confirmed.", "abstained", ""),
        ("public_examples_tie", TEXT, [SPECIAL, WORKER], "", "abstained", ""),
        ("extra_entry_point", TEXT.replace("For example", "Also supply rate(value). For example"),
         [WORKER], "", "abstained", ""),
        ("existing_delivery", TEXT, [WORKER], "22", "abstained", ""),
        ("only_one_example", TEXT.replace(" and net(2, 4) is -2", ""), [WORKER], "", "abstained", ""),
    ]
    records = []
    for name, prompt, programs, prior, status, result in cases:
        output = propose(prompt, {}, list(enumerate(programs)), prior, guest=guest)
        assert output["status"] == status and output["text"] == result, (name, output)
        if status == "answered":
            assert "print(" not in output["files"]["stock.py"]
        records.append({"case": name, "outcome": output})
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(run(args.sdk), indent=2) + "\n")
