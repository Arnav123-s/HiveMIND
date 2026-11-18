"""Re-test frozen scientific submissions with NumPy available, selecting variants only on public observations."""

import argparse
from pathlib import Path

from .campaign import fingerprint, read, save
from .grade import compact, grade
from .numeric_guest import NumericGuest
from .repair import improve


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args()
    root = args.root
    guest = NumericGuest()
    for name in ("climate", "thermal"):
        for model in ("g41", "recruit", "4b", "q35"):
            for mode in ("first", "cold", "grown"):
                parent = (root / (model + "-cold") if mode == "first" else root / model / mode) / (
                    name + ".json"
                )
                if not parent.exists():
                    continue
                data = read(parent)
                code = data["source" if mode == "first" else "program"]
                dest = root / "numeric-trial" / name / (model + "-" + mode + ".json")
                if (
                    dest.exists()
                    and read(dest)["parent"] == fingerprint(code)
                    and read(dest).get("version") == 2
                ):
                    continue
                pub = grade(guest, name, code, "public")
                repaired = improve(guest, name, code, mutations=0) if not pub["complete"] else None
                selected = repaired["program"] if repaired else code
                trial = dict(
                    version=2,
                    parent=fingerprint(code),
                    source=selected,
                    digest=fingerprint(selected),
                    public_raw=compact(pub),
                    public=repaired["public"] if repaired else compact(pub),
                    interface_edits=repaired["history"] if repaired else [],
                )
                for split in ("exam", "confirmation"):
                    trial[split] = grade(guest, name, selected, split)
                    if selected != code:
                        trial[split + "_raw"] = grade(guest, name, code, split)
                save(dest, trial)
                print(
                    name,
                    model,
                    mode,
                    trial["exam"]["correct"],
                    trial["confirmation"]["correct"],
                    flush=True,
                )


if __name__ == "__main__":
    main()
