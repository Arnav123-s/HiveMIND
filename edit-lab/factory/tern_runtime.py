"""Ternary serving runtime (assembly 2026-11-10): the adapter that
lets factory.serve serve the BitNet scale-arm singles.

The scale-arm models (bitnet-hive/scale-arm/members/*.npz) are
CTern models: born-ternary weights served through the CORRECTED
BitNet b1.58 forward (per-matrix absmean ternary codes, RMSNorm +
per-token int8 activation quantization at serve time — see
bitnet-hive/scale-arm/corrected_tern.py). That forward is NOT the
TinyNet forward, so these artifacts cannot be dequantized into
TinyNet records without changing what they compute. They serve
through their own runtime, behind the same Specialist-shaped
interface the serving path already uses:

    run({"text": ...}) -> {"ok": True, "output": <class>,
                           "specialist": <record name>,
                           "evidence": ...}

The registry record for such an artifact is a JSON file in
coding/swarm/models/ (the version file the registry builder
scans) carrying a "payload" pointer: {path, sha256, runtime}.
The audit hashes BOTH the record and the payload, so an npz that
drifts from its adoption record fails the serve-time audit
exactly like a TinyNet record would.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

LAB_ROOT = Path(__file__).parent.parent
_SCALE_ARM = LAB_ROOT / "bitnet-hive" / "scale-arm"
for _p in (str(LAB_ROOT / "coding"), str(LAB_ROOT),
           str(_SCALE_ARM), str(_SCALE_ARM.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import corrected_tern as CT  # noqa: E402


class TernSpecialist:
    """A CTern model behind the TinyNet run() interface. The
    display name comes from the registry record, not the npz
    header (the npz was bred as '<job>-scale-single'; the adopted
    artifact is '<job>-vN')."""

    kind = "ternary-bitnet"

    def __init__(self, record: Dict[str, Any], lab_root: Path = LAB_ROOT):
        payload = record["payload"]
        self.name = record["name"]
        self.niche = record.get("niche", "")
        self.job = record.get("job", "")
        self.substrate = "ternary"
        self.payload_path = payload["path"]
        self.model = CT.load_cnpz(Path(lab_root) / payload["path"])
        self.classes = self.model.classes
        self.features = self.model.features
        self.hidden = self.model.hidden
        self.fmode = self.model.fmode

    def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        text = task.get("text", "") if isinstance(task, dict) \
            else str(task)
        import tern as TN
        X = TN.featurize_matrix([text], self.features, self.fmode)
        if not X.any():
            return {"ok": False, "output": "unknown",
                    "specialist": self.name,
                    "evidence": "no known feature fired",
                    "gap": "no-features"}
        scores = self.model.scores_X(X)[0]
        best = self.classes[int(scores.argmax())]
        top = sorted((float(s) for s in scores), reverse=True)
        margin = top[0] - (top[1] if len(top) > 1 else 0.0)
        return {"ok": True, "output": best, "specialist": self.name,
                "evidence": f"ternary margin {margin:.2f} "
                            f"(corrected BitNet forward)"}

    def acc_on(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.model.acc_on(examples)


def load_tern(record: Dict[str, Any],
              lab_root: Path = LAB_ROOT) -> TernSpecialist:
    return TernSpecialist(record, lab_root)
