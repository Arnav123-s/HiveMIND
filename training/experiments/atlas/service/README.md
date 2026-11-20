# Ask a checked question locally

From the repository root, ask for a weekday, a date difference, a greatest common divisor, a temperature conversion, a percentage price change or a depot shipping quote.

```sh
python -m training.experiments.atlas.service.ask 'Which day of the week is 2024-02-29?'
# Thursday
python -m training.experiments.atlas.service.ask 'A bicycle costs 180 dollars and the price falls by 15%. What is the new price?'
# 153.00 dollars
python -m training.experiments.atlas.service.ask --sdk /path/to/wasi 'Calculate the depot shipping fee for 0.2 kg and 0.9 kg using per-parcel rounding'
# 520 cents
```

The arithmetic route checks the whole question, calculates an exact value, and verifies the displayed answer against the certificate. Dates can be ISO or written as day, month name and year. The days contract measures elapsed calendar days. The conversion contract takes an explicit Celsius or Fahrenheit input and the instruction “One decimal place.” The price contract requires an exact result in cents. [Certificate implementation](../pulse/one_checked/current.py)

Shipping uses the example depot's checked rule: a 250-cent dispatch charge plus 90 cents per started 500 grams, with each parcel rounded separately in the bundled bank. State the rounding convention if the bank contains more than one. The guarded input route supports whole grams and a narrowly phrased kilogram quote; it requires positive masses at whole-gram precision. A conflicting or unsupported request returns no numeric value. The example is a local depot tariff, so the result is only a quote under that tariff. [Example bank](../../../reports/retained-skills/shipping/bank) · [Shipping trace](../traces/README.md)

Use the repository Python environment. The ordinary arithmetic path uses the existing repository dependencies and needs no model download. For shipping, install the CPython WASI SDK with `python scripts/setup_fieldwork.py`, or point `--sdk` / `HIVE_FIELDWORK_SDK` at an existing installation. The CLI selects the bundled read-only example bank by default. `--bank PATH` or `HIVE_BANK` chooses a different checked bank; `--bank off` disables shipping. Shipping runs with one CPU and WASI fuel limits. By default the guarded route writes diagnostic data only to a temporary directory. If you already have a separately qualified kilogram branch, `--trace-bank DIRECTORY` reuses that branch and its ledger after verifying compatibility with the current parent.

Add `--json` for status, typed value, unit, route and proof. Exit 0 indicates an answer; exit 1 covers unsupported, ambiguous or unavailable requests. Decimal values are plain strings in JSON to retain precision. Weekdays use lower-case strings. Shipping fees are integer cents. The command is deliberately separate from the general chat and never falls through to a model. [CLI](ask.py)

```sh
python -m pytest -q training/experiments/atlas/service/test_service.py
python training/experiments/atlas/service/demo.py --sdk /path/to/wasi --out /tmp/hive-checked-service-demo.json
```

## Measured terminal use

With the original certificate at commit `ccd34f5`, four separately launched processes verified the Thursday, 153-dollar and 520-cent examples and withheld a request to promise a delivery time. The 520-cent answer ran the saved depot program in WASI, consumed 2,045,368,958 fuel units and checked the requested per-parcel convention. The model ran zero times. On this machine, cold process CPU was 4.53 seconds for the weekday, 4.59 for the price, 22.42 for the shipping quote and 4.18 for the unsupported request. These figures include Python imports and, for shipping, WASI initialization. [Exact inputs, outputs, method digest and timings](demo-results.json)

An independent 18-question mixed panel compared this initial service to ordinary local HiveMIND. The service answered 10 of 12 eligible questions correctly; stock answered one. Both withheld all six out-of-scope questions and produced zero wrong answers. The service missed two paraphrases. These were fresh one-CPU processes with no model. The initial service used 120.03 total CPU seconds versus 12.20 for stock across those 18 invocations, so the coverage gain also had a cost. [Independent inputs, timings, scoring and outputs](judge/results.json)

The updated CLI loads a standard-library calculator. On identical weekday, price and GCD questions, all **18 matched invocations** (two implementations × three questions × three rotated repetitions) returned the same answers. Median fresh-process wall time fell from **4.870 s to 0.073 s** and median CPU from **4.805 s to 0.070 s** on the same pinned CPU. The machine's file cache was warm. This measures arithmetic startup; shipping still runs its WASI program. All 18 earlier independent inputs retained the same arithmetic eligibility and values under the updated evaluator. [Matched commands, exact source hashes and per-run timings](cold-start.json)
