"""Rebuild what git does not carry: the shared base in llama.cpp format and every registered cell's delta.

    python training/cells_build.py
The base (SmolLM2-135M-Instruct, Apache-2.0) is downloaded from Hugging Face and written at 8 bits
(cells/gguf/smol135.gguf, ~145 MB); each cell's weight delta is converted from cells/adapters/<skill>/.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime  # noqa: E402
from training.cells_promote import hf_dir, to_gguf  # noqa: E402

CONVERT = ROOT / "training" / "llama_cpp_convert"


def base_gguf(base="smol135"):
    out = runtime.GGUF / f"{base}.gguf"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=f"{CONVERT}/gguf-py:{CONVERT}")
    subprocess.run([sys.executable, str(CONVERT / "convert_hf_to_gguf.py"), hf_dir(base), "--outfile", str(out),
                    "--outtype", "q8_0"], check=True, env=env, capture_output=True)
    return out


if __name__ == "__main__":
    reg = runtime.registry()
    for base in sorted({c["base"] for c in reg.values()}):
        from training.cells import BASES
        if Path(BASES[base]).exists():  # a base made here (not downloaded): training/cells_cut.py builds it
            print(f"base {base}: built by training/cells_cut.py")
            continue
        print(f"base {base}: {base_gguf(base)}")
    for skill, c in reg.items():
        dst = runtime.GGUF / f"{skill}.gguf"
        if not dst.exists():
            to_gguf(ROOT / "cells" / "adapters" / skill, skill, c["base"])
        print(f"cell {skill}: {dst} ({dst.stat().st_size / 1e6:.1f} MB)")
