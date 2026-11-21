# Keep a checked worker function

A practice worker can earn a reusable tool when its standalone function passes an independently maintained contract. The contract declares the inputs and their expected results. The admission command runs the extracted function on **every input** in the existing CPython WebAssembly guest. The saved tool checks those same input limits each time someone calls it.

## Use it

Set `HIVE_FIELDWORK_SDK` to the CPython WASI installation and choose a bank directory. These commands generate three reference contracts and submit a real G51 worker's digit-sum function. The normal chat command can answer the example on a machine with the WASI runtime even when no language model is installed. [Runtime setup](../../../reports/rule_lab/fieldwork/reproduce.md)

```sh
export HIVE_FIELDWORK_SDK="$PWD/runs/fieldwork-assets/wasi"
export HIVE_BANK="$PWD/runs/worker-bank"
export HIVE_BANK_CONTRACTS="$PWD/runs/worker-contracts"
python -m training.experiments.astra_transfer.bank_admission.replay --write-contracts "$HIVE_BANK_CONTRACTS"
./hive bank-admit training/experiments/astra_transfer/bank_admission/workers/digits.py "$HIVE_BANK_CONTRACTS/digit_sum.json"
./hive --once 'Calculate the decimal digit sum of 907.'
```

The result is **16**. In an interactive local session the same shortcut works on each self-contained calculation. Requests that use earlier turns, ask for a file, or combine additional work continue through the conversation. `--local` selects this machine even when a service is available. Explicit `HIVE_ROLES=1` uses the role swarm. Supply a JSON object for multiple arguments. For example, after the base-conversion worker earns admission, ask `Calculate the lowercase base notation conversion for {"n":255,"b":16}`.

With both directories configured, the regular practice runner automatically checks named functions found in an individually passing member's last successful program. The practice result's `bank_admissions` records what happened. Fixed exam runs do not submit candidates. Other worker wins can qualify once a trusted contract names the function and its supported inputs.

## Carry practice methods into another session

Download the numbered practice artifacts from a generation into one directory, preserving paths such as `practice/rows-1/rows.jsonl`. Use artifacts from a revision that records each worker’s individual verification. Choose trusted contracts independently of the workers and any evaluation set. Build the first snapshot and query it offline with the usual command:

```sh
./hive bank-promote --practice practice --contracts "$HIVE_BANK_CONTRACTS" --output runs/bank-v1.json
HIVE_BANK="$PWD/runs/bank-v1.json" ./hive --local --once 'Calculate the decimal digit sum of 907.'
```

For the next generation, add `--previous runs/bank-v1.json` and choose a new output name. Promotion rechecks every retained version against its original contract and runs every new candidate through the same guest. It refuses to overwrite a different snapshot. A whole-snapshot hash detects damaged or missing entries. Use snapshots from a checkout or source you trust. Chat withholds conflicting results and sends follow-ups or previous open-ended instructions through the conversation.

A repository owner can enable hosted promotion by setting the Actions variable `HIVE_BANK_CONTRACTS_DIR` to a committed directory of independent JSON contracts. An ordinary generation can then publish `cells/method_bank.json` with its body record. The issue chat tests a matching request before fetching model weights. Trial runs and comparison runs skip promotion. Clearing the variable disables both hosted steps. A local checkout can use its published snapshot with `HIVE_USE_METHOD_BANK=1` and the WASI runtime installed. Explicit `HIVE_BANK` still selects a particular local snapshot or a legacy directory.

## Define a contract

```json
{"task":"double_integer","description":"Double the supplied integer.","function":"double","arguments":[{"name":"n","min":-1,"max":2}],"outputs":[-2,0,2,4]}
```

Each argument is either an inclusive integer interval or a list of explicit JSON values, such as `{"name":"unit","values":["m","cm"]}`. Supply one expected output for every combination, with the last argument changing fastest. The maximum is 65,536 complete inputs. Integers, fractions, booleans and strings are compared by their JSON representations. The verifier accepts standalone functions using the worker miner's supported Python syntax. It checks results in batches and publishes only after every comparison succeeds.

Keep contracts in a trusted directory separate from worker output. The person or system providing a contract is responsible for its meaning and expected values. Admission checks behavior on its declared domain. It does not discover requirements or establish behavior outside that domain. The published module contains the function and guard, with the expected-output table kept out of the bank.

A new implementation or domain creates its own immutable version. Chat uses the versions covering the request and withholds an answer if their outputs conflict. Re-admitting the same method and contract reuses the record.

## Reproduce the archived-worker check

```sh
python -m training.experiments.astra_transfer.bank_admission.replay --sdk "$HIVE_FIELDWORK_SDK"
```

The replay reconstructs member receipts from four source files and their individual passing verdicts in the G50–51 practice artifacts. It checks each original script's SHA-256, exercises the same practice admission function as training, and queries the normal saved-method reader. The original ZIPs omit the standalone member receipt files. The worker linkage comes from seat number, graded verdict and the final successful program event. [Source manifest](workers.json)

| Function | Independent expected results | Verified inputs | Example |
|---|---|---:|---|
| Prime test | Sieve of Eratosthenes | 10,017 integers from −16 to 10,000 | 9,973 is prime |
| Decimal digit sum | Arithmetic by decimal place | 1,000 integers from 0 to 999 | 907 gives 16 |
| Base conversion | Binary, octal and hexadecimal formatting, with binary pairs for base four | 1,024 combinations of 0–255 and bases 2, 4, 8, 16 | 255 in base 16 gives ff |

All three methods passed and answered the example requests. Chat withheld six requests with unsupported values or types. Direct execution of the stored modules in WASI rejected the same six inputs. A fourth script had individually passed its original practice task but returned an empty string when converting zero. The independent contract rejected it at the first input. Two workers contributed identical prime code, which occupied one bank entry. The replay measures transfer into the bank and subsequent delivery, without measuring generation retention or unseen-task accuracy. [Execution receipt](result.json)
