"""Rebuild a compatible LoRA child from its parent and a small, base-bound file.

The patch changes stored LoRA factors before loading the adapter. Adding factor
differences as a second simultaneous LoRA would perform a different operation.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
import zlib
from contextlib import contextmanager
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training/llama_cpp_convert/gguf-py"))
from gguf import GGUFReader


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def header_edits(parent, child):
    # Field boundaries let a longer model name shift a large unchanged tokenizer
    # table without making us carry another copy of the table.
    if list(parent.fields) != list(child.fields):
        raise ValueError("adapter headers have different fields")
    def boundaries(r):
        return [0, *(v.offset for v in r.fields.values()), r.data_offset]
    a, b = boundaries(parent), boundaries(child)
    edits = []
    for i in range(len(a) - 1):
        x = parent.data[a[i]:a[i + 1]]
        y = child.data[b[i]:b[i + 1]]
        n = min(x.size, y.size)
        diff = np.flatnonzero(x[:n] != y[:n])
        prefix = int(diff[0]) if diff.size else n
        suffix = 0
        if prefix < n:
            tail = n - prefix
            diff = np.flatnonzero(x[::-1][:tail] != y[::-1][:tail])
            suffix = int(diff[0]) if diff.size else tail
        if prefix != x.size or prefix != y.size:
            edits.append([a[i] + prefix, int(x.size - prefix - suffix),
                          y[prefix:y.size - suffix].tobytes().hex()])
    return edits


def compatible(p, c):
    def layout(r):
        return [(t.name, t.data_offset, t.data.shape, t.data.dtype.str) for t in r.tensors]
    if layout(p) != layout(c) or (p.data_offset, p.data.size) != (c.data_offset, c.data.size):
        raise ValueError("requires the same tensor names, order, shapes, types and file layout")
    for k in ("general.architecture", "general.type", "adapter.type", "adapter.lora.alpha"):
        if p.fields[k].contents() != c.fields[k].contents():
            raise ValueError(f"incompatible {k}")
    end = p.data_offset
    for tensor in sorted(p.tensors, key=lambda t: t.data_offset):
        if not np.array_equal(p.data[end:tensor.data_offset], c.data[end:tensor.data_offset]):
            raise ValueError("different inter-tensor padding")
        end = tensor.data_offset + tensor.n_bytes
    if not np.array_equal(p.data[end:], c.data[end:]):
        raise ValueError("different trailing padding")


def ternarize(delta, mode):
    width = min(128, delta.shape[-1]) if mode == "groupfit" else delta.size
    # This lab format stores contiguous groups within a row, without padding.
    if delta.size % width or (mode == "groupfit" and delta.shape[-1] % width):
        raise ValueError("factor width does not divide into whole quantization groups")
    rows = delta.reshape(-1, width)
    mag = np.abs(rows)
    scale = mag.mean(axis=1, keepdims=True)
    if mode in ("fit", "groupfit"):
        for _ in range(8):
            keep = (mag > scale * 0.5)
            scale = np.sum(mag * keep, axis=1, keepdims=True) / keep.sum(axis=1, keepdims=True).clip(1)
            scale = scale.astype(np.float32)
    if mode == "absmean":
        # Match the repository's round-to-even convention at an exact threshold.
        codes = np.rint(np.divide(rows, scale, out=np.zeros_like(rows), where=scale > 0)).clip(-1, 1)
    else:
        codes = np.sign(rows) * (mag > scale * 0.5)
    planes = np.concatenate([np.packbits(codes > 0), np.packbits(codes < 0)])
    return width, scale.astype("<f4").tobytes() + planes.tobytes()


def decode(parent, data, mode, width):
    if mode == "exact":
        return np.bitwise_xor(parent.view(np.uint16), np.frombuffer(data, np.uint16).reshape(parent.shape)).view(parent.dtype)
    n = parent.size
    groups, plane = n // width, (n + 7) // 8
    if len(data) != groups * 4 + 2 * plane:
        raise ValueError("incorrect payload length")
    scales = np.frombuffer(data, "<f4", count=groups)
    bits = np.frombuffer(data, np.uint8, offset=groups * 4)
    plus = np.unpackbits(bits[:plane], count=n).astype(np.int8)
    minus = np.unpackbits(bits[plane:], count=n).astype(np.int8)
    delta = (plus - minus).reshape(-1, width) * scales[:, None]
    return (parent.astype(np.float32) + delta.reshape(parent.shape)).astype(parent.dtype)


@contextmanager
def new_capsule(path):
    with tempfile.TemporaryDirectory(dir=path.parent) as temp:
        staged = Path(temp) / "patch.zip"
        with zipfile.ZipFile(staged, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            yield z
        staged.replace(path)


def encode(parent, child, capsule, mode, hashes):
    if mode not in ("exact", "absmean", "fit", "groupfit"):
        raise ValueError("unknown patch mode")
    p, c = GGUFReader(parent), GGUFReader(child)
    compatible(p, c)
    meta = dict(format=1, mode=mode, **hashes, header_edits=header_edits(p, c), tensors=[])
    error, signal, changed_values = 0., 0., 0
    with new_capsule(capsule) as z:
        for old, new in zip(p.tensors, c.tensors):
            x, y = old.data, new.data
            if x.dtype != np.float16:
                raise ValueError("this experiment supports FP16 adapter factors")
            if np.array_equal(x.view(np.uint16), y.view(np.uint16)):
                continue
            delta = y.astype(np.float32) - x.astype(np.float32)
            if mode == "exact":
                width, payload = 0, np.bitwise_xor(x.view(np.uint16), y.view(np.uint16)).tobytes()
            else:
                width, payload = ternarize(delta, mode)
            restored = decode(x, payload, mode, width)
            error += np.square(y.astype(np.float64) - restored).sum()
            signal += np.square(delta.astype(np.float64)).sum()
            changed_values += np.count_nonzero(delta)
            z.writestr(new.name, payload)
            meta["tensors"].append([new.name, width])
        z.writestr("manifest.json", json.dumps(meta))
    return {"bytes": capsule.stat().st_size, "changed_tensors": len(meta["tensors"]),
            "total_tensors": len(c.tensors), "changed_values": int(changed_values),
            "relative_delta_l2_error": float(np.sqrt(error / signal)) if signal else 0.}


def restore(parent, base, capsule, output):
    if output.resolve() in {p.resolve() for p in (parent, base, capsule)}:
        raise ValueError("output must be a separate file")
    with zipfile.ZipFile(capsule) as z:
        m = json.loads(z.read("manifest.json"))
        if m["format"] != 1 or m["mode"] not in ("exact", "absmean", "fit", "groupfit"):
            raise ValueError("unknown patch format")
        if digest(base) != m["base"]:
            raise ValueError("parent or base fingerprint mismatch")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output.parent) as temp:
            dest = Path(temp) / "rebuilt.gguf"
            shutil.copyfile(parent, dest)
            if digest(dest) != m["parent"]:
                raise ValueError("parent or base fingerprint mismatch")
            # These edits are relative to the original header and preserve its total size.
            with dest.open("r+b") as f:
                size = GGUFReader(dest).data_offset
                header = bytearray(f.read(size))
                for start, removed, replacement in reversed(m["header_edits"]):
                    header[start:start + removed] = bytes.fromhex(replacement)
                if len(header) != size:
                    raise ValueError("incompatible rebuilt header")
                f.seek(0)
                f.write(header)
            r = GGUFReader(dest, "r+")
            tensors = {t.name: t for t in r.tensors}
            for name, width in m["tensors"]:
                x = tensors[name].data
                x[:] = decode(x, z.read(name), m["mode"], width)
            r.data.flush()
            if m["mode"] == "exact" and digest(dest) != m["child"]:
                raise ValueError("incorrect rebuilt child fingerprint")
            dest.replace(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    build, regrow, family = sub.add_parser("build"), sub.add_parser("restore"), sub.add_parser("family")
    for parser in (build, regrow, family):
        parser.add_argument("--parent", type=Path, required=True)
        parser.add_argument("--base", type=Path, required=True)
        parser.add_argument("--out", type=Path, required=True)
    build.add_argument("--child", type=Path, required=True)
    regrow.add_argument("--capsule", type=Path, required=True)
    family.add_argument("--children", type=Path, required=True, nargs="+")
    args = p.parse_args()
    if args.command == "restore":
        restore(args.parent, args.base, args.capsule, args.out)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    if args.command == "family":
        hashes = {k: digest(getattr(args, k)) for k in ("parent", "base")}
        siblings = {}
        for child in args.children:
            capsule = args.out / f"{child.stem}.zip"
            stats = encode(args.parent, child, capsule, "exact", dict(hashes, child=digest(child)))
            with tempfile.TemporaryDirectory(dir=args.out) as temp:
                restore(args.parent, args.base, capsule, Path(temp) / "repaired.gguf")
            stats.update(deflated_full_child_bytes=len(zlib.compress(child.read_bytes(), level=6)),
                         child_bytes=child.stat().st_size, exact_rebuild_verified=True)
            siblings[child.stem] = stats
        (args.out / "family.json").write_text(json.dumps(siblings, indent=2) + "\n")
        return
    hashes = {k: digest(getattr(args, k)) for k in ("parent", "base", "child")}
    report = {"sha256": hashes, "child_bytes": args.child.stat().st_size,
              "deflated_full_child_bytes": len(zlib.compress(args.child.read_bytes(), level=6)), "variants": {}}
    for mode in ("exact", "absmean", "fit", "groupfit"):
        capsule = args.out / f"{mode}.zip"
        stats = encode(args.parent, args.child, capsule, mode, hashes)
        output = args.out / "catalog" / f"{mode}.gguf"
        restore(args.parent, args.base, capsule, output)
        stats["rebuilt_sha256"] = digest(output)
        report["variants"][mode] = stats
        print(mode, stats, flush=True)
    (args.out / "storage.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
