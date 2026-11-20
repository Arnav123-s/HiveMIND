"""Read tokenizer metadata without loading a tensor or importing a model library."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


FORMATS = ("B", "b", "H", "h", "I", "i", "f", "?", None, None, "Q", "q", "d")
FIELDS = {
    "general.architecture", "general.name", "tokenizer.ggml.pre", "tokenizer.ggml.model",
    "tokenizer.ggml.tokens", "tokenizer.ggml.eos_token_id", "tokenizer.ggml.bos_token_id",
    "tokenizer.ggml.padding_token_id", "tokenizer.ggml.add_bos_token", "tokenizer.ggml.add_eos_token",
}


def inspect(f):
    def number(fmt):
        native = "<" + fmt
        return struct.unpack(native, f.read(struct.calcsize(native)))[0]

    def string():
        return f.read(number("Q"))

    if f.read(4) != b"GGUF":
        raise ValueError("expected a GGUF file")
    result = {"GGUF_version": number("I"), "tensor_count": number("Q")}
    for _ in range(number("Q")):
        key, kind = string().decode(), number("I")
        keep = key in FIELDS or key.endswith(".block_count")
        if kind == 8:
            raw = string()
            if keep:
                result[key] = raw.decode()
        elif kind == 9:
            subtype, count = number("I"), number("Q")
            if key == "tokenizer.ggml.tokens" and subtype == 8:
                digest = hashlib.sha256()
                for _ in range(count):
                    raw = string()
                    digest.update(len(raw).to_bytes(8, "little"))
                    digest.update(raw)
                result[key] = {"count": count, "length_prefixed_sha256": digest.hexdigest()}
            elif subtype == 8:
                for _ in range(count):
                    string()
            else:
                f.seek(count * struct.calcsize("<" + FORMATS[subtype]), 1)
        else:
            value = number(FORMATS[kind])
            if keep:
                result[key] = value
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("weights", type=Path, nargs="+")
    for path in parser.parse_args().weights:
        with path.open("rb") as handle:
            print(json.dumps(inspect(handle), indent=2))
