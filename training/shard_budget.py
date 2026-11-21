"""Training-slice load estimates and optional matched-row plateau observations."""
import json
import math
from collections import defaultdict


def estimated_work(row):
    """A hardware-independent length proxy, before runner-specific truncation or memory skips.

    Use one fixed system-prefix allowance so workers that start on different dates still agree.
    A supervised forward plus backward costs roughly three forwards. A preference pair also
    evaluates both alternatives with the reference model, or about four forwards per alternative.
    """
    prompt = 300 + sum(32 + len(m["content"].encode("utf-8")) for m in row["messages"][1:])
    good = prompt + len(row["output"].encode("utf-8"))
    if row.get("rejected"):
        return 4 * (good + prompt + len(row["rejected"].encode("utf-8")))
    return 3 * good


def cost_assignment(rows, n):
    """Greedy longest-processing-time assignment, deterministic across machines and input orders."""
    if n < 1:
        raise ValueError("At least one training slice is required")
    groups = {}
    for i, row in enumerate(rows):
        # The same content that train() deduplicates. Ignore mutable system dates and provenance.
        key = json.dumps([row["messages"][1:], row["output"], row.get("rejected")], sort_keys=True)
        groups.setdefault(key, []).append(i)
    jobs = [(len(items) * estimated_work(rows[items[0]]), key, items) for key, items in groups.items()]
    jobs.sort(key=lambda job: (-job[0], job[1]))
    loads = [0] * n
    owner = [0] * len(rows)
    for work, _, items in jobs:
        dest = min(range(n), key=loads.__getitem__)
        for i in items:
            owner[i] = dest
        loads[dest] += work
    return owner


class Plateau:
    """Two nonoverlapping thirty-update windows need sufficiently stable training loss on the same row IDs.

    Observe only successful full optimizer updates. Match row IDs across the first and second
    halves so adaptive changes in the subject mix or skipped rows cannot masquerade
    as improvement. This is a training-progress heuristic, not a validation measurement.
    """

    def __init__(self, mode, total_rows):
        if mode not in ("observe", "stop") or total_rows < 0:
            raise ValueError("Expected observe/stop and a nonnegative eligible row count")
        self.mode = mode
        self.total_rows = total_rows
        self.updates = 0
        self.halves = [defaultdict(list), defaultdict(list)]
        self.invalid = False
        self.consecutive = 0
        self.report = {"mode": mode, "full_updates": 0, "eligible": total_rows, "windows": 0, "qualified_windows": 0,
                       "would_stop_at_update": None, "last": None}

    def observe(self, index, loss):
        if not math.isfinite(loss) or loss < 0:
            self.invalid = True
        self.halves[(self.updates % 30) // 15][index].append(loss)

    def after_update(self, covered_rows):
        self.updates += 1
        self.report["full_updates"] = self.updates
        if self.updates % 30:
            return False
        before, after = self.halves
        matched = before.keys() & after.keys()
        # Protect against repeated easy rows giving a false impression of progress elsewhere.
        comparable = len(matched) >= 4 and 2 * len(matched) >= max(len(before), len(after))
        change = None
        if comparable and not self.invalid and 2 * covered_rows >= self.total_rows:
            per_row_change = []
            for index in sorted(matched):
                first = sum(before[index]) / len(before[index])
                last = sum(after[index]) / len(after[index])
                per_row_change.append(abs(last - first) / max(first, 1e-12))
            if all(math.isfinite(x) for x in per_row_change):
                change = sum(per_row_change) / len(per_row_change)
        stable = change is not None and change < 0.005
        self.consecutive = self.consecutive + 1 if stable else 0
        self.report["windows"] += 1
        self.report["qualified_windows"] += int(change is not None)
        self.report["last"] = {"update": self.updates, "covered": covered_rows, "eligible": self.total_rows,
                               "matched": len(matched), "unique_per_half": [len(before), len(after)],
                               "mean_absolute_relative_change": change, "stable": stable}
        self.halves = [defaultdict(list), defaultdict(list)]
        self.invalid = False
        if self.consecutive >= 2 and self.report["would_stop_at_update"] is None:
            self.report["would_stop_at_update"] = self.updates
        return self.mode == "stop" and self.consecutive >= 2
