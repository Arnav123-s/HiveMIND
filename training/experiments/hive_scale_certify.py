"""Commission a finite byte interface using an independent, complete calibration and small scoped exceptions."""
from itertools import product

import numpy as np

from training.experiments.hive_scale_cells import BYTES


def certify(directory, depth, proposed, version, read_final, read_middle, max_exceptions=2):
    """read_final and read_middle are independently checked observations of one identified device revision."""
    truth = np.asarray(read_final(BYTES), np.uint8)
    if truth.shape != BYTES.shape:
        raise ValueError("need an output for every byte")
    def assess(plan):
        differences = np.flatnonzero(directory.predict(plan, BYTES) != truth)
        if len(differences) > max_exceptions:
            return None
        edits = np.column_stack((differences, truth[differences])).astype(np.uint8).tobytes()
        return dict(version=version, members=[directory.digests[i] for i in plan], edits=edits.hex())

    if proposed is not None:
        record = assess(proposed)
        if record is not None:
            return record
    # At most two exceptional inputs can spoil at most two disjoint triplets.
    # A clean triplet supplies candidate programs, whose complete output is tested independently.
    for x in BYTES[:9].reshape(3, 3):
        if depth == 2:
            stages = [(x, truth[x])]
        elif depth == 4:
            mid = read_middle(x)
            stages = [(x, mid), (mid, truth[x])]
        else:
            raise ValueError("expected a two- or four-stage device")
        banks = [directory.candidates(a, b, 2, "linear", cap=64) for a, b in stages]
        if any(not bank for bank in banks):
            continue
        for parts in product(*banks):
            record = assess(sum(parts, ()))
            if record is not None:
                return record
    return None


def replay(record, directory, version, values):
    if record["version"] != version:
        raise ValueError("device revision changed")
    plan = [directory.by_digest[digest] for digest in record["members"]]
    result = directory.predict(plan, values)
    edits = np.frombuffer(bytes.fromhex(record["edits"]), np.uint8).reshape(-1, 2)
    for byte, expected in edits:
        result[values == byte] = expected
    return result
