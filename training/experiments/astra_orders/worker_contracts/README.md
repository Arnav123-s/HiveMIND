# Inspecting inputs and checking a worker's files

A worker can use fresh HTTP responses across its own Python turns, check an explicitly requested Python example in WASI, and repair the actual file before agreement. All three controls are opt-in.

| Control | When it acts |
|---|---|
| `HIVE_ASSERT_FIRST=1` | Adds a short inspection and assertion instruction to an unfamiliar first prompt. Checks explicit acceptance examples on a single requested Python module before a candidate can witness agreement. |
| `HIVE_PAGE_CHECKS=1` | Records up to 2,048 successful Requests GET addresses per turn on the run board. An explicitly required list of URLs can produce a missing-address repair when the worker uses observable, literal GETs. |
| `HIVE_HTTP_CACHE=1` | Reuses identical fresh public GET representations in a private store that lives for one member. Enables the same address diagnostics. |
| `HIVE_FAMILIAR_TASKS` | Optional path to a checked request-text index. The index and recently checked solves supply the wording comparison. Without an index, the worker consults its recent checked solves. |

Public module checks need an installed fieldwork WASI SDK. Supported prompts have one requested Python file and a Python fence headed by “Acceptance tests:”, “Required checks:” or “Examples to pass:”. Its contents must be literal `assert function(arguments) == expected` statements. A narrow pure-Python subset is eligible. Code that depends on outside files, libraries or the operating system gets no verdict. A contradiction is evidence for repair. The usual independent delivery checks still apply.

An explicit page list begins with “Using requests, fetch each of these URLs:” followed by one URL per line. Cursors, sessions, generated addresses and other unobservable request paths can all change what one address represents. The count shown on the board is diagnostic. Historical repeated-address errors keep their existing behavior when both HTTP flags are off.

## Measurements

* Two worker turns traversed five cursor pages at one address. Both produced the same four author totals. With the cache off, the origin received 5 + 5 GETs. With it on, the origin received 5 + 0. A second worker started with five cold misses. Private or stale responses, response cookies, credentialed requests, queries and encoded responses went back to the origin.
* On an explicitly supplied empty-input assertion, the bad saved module raised `IndexError` in WASI. The worker received the failing input and expected value and its next program replaced the file. The worker programs in these two controls were scripted to isolate runtime behavior.
* All 64 prompts from G55's eight after-body pulse artifacts were checked for eligibility. The two hard checks would have applied to 0/52 passing and 0/12 failing prompts. They also apply to 0/30 fixed held-out prompts. The independent text-only G55 history makes the inspect instruction applicable to 0/52 passing pulse prompts, 7/12 failed pulse prompts and all 30 fixed held-out prompts. These are coverage counts. [Historical receipt](history.json)

The cache keys all eligible request headers, recognizes an explicitly varied X-Cursor selector and accepts `Cache-Control: public, max-age=N` with a valid date. Its limit is 32 entries, 1 MiB and 60 seconds. The native Requests path bypasses streaming, proxies, custom transports, credentials, encoded bodies and ambiguous freshness policies. The URI, headers, conditional requests and origin time determine whether an actual web task can save any fetches.

## Native worker results

The G55 trunk missed the cold-chain file in both conditions. The stock worker printed the correct count of 3 and wrote temperature/code pairs. The task asks for lot codes ordered by descending rise and then by code. The inspect worker reached the 192-token limit on all three turns and produced no file. Stock used 100, 123 and 2 output tokens. This local pilot uses the first-program study’s token budget. The normal multi-member exam has a longer worker output allowance. [Raw worker turns and files](native.json)

## Reproducing the checks

Run from the repo root in its Python environment.

```sh
HIVE_FIELDWORK_SDK=/path/to/wasi python -m pytest -q tests/test_worker_contracts.py
python -m team.familiarity /path/to/g55-rows.jsonl /tmp/g55-checked.json --rows-sha256 c33f707c7120d279c050748a5752067be708687711aa9acc84a4f434208fadfd
python -m training.experiments.astra_orders.worker_contracts.history --archives /path/to/g55-gate-zips --familiar-index /tmp/g55-checked.json --out /tmp/g55-coverage.json
TZ=UTC taskset -c 3,4 python -m training.experiments.astra_orders.worker_contracts.native --runtime "$LLAMA" --model "$BASE" --lora "$CELL" --familiar-index /tmp/g55-checked.json --out /tmp/paired-results.json --log /tmp/g55-local-server.log
```

For the hosted comparison, download stock and F3 shard artifacts into one folder using their original names. ZIPs and unpacked directories are accepted. The scorer checks protocol settings, the body manifest, request text, task IDs and run identity. It reports gains and losses on common tasks. The four-additional-task verdict requires all 30 tasks in both arms. For a partial rerun, use `--through-attempt N` to include the latest supplied attempt of each shard through N.

```sh
python -m training.experiments.astra_orders.worker_contracts.paired /path/to/shard-artifacts
```
