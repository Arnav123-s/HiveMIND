"""Render the historical forecast figure from measured, sealed field-work results."""

import argparse
import datetime
import json
from pathlib import Path


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exam", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    def outcomes(label):
        return [
            r["detail"]
            for r in json.loads((args.exam / ("climate-" + label + ".json")).read_text())["tests"]
        ]

    fixed, selected = outcomes("fixed"), outcomes("growth")
    fig, ax = plt.subplots(
        1, 2, figsize=(11, 4.4), layout="constrained", gridspec_kw={"width_ratios": [1.16, 1]}
    )
    last = fixed[-1]
    origin = last["origin"]
    dates = [datetime.date(origin + 1 + i // 12, i % 12 + 1, 15) for i in range(24)]
    ax[0].plot(
        dates,
        last["observations"],
        color="#20262b",
        linewidth=2.5,
        marker="o",
        markersize=3.2,
        label="Observed",
    )
    ax[0].plot(dates, last["predictions"], color="#006f84", linewidth=2, label="Fixed 10-year model")
    ax[0].plot(
        dates,
        selected[-1]["predictions"],
        color="#ba6330",
        linewidth=2,
        linestyle="--",
        label="Selected model",
    )
    ax[0].xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax[0].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax[0].set(title="Two years forecast from December 2023", ylabel="Monthly atmospheric CO₂ (ppm)")
    ax[0].legend(frameon=False, fontsize=8, loc="upper left")
    origins = np.array([r["origin"] for r in fixed])
    pos = np.arange(len(origins))
    for shift, key, series, color, label in (
        (-0.27, "naive_rmse", fixed, "#b7bbbe", "Seasonal repeat"),
        (-0.09, "drift_rmse", fixed, "#686778", "Five-year drift"),
        (0.09, "rmse", fixed, "#006f84", "Fixed model"),
        (0.27, "rmse", selected, "#ba6330", "Selected model"),
    ):
        ax[1].bar(pos + shift, [r[key] for r in series], width=0.17, color=color, label=label)
    ax[1].set(
        title="Error across five forecast origins",
        ylabel="24-month RMSE (ppm)",
        xlabel="Final year available at forecast time",
        xticks=pos,
        xticklabels=origins,
    )
    ax[1].legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", color="#dddddd", linewidth=0.6)
        a.set_axisbelow(True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
