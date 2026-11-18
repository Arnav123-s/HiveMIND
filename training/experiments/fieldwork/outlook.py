"""Score the first nine 2026 monthly CO₂ measurements and freeze a calendar-2027 forecast."""

import argparse
import csv
import hashlib
from pathlib import Path

from .campaign import save
from .discovery import atmosphere
from .grade import rmse


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--snapshot", type=Path, required=True, help="NOAA monthly Mauna Loa CSV created on October 9, 2026"
    )
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    raw = args.snapshot.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != "d895fb5b4a59fb5e4cd98e69b7667fe5bef595c6581f630852b12cb41c07f675":
        raise ValueError("use the October 9, 2026 NOAA snapshot for this frozen forecast")
    months = [
        [int(r["year"]), int(r["month"]), float(r["average"])]
        for r in csv.DictReader(line for line in raw.decode().splitlines() if not line.startswith("#"))
        if float(r["average"]) > 0
    ]
    year = [r for r in months if r[0] == 2026]
    past = [r for r in months if r[0] < 2026][-240:]
    future = [[2027, m] for m in range(1, 13)]
    observed = [r[2] for r in year]
    study = dict(
        source_sha256=digest,
        training_cutoff=months[-1][:2],
        historical=dict(months=[r[:2] for r in year], observed=observed),
        future_months=future,
        release="2026-11-18",
        models={},
    )
    for name, choose in (("fixed", False), ("adaptive", True)):
        check = atmosphere(dict(history=past, future=[r[:2] for r in year]), choose)
        pred = atmosphere(dict(history=months[-240:], future=future), choose)
        study["models"][name] = dict(
            historical_forecast=check["forecast"],
            historical_rmse_ppm=rmse(check["forecast"], observed),
            forecast=pred,
        )
    args.out.mkdir(parents=True, exist_ok=True)
    save(args.out / "co2-forecast-record.json", study)
    with (args.out / "co2-2027.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(("year", "month", "fixed_ppm", "adaptive_ppm"))
        for i, (year, month) in enumerate(future):
            writer.writerow(
                [
                    year,
                    month,
                    *[
                        f"{study['models'][name]['forecast']['forecast'][i]:.3f}"
                        for name in ("fixed", "adaptive")
                    ],
                ]
            )
    print({k: v["historical_rmse_ppm"] for k, v in study["models"].items()})


if __name__ == "__main__":
    main()
