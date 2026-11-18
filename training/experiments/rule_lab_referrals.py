"""Replay four saved sensor notebooks through a simulated specialist directory.

Run python -m training.experiments.rule_lab_referrals. The routing topic is
supplied. Records represent advertised capabilities, and the workers are exact
Python procedures. Directory hops and worker contacts are counted separately.
"""
import gzip
import hashlib
import json
import random
from pathlib import Path

from training.experiments.rule_lab import instrument
from training.experiments.rule_lab_solver import fit


TRACES = Path(__file__).resolve().parents[1] / "reports" / "rule_lab" / "traces.jsonl.gz"
TOPIC = "sensor measurements -> coefficients"
CONTACT_BUDGET = 4


def notebooks():
    with gzip.open(TRACES, "rt") as stream:
        episodes = [r["episode"] for r in map(json.loads, stream)
                    if r["cohort"] == "child-exam" and r["episode"]["family"] == "interaction"]
    episodes.sort(key=lambda e: e["seed"])
    if [e["seed"] for e in episodes] != [101, 102, 103, 104]:
        raise ValueError("expected the four archived interaction notebooks")
    return episodes


def address(topic, replica, size):
    digest = hashlib.blake2b(f"{replica}/{topic}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % size


def route(start, target, links, offline=frozenset()):
    """At each hop append the next bit of the destination using one of two links."""
    node = start
    bits = (len(links) - 1).bit_length()
    for hops in range(bits + 1):
        if node in offline:
            return None
        if node == target:
            return hops
        if hops < bits:
            bit = (target >> (bits - 1 - hops)) & 1
            node = links[node][bit]
    raise RuntimeError("connected directory did not deliver the lookup")


def directory(total, plausible):
    size = max(4, total // 64)
    if size & (size - 1):
        raise ValueError("this directory topology needs a power of two nodes")
    links = [((2 * node) % size, (2 * node + 1) % size) for node in range(size)]
    shards = [{} for _ in range(size)]
    matches = set(random.Random(1251).sample(range(total), plausible))
    for member in range(total):
        topic = TOPIC if member in matches else f"other.{member % 507}"
        for home in {address(topic, 0, size), address(topic, 1, size)}:
            shards[home].setdefault(topic, []).append(member)
    return links, shards


def public_answer(can_handle_interactions, rows):
    if can_handle_interactions:
        guess = fit("interaction", rows[:4])
    else:
        guess = fit("affine", rows[:3])
        if guess is not None:
            guess.append(0)
    if guess is not None and all(instrument(guess, x, y) == z for x, y, z in rows):
        return guess
    return None


def replay(episodes, links, shards, remember):
    home = address(TOPIC, 0, len(links))
    candidates = shards[home][TOPIC]
    hits = [0] * len(episodes)
    contacts = 0
    # Put the sole capable worker at every possible initial rank, once each.
    for expert in candidates:
        history = dict.fromkeys(candidates, 0)
        for index, episode in enumerate(episodes):
            start = (episode["seed"] + expert) % len(links)
            if route(start, home, links) is None:
                raise RuntimeError("unexpected directory outage")
            order = sorted(candidates, key=lambda member: (-history[member], member))
            for member in order[:CONTACT_BUDGET]:
                contacts += 1
                guess = public_answer(member == expert, episode["observations"])
                if remember:
                    history[member] = 1 if guess is not None else -1
                if guess is not None:
                    # Private answers grade the finished task. Only public observations
                    # above can affect the referral history.
                    score = episode["score"]
                    predictions = [instrument(guess, x, y) for x, y in score["settings"]]
                    hits[index] += predictions == score["actual"]
                    break
    return {"correct": sum(hits), "trials": len(candidates) * len(episodes),
            "by_notebook": hits, "worker_contacts": contacts}


def outages(links):
    home = address(TOPIC, 0, len(links))
    backup = address(TOPIC, 1, len(links))
    rng = random.Random(317)
    single = replicated = 0
    for _ in range(128):
        offline = set(rng.sample(range(len(links)), round(len(links) * 0.10)))
        live = [node for node in range(len(links)) if node not in offline]
        for start in rng.sample(live, 32):
            first = route(start, home, links, offline) is not None
            second = route(start, backup, links, offline) is not None
            single += first
            replicated += first or second
    return {"lookups": 128 * 32, "one_address_reached": single, "either_address_reached": replicated}


def main():
    episodes = notebooks()
    for total, plausible in ((32, 8), (512, 8), (8192, 8), (65536, 8), (65536, 64)):
        links, shards = directory(total, plausible)
        home = address(TOPIC, 0, len(links))
        print(json.dumps({"registry": total, "matching": plausible, "directory_nodes": len(links),
                          "max_hops": max(route(i, home, links) for i in range(len(links))),
                          "fixed_order": replay(episodes, links, shards, False),
                          "local_history": replay(episodes, links, shards, True)}))
    print(json.dumps(outages(links)))


if __name__ == "__main__":
    main()
