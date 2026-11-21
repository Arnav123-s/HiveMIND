"""Collect unseen cells of the frozen prompt by sampling table on the original G55 body."""
import argparse
import json
from pathlib import Path
from team import solo
from training.experiments.astra_orders import generate

HERE = Path(__file__).resolve().parent
DATE = "2026-11-21 (Saturday)"


def offers(data):
    panel = {r["id"]:r["task"] for r in json.loads((generate.HERE / "panel.json").read_text())}
    for row in data["rows"]:
        modes = ["short2", "short3"]
        if row["gate"] == "full":
            modes += ["modular0", "modular2"]
        for mode in modes:
            system = solo.modular_orders(panel[row["id"]], DATE) if mode.startswith("modular") else data["orders"]["short"]
            messages = [{"role":"system", "content":system},{"role":"user", "content":row["user"]}]
            settings = {} if mode == "modular0" else {
                "temperature": 0.7, "top_k":20, "top_p":0.8, "seed":8104 if mode == "short3" else 8103}
            yield row["id"], mode, messages, settings


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    for argument in ("runtime","model","lora","out","log"):
        p.add_argument("--"+argument,type=Path,required=True)
    generate.run(p.parse_args(),offers)
