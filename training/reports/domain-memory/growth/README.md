# Growing a local label adapter from checked lessons

`./hive learn teach` records an explicit answer on this computer. `./hive learn refresh` fits a small neural adapter to a topic when it has enough examples. A topic can belong to coding, math, physical science, conversation, machine learning or computer engineering. The native trainer updates the output weights of one local Ternary-Bonsai 8B model and measures unrestricted first-token answers with the edit on and off.

```sh
./hive learn teach --domain machine_learning --topic "ML incident audit coding" \
    --prompt "Our ML incident audit uses X or Y. A test label appears among the model inputs." --answer X
./hive learn list
./hive learn status
./hive learn refresh --domain machine_learning --model /path/to/t80.gguf \
    --runtime /path/to/llama-server --threads 1
```

Use at least three distinct prompts per label and at least two labels in one topic. On arrival, each label's first two prompts go into training and the third goes into qualification. Subsequent qualification prompts occur every four distinct prompts of that label. Repeating an example preserves its original split. Contradictory answers to the same prompt and topic remain in local storage and exclude that prompt from fitting and scoring. A contradiction involving the evidence used by a published local edit retires the edit.

The refresh tests up to eight labels per topic, twelve training prompts and six qualification prompts per label. Each qualification prompt must have a single-token expected answer. It promotes an adapter only when it scores higher than the base model, loses none of the base model's correct answers on that panel, and preserves every measured win of the previous active edit for that topic. A changed corpus can produce a new fit from the same base model. Unchanged evidence normally reuses its recorded measurement. Free-form and multiword answers can be retained as evidence. The fitted output layer supports bounded label choices.

## Where evidence comes from

- A generated practice task contributes the exact response of a member whose own grader passed it. The member file and original task must match hashes captured at grading. An unbound older receipt does not qualify.
- A fieldwork order contributes its labeled public inputs only after the executable program passes its public examples and disjoint qualification set and delivers every job. Private tests and job content stay outside the lesson store. The provenance identifies the expected value as the work order's label.
- `teach` records answers the user explicitly supplies. Ordinary conversation is never an automatic training target.

A local SQLite database under `runs/engram-learning` preserves each distinct lesson and its provenance. Set `HIVE_LEARNING_HOME` to move the database. Local artifacts use the native engram directory, normally `runs/engram-learning/native`. Set `HIVE_ENGRAM_LEARN=0` to disable automatic collection. At the end of a practice run with checked observations, the system can refresh one eligible changed topic using a local cached model. `HIVE_ENGRAM_AUTO_REFRESH=0` disables that automatic fit. Explicit `refresh` also accepts `HIVE_ENGRAM_MODEL` and `HIVE_TERNARY_BIN`. Chat requests do not start training.

## Restoring generated practice

The hosted practice runner writes `rows.engrams.jsonl` beside its existing rows. Gathering validates and deduplicates the shard records. A successful release-recording job publishes the combined file with the run, attempt, and complete SHA-256 in its name. Each generation's file survives subsequent releases at its own name. This channel carries generated practice observations only. Local user labels, ordinary conversations, private qualification data, local fieldwork, and personal adapters are excluded.

Use a trusted release copy to restore generated observations offline. The command validates the file hash in a released filename, each record hash, and the practice provenance before recording anything. Checksums establish file integrity. Use a source you trust when importing a custom file.

```sh
./hive learn restore --practice-file /path/to/practice-engrams-RUN-ATTEMPT-SHA256.jsonl
./hive learn status
./hive learn refresh --domain math --threads 2
```

Supply `--sha256 HASH` when the downloaded file has been renamed. Restoring the same file twice preserves one copy of each lesson and evidence record. Regular hosted practice also caches its generated-only local lesson database and native adapters per DNA and shard. Later ordinary practice can resume that shard’s learning. Trial, comparison and benchmark jobs bypass this cache. A new installation or an expired cache can restore the chosen release files.

## Frozen demonstration

The example corpus teaches an arbitrary two-letter code for two kinds of ML audit finding. The second batch adds distinct wording and further qualification prompts. Both batches and their order were frozen before execution, SHA-256 `8457b562e9044343248efad405610b84142d7dee4b467b2678ac5cfc72a32521`. Every example was supplied explicitly for the exercise. [Corpus](incident-labels.json) · [Reproduction](replay.py)

```sh
python training/reports/domain-memory/growth/replay.py --model /path/to/t80.gguf \
    --runtime /path/to/llama-server --out /tmp/hive-local-growth
```

The replay creates an isolated store, invokes the ordinary CLI, and writes both full measurements. Its scope is the first generated token on a small, labeled classification contract.

| Refresh | Fitting prompts | Reserved prompts | Base correct | Fitted edit correct | Publication |
| --- | ---: | ---: | ---: | ---: | --- |
| First batch | 4 | 2 | 1 | 1 | Declined |
| After eight more lessons | 10 | 4 | 2 | 4 | Published |

The base returned `X` on every reserved prompt. After the second batch, the edit returned `Y` for both class-imbalance findings and retained `X` for both leakage findings. The four probes included both earlier cases and two newly reserved cases. The training and qualification prompts use different sentences with shared diagnostic vocabulary. This measures learning an explicitly taught code on four examples. The earlier revision was declined. This pilot measures preservation of previous correct answers on the panel. Retention across two deployed local edits would require a further qualified refresh. [Raw native results](result.json)

Each standalone fit used one CPU thread. The first fit and qualification took 25.3 minutes and the second took 21.4 minutes under concurrent load. The published standard GGUF adapter occupied 1,246,560 bytes and had effective rank two. The unchanged third refresh returned the saved qualification without starting the model. The first fit used HTTP embeddings. The second reused identical token prefixes in the native feature extractor. Both rounds scored unrestricted first tokens with the native model and the adapter at scales zero and one.

## Try the trained example

The portable bank contains the exact qualified public demonstration weights and manifest. The adapter SHA-256 is `6bb2dd875f9393ba7478a4e35cf55cadde69827e71891df3c5b3c5d83e42a54a`. The manifest SHA-256 is `98b5b16483fc1addf2e30a9cdd8f0e73b2464e7d4fef11b45c3bb0e8c21b28b0`. This named X/Y convention is available as an example outside the default starter bank. [Weights and manifest](example-bank/)

```sh
HIVE_ENGRAMS_HOME="$PWD/training/reports/domain-memory/growth/example-bank" ./hive learn list
python training/reports/domain-memory/growth/serve.py --grade --model /path/to/t80.gguf \
    --runtime /path/to/llama-server --out /tmp/hive-grade-growth
python training/reports/domain-memory/growth/serve.py --model /path/to/t80.gguf \
    --runtime /path/to/llama-server --out /tmp/hive-served-growth
```

The `--grade` command reconstructs the four frozen prompts from their recorded hashes and the human-labeled corpus, then runs the native paired score directly on the saved weights. Both modes use a single CPU thread and a fresh output directory.

The serving reproduction checks the base and adapter hashes and invokes the ordinary `talk.reply` route. It uses the first reserved leakage example with the exact topic name prefixed, as specified before the second round's result was known. The receipt records native adapter scales during generation and the complete response. [Serving input](served-case.json)

The original two-round replay used the runtime’s default graph reuse. A later runtime audit found that changing adapter scales can reuse an obsolete computation graph. On a fresh CPU server with graph reuse explicitly disabled, the same published GGUF and all four original prompts reproduced **2/4 → 4/4**. Every before/after token matched the first measurement. This repeat used the same four probes and tested runtime reproducibility. The first round declined its candidate and discarded its weights. Its 1/2 tie remains an initial measurement under the original runtime configuration. [Corrected raw grade](graph-safe-grade.json) · [Native environment](regrade-environment.json) · [Original index](initial-index.json)

Previously recorded local growth heads now require the graph-safe validation version for automatic serving. On the original evidence, refresh can recheck a previous fit’s immutable bytes directly. A passing revision receives a current proof. Old weights, original measurements, and labels remain inspectable after either outcome. The first user-facing witness routed the named request to a worker, which produced no answer. We interrupted that run before its final reply while correcting runtime and routing. [Initial routing trace](initial-serving-route.json)

After the routing change, that same named X/Y request returned exactly `X` in **one native call**. The active scale of `eg8a7da83f3dc5b75b029cb270` was **1.0**. The request used 155 prompt tokens and one generated token and took 27 seconds on one CPU thread with an empty prompt cache. The predeclared example repeats a leakage case the base already answered correctly. The paired four-case grade measures the improvement, and this readback establishes that the ordinary user-facing route selected and applied the packaged weights. [Served reply and native scales](served/machine_learning-choice.json) · [Launch and source hashes](served/launch-48af3180cebe.json)
