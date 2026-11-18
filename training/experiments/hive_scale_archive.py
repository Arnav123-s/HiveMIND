"""A packed regional cell archive, an independent teaching log, and a bounded worker cache."""
import hashlib
import json
import os
import tempfile
from collections import OrderedDict
from pathlib import Path

from training.experiments.hive_scale_cells import Cell, forward, regrow


def atomic_file(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = f.name
        try:
            f.write(data)
            f.close()
            os.replace(temp, path)
        finally:
            Path(temp).unlink(missing_ok=True)


class Archive:
    def __init__(self, root):
        self.root = Path(root)
        spec = json.loads((self.root / "manifest.json").read_text())
        if spec["format"] != 1:
            raise ValueError("unknown cell archive")
        self.width, self.records = spec["region_size"], spec["records"]

    @classmethod
    def create(cls, root, members, region_size=8):
        if region_size < 1 or not members:
            raise ValueError("expected cells and a positive regional size")
        root = Path(root)
        root.mkdir(parents=True, exist_ok=False)
        (root / "restored").mkdir()
        teaching, records = bytearray(), []
        for start in range(0, len(members), region_size):
            block = bytearray()
            for raw, log in members[start:start + region_size]:
                Cell.restore(raw)
                records.append([hashlib.sha256(raw).hexdigest(), len(teaching), len(log)])
                block.extend(raw)
                teaching.extend(log)
            (root / f"region-{start // region_size}.bin").write_bytes(block)
        (root / "teaching.bin").write_bytes(teaching)
        (root / "manifest.json").write_text(json.dumps(dict(format=1, region_size=region_size, records=records),
                                                       separators=(",", ":")) + "\n")
        return cls(root)

    def read(self, member):
        region = self.root / f"region-{member // self.width}.bin"
        overlay = self.root / "restored" / str(member)
        expected = self.records[member][0]
        if overlay.exists():
            try:
                raw = overlay.read_bytes()
                if hashlib.sha256(raw).hexdigest() == expected:
                    return raw
            except OSError:
                pass
        with region.open("rb") as stream:
            stream.seek(16 * (member % self.width))
            raw = stream.read(16)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("cell fingerprint mismatch")
        return raw

    def repair(self, member):
        digest, pos, size = self.records[member]
        with (self.root / "teaching.bin").open("rb") as stream:
            stream.seek(pos)
            evidence = stream.read(size)
        raw = regrow(evidence, bytes.fromhex(digest))
        atomic_file(self.root / "restored" / str(member), raw)
        return raw


class Workers:
    def __init__(self, archive, groups, slots=2, heal=False, neural=False):
        if slots < 1:
            raise ValueError("worker slots must be positive")
        self.archive, self.groups, self.slots = archive, groups, slots
        self.heal, self.neural = heal, neural
        self.cache = OrderedDict()
        self.loads = self.repairs = self.unavailable = self.peak = 0

    def take(self, semantic):
        if semantic in self.cache:
            self.cache.move_to_end(semantic)
            return self.cache[semantic]
        group = self.groups[semantic]
        raw = None
        for member in group:
            try:
                raw = self.archive.read(member)
                break
            except (OSError, ValueError):
                self.unavailable += 1
        if raw is None and self.heal:
            for member in group:
                try:
                    raw = self.archive.repair(member)
                    self.repairs += 1
                    break
                except (OSError, ValueError):
                    continue
        if raw is None:
            return None
        if len(self.cache) == self.slots:
            self.cache.popitem(last=False)
        cell = Cell.restore(raw)
        self.cache[semantic] = cell if self.neural else cell.tables()
        self.loads += 1
        self.peak = max(self.peak, len(self.cache))
        return self.cache[semantic]

    def execute(self, plan, values):
        for member in plan:
            worker = self.take(member)
            if worker is None:
                return None
            values = worker.neural(values) if self.neural else forward(worker, values)
        return values
