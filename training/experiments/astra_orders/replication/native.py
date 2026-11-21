"""Run one frozen request per server lease so each case is an independent checkpoint."""
import argparse
import os
from pathlib import Path
from unittest.mock import patch

from team import solo
from training.experiments.astra_orders import generate

HERE = Path(__file__).resolve().parent
CASES_HASH = "0b307fa20ab55c4a4cfdae856be3d3d29485dc1829abffd35aaca08e2c5888ac"
DATE = "2026-11-21 (Saturday)"


def offers(row):
    for arm, n, temp in [("short", 1, 0.), ("short2", 2, .7), ("greedy2", 2, .7), ("short3", 3, .7)]:
        env = {"HIVE_SHORT_ORDERS": "0", "HIVE_FULL_ORDERS": "0", "HIVE_DIVERSE_GREEDY": "1",
               "HIVE_DIVERSE_ORDERS": "1" if arm == "greedy2" else "0"}
        with patch.dict(os.environ, env), patch.object(solo, "familiar", return_value=row["familiar"]), \
             patch.object(solo.time, "strftime", return_value=DATE):
            system, temperature = solo.member_settings(row["task"], n, "t80+g55trunk", (), temp)
        sampling = {"temperature":temperature, "top_k":20, "top_p":.8, "seed":8104 if arm == "short3" else 8103} if temperature else {}
        yield row["id"], arm, [{"role":"system", "content":system}, {"role":"user", "content":row["user"]}], sampling


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("runtime", "model", "lora", "out", "log"):
        p.add_argument("--" + flag, type=Path, required=True)
    p.add_argument("--case", required=True)
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    def selected(rows):
        row, = [r for r in rows if r["id"] == args.case]
        yield from offers(row)
    generate.run(args, selected, HERE / "cases.json", CASES_HASH)
