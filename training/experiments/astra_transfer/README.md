# Do checked file-handling patterns help a new request?

Five hand-written I/O reminders matched operations in checked, teacher-authored G51 lesson programs. On ten fresh requests, the selector identified the exact operations on **8/10**, compared with **5/10** for HiveMIND's existing output-filename resolver. This measures role recognition. In the separate native G55 worker trial, the assisted and unassisted worker each solved **4/6**. The hints changed two answers and recovered zero complete tasks.

## Earlier evidence

The input file contained 6,757 training rows. This study uses the `who=lesson` teacher programs. The companion study extracted the hive workers' own reused code. Its independently checked `is_prime` implementation passed all 10,017 integers from −16 through 10,000 and ran via the existing saved-method API. [Worker-authored helpers](helpers/README.md) We selected first-turn lessons whose generator requires a passing program, excluded 56 held-back task texts, and required three distinct source tasks per operation. Membership in the archive establishes training eligibility. Actual optimizer exposure is unknown. The builder parses the old Python source and records the three lowest matching row hashes as reproducible witnesses. The hint text is hand-authored. The archive determines which hints qualify. Each of the three JSON-lines, CSV-output and module-output witnesses came from a single teacher generator for that operation. Different task texts can share the same underlying method.

| Operation | Distinct supporting task texts |
| --- | ---: |
| Read CSV by header | 125 |
| Decode JSON lines | 11 |
| Write CSV header and data rows | 10 |
| Write JSON | 126 |
| Write and test a Python module | 26 |

The five reminders contain no archived filenames, answers, quantities or field names. All 31 combinations cost 41–147 t80 tokens, including the separator. The text is omitted for any of the 277 supporting source prompts, an explicitly protected request or a recognized negated file instruction. The source-prompt comparison normalizes case and whitespace. It cannot detect every paraphrase.

## Independent role test

Another agent wrote and hashed ten requests and their expected operations before seeing the selector. The selector and protocol were frozen before the independent panel was opened. The requests cover inputs, output files, negation and unsupported actions.

| Selection method | Exact sets | Correct offers | Incorrect offers | Missed operations |
| --- | ---: | ---: | ---: | ---: |
| No hints | 2/10 | 0 | 0 | 11 |
| Existing output-filename resolver | 5/10 | 5 | 0 | 6 |
| Frozen input and output selector | 8/10 | 9 | 0 | 2 |

A ban on exporting a file also suppressed a permitted CSV read. A JSONL file described as “uploaded lines” missed the input cue. Both failures remain in the receipts. All five hand-authored cards qualified on G51, so always enabling this same set of cards produces the same role coverage on these ten fresh prompts. The role test provides no evidence that example retrieval improves on the fixed set.

## Paired native answers and files

One real G55 trunk produced greedy first programs with the usual short worker instructions. The independent grader extracted the first program, ran it in a fresh CPython WASI directory with the original Python hooks and checked stdout and requested file content. Four identical inputs reused the stock prediction. Both arms passed 3/3 familiar tasks and 1/3 unfamiliar ones. This six-request panel measures first attempts only.

| Across all six requests | Short worker | Short worker + I/O hints |
| --- | ---: | ---: |
| Complete tasks | 4 | 4 |
| Named JSON files actually created on the two hinted jobs | 1/2 | 2/2 |
| Hinted jobs passing the whole contract | 0/2 | 0/2 |
| Prompt tokens | 967 | 1,057 |
| Generated tokens | 486 | 547 |
| Wall seconds | 159.248 | 175.941 |
| Server CPU seconds | 312.19 | 343.45 |

The warehouse task required an array of lot codes. The stock program printed the right count and omitted the file. With a hint, the worker saved a JSON file containing records with extra fields. The counter task required wrapping modulo 32. The hinted program added 31 on a wrap, producing 36 where the required sum was 38. Even though the hints elicited one missing file, neither changed response passed its contract. This path remains experimental.

A post-audit control replayed all 14 sealed programs with the normal worker Python environment after an unused `requests` import failed under WASI. It reproduced every short and scaffold task verdict, including the two failures. Full worker instructions went from 3/6 in WASI to 4/6 in the normal environment. The full worker solved the counter and missed the booking schedule, while the short worker did the reverse. No prompts or generations changed.

`native_summary.json` contains the per-request grades, file and generation hashes, token counts and timings. The companion study publishes the frozen native replies, independent grader and normal Python replay. The role test and selector run on their own. [Native programs and paired grades](https://github.com/Arnav123-s/HiveMIND/tree/c488da6/training/experiments/astra_orders)

## Reproduce

The earlier training artifact contains `rows.jsonl`. Its ZIP SHA-256 is `2798a3df6ff7eb8852aa1e8e7e82b872287c8e46a307ed9d83e6144072339605`. [G51 training rows](https://github.com/Arnav123-s/HiveMIND/actions/runs/44525337919/artifacts/14535816261)

Run from the repository root with the `tokenizer.json` from `prism-ml/Ternary-Bonsai-8B-unpacked` at revision `ac20f03fc62e872399218b659c8e949dfca05769`. Both input file digests are recorded in `bank.json`. Rebuilding selects witnesses deterministically. The original source code need not be executed.

```bash
python -m training.experiments.astra_transfer.build G51_ROWS.jsonl T80_TOKENIZER.json --out /tmp/g51-bank.json
cmp /tmp/g51-bank.json training/experiments/astra_transfer/bank.json
python -m training.experiments.astra_transfer.grade_roles
```

For one request, `scaffolds.render(request)` returns the complete suffix, including its separator, or the empty string. `render(request, protected=True)` leaves the task unassisted. The study has no production switch.
