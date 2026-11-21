# A recurring worker function reaches the saved-method bank

One 156-byte `is_prime(n)` function from a G51 worker passed all **10,017 integer inputs from −16 through 10,000** in CPython WASI. An independent Sieve of Eratosthenes supplied the oracle. A copy with an off-by-one divisor bound failed 35 cases, including 4, 9 and 25. [Contract receipt](contract-result.json)

The production saved-method reader loaded the exact function and a small argument guard from an isolated scratch bank. With a structured prime-integer request it answered true for 9,973 and false for 9,801. Seven calls carrying booleans, a float, a string, null or out-of-range integers returned `missing` and released no value. The complete guarded bank source independently passed all 10,017 integer cases and rejected nine malformed or out-of-range arguments. Open-ended language routing and exam scores remain unmeasured. [Saved-method receipt](scratch-bank-result.json)

## What recurred

The original 36 practice archives contain 288 sittings and 611 individually graded workers across G50–G52. All 316 passing workers had a final answered turn with a successful recorded execution and an unambiguous archived source. Those sources contained 165 top-level function definitions. The frozen dependency and syntax filter kept 63 occurrences, representing 42 unique normalized signatures. **Seven** signatures occurred on at least two distinct normalized questions. **Four** occurred under at least two known kind labels. Questions were case-folded and whitespace-normalized. Similar questions with different values can still count separately. [Protocol](protocol.md) · [Occurrence receipts](results.json)

The selected function recurred five times on three distinct questions across four workers. Two occurrences belonged to “a number with given properties” and three to “several tasks in one.” A compound task can contain the same underlying math operation. These worker grades establish provenance for the containing programs. The exhaustive guest check establishes the helper's bounded input/output behavior.

The first selected copy is at line 16 of `practice_10005107/c10005107_02/members/work/member1_2.py`, artifact 14534767525. Its bytes, including the trailing newline, occur verbatim in that worker source. SHA-256 of the extracted file is `5c2b29aebc5d7553f165aca748952f0d802db61208c5805122e124a64e0743a5`. Every occurrence in the results has its own original script hash, member, artifact ID, line, and hashed question identity. The full archive digests are in [the manifest](practice-artifacts.json). The practice ZIPs omit exact kind labels. An exact join to G55 training-row question hashes supplied a unique label for 177 of 285 questions. The remaining questions participate only in the across-question count. [Kind map](kind-map.json)

## Reproduce

Run these commands from the repository root. `ARCHIVES` contains each manifest artifact named `<id>.zip`. `SDK` is the repository's CPython WASI SDK directory containing `python.wasm` and `lib`. The miner uses Python's standard library. The guest requires the existing fieldwork Wasmtime dependency.

```sh
python -m training.experiments.astra_transfer.helpers.mine "$ARCHIVES" --out /tmp/hive-helper-extraction
python -m training.experiments.astra_transfer.helpers.contract "$SDK"
python -m training.experiments.astra_transfer.helpers.scratch_bank "$SDK" --bank /tmp/hive-verified-prime-bank
```

Omit `--bank` for a disposable scratch directory. Supplying a fresh empty directory preserves the verified method for local reuse. The builder calls the existing fieldwork verifier, bank admission and loader, and `team.saved.answer`. It requires the bank path explicitly and leaves the user's configured bank alone. The original short G51 source remains unchanged inside `solve(x)`'s guarded module. The declared contract accepts exactly one integer field named `n`.

After building the bank once, use the saved-method reader directly. This example prints `True`. Changing 17 to 18 returns `False`. The reader withholds a value for 10,001 because the independent check stopped at 10,000.

```sh
HIVE_BANK=/tmp/hive-verified-prime-bank HIVE_FIELDWORK_SDK="$SDK" python - <<'PY'
from team.saved import answer

result = answer('Prime integer check {"n": 17}')
print(result.get("value", result["status"]))
PY
```

To reproduce the optional kind-label join, pass the original `g55-rows.jsonl` to the miner using `--original-labels`. It verifies file SHA-256 `c33f707c7120d279c050748a5752067be708687711aa9acc84a4f434208fadfd`. The saved hashed kind map suffices for the ordinary replay. Extraction and independent guest checking require no hosted inference.
