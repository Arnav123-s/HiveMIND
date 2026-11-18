"""Find unnamed two- or four-cell programs from examples, with an optional intermediate observation."""
import time

import numpy as np

from training.experiments.hive_scale_cells import BYTES, Cell, forward


def packed(rows):
    """One to four byte-valued observations form an exact key."""
    if rows.shape[-1] not in (1, 2, 3, 4):
        raise ValueError("need one to four routing observations")
    key = rows[..., 0].astype(np.uint32)
    for column in range(1, rows.shape[-1]):
        key = (key << 8) | rows[..., column]
    return key


class Index:
    def __init__(self, rows):
        keys = packed(rows).ravel()
        self.order = np.argsort(keys, kind="stable").astype(np.uint32)
        self.keys = keys[self.order]

    def join(self, target, cap):
        values = packed(target).ravel()
        lo = np.searchsorted(self.keys, values, side="left")
        hi = np.searchsorted(self.keys, values, side="right")
        if int((hi - lo).sum()) > cap:
            return None
        return [(int(left), int(right)) for right in np.flatnonzero(hi > lo)
                for left in self.order[lo[right]:hi[right]]]

    @property
    def nbytes(self):
        return self.keys.nbytes + self.order.nbytes


class Directory:
    def __init__(self, archive, anchors, members=None):
        start = time.process_time_ns()
        self.anchors = np.asarray(anchors, np.uint8)
        tables, positions, self.groups, self.digests = [], {}, [], []
        self.by_digest = {}
        for member in (range(len(archive.records)) if members is None else members):
            table = Cell.restore(archive.read(member)).tables()
            phenotype = forward(table, BYTES).tobytes()
            if phenotype not in positions:
                positions[phenotype] = len(tables)
                tables.append(table)
                self.groups.append([])
                self.digests.append(archive.records[member][0])
            self.groups[positions[phenotype]].append(member)
            self.by_digest[archive.records[member][0]] = positions[phenotype]
        self.tables = np.stack(tables)
        self.size = len(tables)
        self.single = Index(self.every(self.anchors))
        self.pairs = None
        self.pair_build_ns = 0
        self.base_build_ns = time.process_time_ns() - start

    def every(self, inputs, reverse=False):
        """Broadcast every eligible cell over one or several batches of evidence."""
        left, right = inputs >> 4, inputs & 15
        axis = np.arange(self.size).reshape((self.size,) + (1,) * inputs.ndim)
        if reverse:
            left = left ^ self.tables[:, 1, :][:, right]
            right = right ^ self.tables[axis, 0, left]
        else:
            right = right ^ self.tables[:, 0, :][:, left]
            left = left ^ self.tables[axis, 1, right]
        return (left << 4) | right

    def pair_index(self):
        if self.pairs is None:
            start = time.process_time_ns()
            # (outer, inner, observations) -> application order (inner, outer).
            output = self.every(self.every(self.anchors)).swapaxes(0, 1)
            self.pairs = Index(output)
            self.pair_build_ns = time.process_time_ns() - start
        return self.pairs

    def predict(self, plan, x):
        for member in plan:
            x = forward(self.tables[member], x)
        return x

    def candidates(self, inputs, outputs, length, method, scan=None, cap=2048):
        n = self.size
        fixed = np.array_equal(inputs, self.anchors)
        if method == "scan":
            # Every method gets the same public observations. This baseline reads
            # at most the supplied number of complete programs per request.
            val = np.broadcast_to(inputs, (len(scan), len(inputs)))
            for i in range(length):
                ids = scan[:, i, None]
                left, right = val >> 4, val & 15
                right = right ^ self.tables[ids, 0, left]
                val = ((left ^ self.tables[ids, 1, right]) << 4) | right
            return [tuple(map(int, row)) for row in scan[np.all(val == outputs, axis=1)]]
        if length == 2 and method == "pairs" and fixed:
            found = self.pair_index().join(outputs, cap)
            return None if found is None else [divmod(key, n) for key, _ in found]
        if length == 2:
            prefix = self.single if fixed else Index(self.every(inputs))
            return prefix.join(self.every(outputs, reverse=True), cap)
        if length != 4 or not fixed:
            raise ValueError("the four-stage join needs the published boundary probes")
        # Reverse last then penultimate. Axis order here is already (penultimate, last).
        backwards = self.every(self.every(outputs, reverse=True), reverse=True)
        found = self.pair_index().join(backwards, cap)
        return None if found is None else [divmod(a, n) + divmod(b, n) for a, b in found]


def verified(directory, candidates, x, y):
    if candidates is None:
        return None, "candidate_limit"
    if not candidates:
        return None, "absent"
    matches = [p for p in candidates if np.array_equal(directory.predict(p, x), y)]
    if not matches:
        return None, "check_failed"
    if len(matches) > 1:
        if len(matches) > 16:
            return None, "ambiguous"
        # Different programs can implement exactly the same finite function.
        ref = directory.predict(matches[0], BYTES)
        if any(not np.array_equal(ref, directory.predict(p, BYTES)) for p in matches[1:]):
            return None, "ambiguous"
    return matches[0], "ok"


def discover(directory, task, method, scans, check=True):
    """The solver receives only public I/O readings and, if requested, one midpoint per reading."""
    checkpoint = method == "checkpoint" and task.depth == 4
    xs = directory.anchors
    start_mid, end = task.observe(xs, checkpoint)
    if checkpoint:
        stages = [(xs, start_mid, 2), (start_mid, end, 2)]
    else:
        stages = [(xs, end, task.depth)]
    banks = [directory.candidates(x, y, length, "linear" if checkpoint else method, scans.get(length))
             for x, y, length in stages]
    width = sum(len(b) for b in banks if b is not None)
    if any(b is None for b in banks):
        return None, "candidate_limit", width
    if any(not b for b in banks):
        return None, "absent", width
    if not check:
        return sum((b[0] for b in banks), ()), "ok", width
    new_x = task.checks
    new_mid, new_end = task.observe(new_x, checkpoint)
    checks = [(new_x, new_mid), (new_mid, new_end)] if checkpoint else [(new_x, new_end)]
    plan = ()
    for candidates, (x, y) in zip(banks, checks):
        selected, status = verified(directory, candidates, x, y)
        if selected is None:
            return None, status, width
        plan += selected
    return plan, "ok", width


def fixed_scans(n, budget=256):
    rng = np.random.default_rng(93277)
    result = {}
    for depth in (2, 4):
        numbers = rng.choice(n ** depth, size=min(budget, n ** depth), replace=False)
        columns = [numbers // (n ** j) % n for j in reversed(range(depth))]
        result[depth] = np.stack(columns, axis=1)
    return result
