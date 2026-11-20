"""Draw the preregistered prompt stream. Keep maker names and grading seeds out of the inference input."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4]))
from training import exam, kinds


def digest(data):
    return sha256(data).hexdigest()


def serialize(obj):
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def draw(folder):
    settings = json.loads((HERE / "settings.json").read_bytes())
    historical = json.loads((HERE.parent / "ledger.json").read_bytes())
    taken = set(historical["prompt_sha256"].values())
    assert len(taken) == 30
    selected, seeds, excluded, unavailable = [], {}, [], []
    for maker in sorted(kinds.HELD_OUT):
        for index in range(64):
            seed = f"verified-growth-native:{settings['nonce']}:{maker}:{index}"
            _, _, message, _ = exam._made(kinds.get(maker).make, seed)
            key = digest(message.strip().encode())
            if key in taken:
                excluded.append({"maker": maker, "index": index, "prompt_sha256": key})
                continue
            taken.add(key)
            ident = digest((settings["nonce"] + key).encode())[:16]
            selected.append({"id": ident, "task": message})
            seeds[ident] = {"maker": maker, "index": index, "seed": seed, "prompt_sha256": key}
            break
        else:
            unavailable.append(maker)
    selected.sort(key=lambda row: row["id"])
    assert len(selected) + len(unavailable) == len(kinds.HELD_OUT) == 10
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "requests.json").write_text(serialize(selected))
    manifest = {"settings_sha256": digest((HERE / "settings.json").read_bytes()),
                "requests_sha256": digest((folder / "requests.json").read_bytes()),
                "excluded": excluded, "selected": seeds, "unavailable": unavailable}
    (folder / "draw-manifest.json").write_text(serialize(manifest))
    print(len(selected), "selected,", len(excluded), "exact duplicates skipped, unavailable", len(unavailable))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", required=True, type=Path)
    draw(p.parse_args().out_dir)
