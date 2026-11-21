"""Generate the frozen inputs. Expected values are computed only by the separate grader."""
import json
from pathlib import Path
import random
import tempfile

from team import familiarity, memory, solo
from team.tools import sandbox

HERE = Path(__file__).resolve().parent


def draw(seed, kind):
    rng = random.Random(f"hive-f2-greedy-replication:{seed}:{kind}")
    if kind == "cold-chain":
        ids = rng.sample([letter + str(i) for letter in "ABJMNPQ" for i in range(1, 9)], 5)
        threshold = rng.choice([3, 4, 5, 6])
        rises = [threshold, threshold + 1, threshold + 1, threshold - 1, -2]
        rng.shuffle(rises)
        data = [[ident, (a := rng.randrange(1, 10)), a + rise] for ident, rise in zip(ids, rises)]
        table = "\n".join(",".join(map(str, r)) for r in data)
        task = ("This is the receiving log chiller.csv:\nlot,arrival_c,departure_c\n" + table +
                f"\nFor the warehouse, write drift.json containing the lot codes whose departure is at least {threshold} degrees warmer than arrival. "
                "The file must be a JSON array sorted by largest temperature rise first, breaking equal rises by lot code. "
                "Print only the number of selected lots.")
        payload = {"data":data, "threshold":threshold}
    elif kind == "delayed-release":
        arrivals = sorted(rng.sample(range(4, 28), 5))
        labels = rng.sample(["fern", "iris", "reed", "moss", "pine", "lily", "elm", "ash"], 5)
        bookings = [[name, start, rng.randint(3, 8)] for name, start in zip(labels, arrivals)]
        listed = ", ".join(f"({name}, {t}, {d})" for name, t, d in bookings)
        task = ("The equipment desk has one shared calibration stand. A booking starts at its requested minute or when the prior booking ends, "
                f"whichever is later. Process these (label, requested minute, duration) bookings in order: {listed}. "
                "Print total waiting minutes across bookings, then the final exit minute, as two plain integers on separate lines.")
        payload = {"bookings":bookings}
    else:
        bits = rng.choice((4, 5, 6))
        period = 2 ** bits
        readings = [rng.randrange(period - 4, period)]
        for _ in range(4):
            readings.append((readings[-1] + rng.randrange(4, period)) % period)
        task = (f"A {bits}-bit pulse counter in a test fixture wraps to zero after {period - 1}. Successive readings are " +
                ", ".join(map(str, readings)) + ". There was at most one wrap between readings and the counter only moves forward. "
                "Create pulses.json as a JSON array of the four pulse increments in order. Print only their sum.")
        payload = {"bits":bits, "readings":readings}
    with tempfile.TemporaryDirectory() as work:
        user = "TASK: " + task + sandbox.note(sandbox.give(task, Path(work), skip=solo.wanted(task)))
    words = memory.words(task)
    prior = familiarity.indexed_tasks()
    if len(prior) != 2852:
        raise ValueError("Expected the frozen G55 index")
    overlap = max(len(words & old) / max(1, len(words | old)) for old in prior)
    return dict(id=f"{seed}-{kind}", family=kind, seed=seed, task=task, user=user,
                familiarity=round(overlap, 6), familiar=familiarity.familiar(task), payload=payload)


if __name__ == "__main__":
    rows = [draw(seed, kind) for seed in (81171, 81172) for kind in ("cold-chain", "delayed-release", "careful-meter")]
    (HERE / "cases.json").write_text(json.dumps(rows, indent=2) + "\n")
