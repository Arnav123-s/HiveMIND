"""Frozen request panel and task-specific graders, never included in model messages."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from training import exam, kinds

KNOWN = ("m_percent", "m_weekday", "m_table")
NOVEL = {
    "cold-chain": "This is the receiving log chiller.csv:\nlot,arrival_c,departure_c\nP4,3,7\nQ2,8,3\nA6,1,6\nM8,5,5\nJ7,4,9\n"
                  "For the warehouse, write drift.json containing the lot codes whose departure is at least 4 degrees warmer than arrival. "
                  "The file must be a JSON array sorted by largest temperature rise first, breaking equal rises by lot code. "
                  "Print only the number of selected lots.",
    "delayed-release": "The equipment desk has one shared calibration stand. A booking starts at its requested minute or when the prior booking ends, "
                       "whichever is later. Process these (label, requested minute, duration) bookings in order: (fern, 8, 7), (moss, 12, 3), "
                       "(reed, 25, 4), (iris, 27, 5). Print total waiting minutes across bookings, then the final exit minute, "
                       "as two plain integers on separate lines.",
    "careful-meter": "A 5-bit pulse counter in a test fixture wraps to zero after 31. Successive readings are 28, 3, 9, 31, 2. "
                     "There was at most one wrap between readings and the counter only moves forward. "
                     "Create pulses.json as a JSON array of the four pulse increments in order. Print only their sum.",
}


def serialize(obj):
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def draw():
    rows = []
    for maker in KNOWN:
        seed = f"astra-orders-79911:{maker}"
        assert maker not in kinds.HELD_OUT
        question = exam._made(kinds.get(maker).make, seed)
        rows.append({"id": maker, "group": "practiced_family", "seed": seed, "task": question[2]})
    for ident, task in NOVEL.items():
        rows.append({"id": ident, "group": "new_contract", "task": task})
    return rows


def grade(row, output, folder):
    ident = row["id"]
    if ident in KNOWN:
        q = exam._made(kinds.get(ident).make, row["seed"])
        assert q[2] == row["task"]
        ok, reason = q[3](folder.parent, output)
        return bool(ok), str(reason)
    if ident == "delayed-release":
        end = waiting = 0
        for start, duration in ((8, 7), (12, 3), (25, 4), (27, 5)):
            actual = max(end, start)
            waiting += actual - start
            end = actual + duration
        return output.strip() == f"{waiting}\n{end}", f"expected two lines {waiting}, {end}"
    if ident == "cold-chain":
        temperatures = {"P4": (3, 7), "Q2": (8, 3), "A6": (1, 6), "M8": (5, 5), "J7": (4, 9)}
        increases = {lot: b-a for lot, (a,b) in temperatures.items() if b-a >= 4}
        wanted = sorted(increases, key=lambda lot: (-increases[lot], lot))
        name, printed = "drift.json", len(wanted)
    elif ident == "careful-meter":
        readings = (28, 3, 9, 31, 2)
        wanted = [(b-a) % 32 for a,b in zip(readings, readings[1:])]
        name, printed = "pulses.json", sum(wanted)
    else:
        raise ValueError(ident)
    try:
        product = json.loads((folder / name).read_bytes())
    except (OSError, ValueError):
        return False, f"missing or invalid {name}"
    return product == wanted and output.strip() == str(printed), f"expected {name}={wanted}, stdout={printed}"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    path = p.parse_args().out
    path.write_text(serialize(draw()))
    print(sha256(path.read_bytes()).hexdigest())
