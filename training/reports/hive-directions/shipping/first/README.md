# Comparing three routes into a saved shipping method

Each arm receives the same message after the outer chat router has chosen work. The baseline calls the checkout's `team.saved.answer` with its registered shipping bank. The candidate's `extract_shipping` either supplies weights to the same bank or declines. The final arm always declines. The actual saved source runs inside the repository's CPython WebAssembly guest. No language model or ordinary worker team participates.

Each positive case requires the entire weight list in the stated order, including multiplicity, plus the integer fee. An independent calculation of the expected fee is checked against the archived program on every positive input. A price collision is recorded explicitly when incorrect arguments happen to give the right price. An actual solver invocation on a negative case is a false call, including an invocation that fails to produce an answer. The raw rows distinguish calling from releasing. This is a constructed routing study; the protocol and original labels are included alongside the runner.

## First result

| Arm | Correct calls on 14 valid requests | Wrong arguments | Valid requests missed | False calls on 14 other requests | Correct declines | Correct decisions |
|---|---:|---:|---:|---:|---:|---:|
| Main saved router | 7 | 5 | 2 | 10 | 4 | 11/28 |
| Frozen typed adapter | 0 | 0 | 14 | 0 | 14 | 14/28 |
| Always decline | 0 | 0 | 14 | 0 | 14 | 14/28 |

The baseline's seven exact calls produced the expected integer fee. All five wrong argument lists on valid cases also produced a different fee. Its ten false calls all returned a number. The candidate matched the always-decline control on every case. Its higher decision count over the baseline came entirely from withholding results. It completed no jobs on this panel.

The protocol treats the published per-parcel tariff as the subject of ordinary valid requests for it. The candidate also requires a recognized explicit statement of the rounding convention. Only one of fourteen valid messages matched that condition, and the candidate declined that message too. This diagnostic was counted after the outcome. A setting with several equally applicable tariffs would require separate testing.

## Scope and reproducibility

The 28 messages and their expected arguments were authored independently of the router code and earlier probes. Fourteen are positives and fourteen require other handling. Construction included boundary weights, changes, omissions and other goals. This balance is a test design, not a production traffic estimate. The candidate was developed separately and frozen before this evaluator ran the panel. The code was compared without fitting to the labels or choosing an operating point on the panel.

The checkout used was main `1414d49243987ea58c5913af251c39e104d77b68`. Both executable arms received the same message at the same downstream boundary. The frozen bank contains one retained per-parcel program. No model, full-chat routing, alternate tariff, or generic worker output was scored. The observed environment used CPython 3.12.14 and wasmtime 36.0.0. `hashes.json` records the study artifacts.

Use the project's Python environment with its Fieldwork dependencies, the indicated HiveMIND revision, and a CPython WASI SDK containing `python.wasm` and the associated standard library. SDK setup is described in `training/reports/rule_lab/fieldwork/reproduce.md` in the checkout. Run the following from this directory.

```bash
python compare.py --checkout /path/to/HiveMIND --sdk /path/to/wasi --out replay.json
diff -u observed.json replay.json
```

The default adapter and cases paths are relative to the runner. The output includes hashes of the label set, adapter, shipping program, saved router, runner and WASI interpreter.
