# Select a program from a table question

This tool receives an English request and a flat CSV or JSON table. It chooses operations, binds the actual column names and category values, executes the resulting program, and can save the requested JSON file. On the independent panel, a handwritten planner solved **13/18** primary requests on *both* table editions. The factorized learned planner solved **11/18**, tying a classifier that recalls entire seen operation pairs. The handwritten planner is the checked publisher’s default. Supplying one separately graded example raised the known-library result to **15/18**, including three of six complete task patterns, with three abstentions and zero wrong primary files. [Independent grader](../transfer/README.md) · [Frozen planning protocol](protocol.md)

## Try it

From the repository root:

```sh
printf 'supplier,units,aisle\nFir,4,East\nElm,3,East\nElm,2,West\n' > /tmp/hive-orders.csv
python -m training.experiments.verified_growth.composer.checked_files /tmp/hive-orders.csv \
  'Sum units by supplier. Save as totals.json.' --out-dir /tmp/hive-supplier-results
```

The file contains `{"Fir": 4, "Elm": 5}`. The CLI also prints the selected operations and the published path. Existing files are protected against overwrite. Use `--mode learned` for the factorized classifier or `--mode native --server http://127.0.0.1:PORT` when a compatible t80 CPU server is running. A directory-qualified output filename, an absent filename or an unsupported computation leads to a refusal. The historical trial's `solver` command can return scalar values directly without naming an output file. [Checked file publisher](checked_files.py) · [Historical solver](solver.py)

One example can disambiguate a request. For the command above, a separate JSON file can contain:

```json
{"rows":[{"supplier":"Fir","units":1,"aisle":"East"},{"supplier":"Elm","units":5,"aisle":"West"},{"supplier":"Fir","units":2,"aisle":"West"}],"answer":{"Fir":3,"Elm":5}}
```

Add `--example /path/to/example.json` and use a fresh output directory. The tool selects from seven known aggregation/selection pairs using the supplied answer, and withholds the result if surviving programs diverge on the new table. This path needs no t80 call.

## What is learned?

The two small linear classifiers fit English requests with human-provided labels. One chooses to count records or sum a numeric column. The other chooses a scalar, grouped mapping, highest group or lowest group. They can choose a pair that never occurred as a complete training label. The flat classifier uses the same words, training rows and optimization method but can choose only observed complete pairs. The explicit cue rules and the independent-agreement arm supply simpler controls. The native model also chooses two operators, using a fixed grammar and the exact request plus header names. The model receives neither the rows nor the answer. The selected operators are then shared by all rows without further inference. [Training examples and optimizer](learner.py) · [Native prompt and grammar](native.py)

Field binding, type checks, exact equality filtering, tie handling, execution and file publication are human-authored. The grouped numeric reduction reuses the earlier atlas primitive. A plan that fits the types can still answer a different question from the one the user meant. In the previous 72/72 study, the same program generated both the request and the executable plan. This test supplies only the independent user's English and data. [Original program generator](../../atlas/proposer/README.md)

The actual t80 semantic selector delivered **4/18** paired primary jobs, with the intended structural code on 6/18. Its 27 native completions emitted 74 tokens and took 526.751 seconds of summed HTTP time. The fixed prompt and shared execution code matter more than syntactic validity here. [Native choices, schemas and timings](../transfer/native.jsonl)

The blind grader ran each request on two independently changed table editions, retained failures, and scored the entire request as correct only when both answers matched its separately computed SQL results. An additional one-example study supplies a third table with its externally known answer and asks which frozen programs that demonstration can distinguish. The constant, unlabelled agreement, known-library and exhaustive typed comparisons account for information supplied by the user. [Qualification protocol](qualification.md) · [Chooser](qualification.py)

On the primary panel the unlabeled planner committee delivered 4/18 and simply repeating the teaching answer delivered 0/18. The one-example emitter using the frozen selector portfolio, the seven historically observed pairs, or all eight type-compatible pairs each delivered 15/18. The portfolio and exhaustive libraries mastered different task patterns. The new eighth pair supplied no extra paired success. Three intrinsically ambiguous requests had no teaching label and were excluded from this comparison.

After the original implementation and external evaluation were frozen, development controls exposed a publication issue and a numeric issue. An absolute requested path could yield an answer without its file. A 41-digit integer sum silently lost its last two units under the default decimal precision. The checked publisher requires a safe named result and sizes decimal precision from the numeric input and row count. It returned the full integer and withheld ambiguous path requests. A separate transport study exposed another failure in which a request for money summed a days column. The checked publisher requires an explicitly bound measure and tests stated currency or time units against the column name. These nine checks are post-study controls. [Original and corrected receipts](publishing-controls.json)
## Final file audit

The existing 27 requests ran through 54 fresh, single-invocation file commands. Adding an independently computed worked example to each of the 24 determinate requests produced another 48 actual invocations. On the 18 primary work orders, the rules publisher returned 13 correct, three wrong and two withheld. The worked-example publisher returned 15 correct, zero wrong and three withheld. Both preserved three of three anchor requests and withheld three adjacent computations. The rules publisher still produced wrong files for two of three inherently unresolved requests. This is a known-cohort file replay; the numeric and filename changes had already been made. The scorer read the physical files, parsed them as JSON and compared them with SQL grades after all decisions. A table edition with no published file is recorded as withheld. [All 102 file receipts](publishing-panel.json) · [Reproduction command](check_publisher.py)

```sh
python -m training.experiments.verified_growth.composer.check_publisher --out /tmp/hive-typed-file-replay.json
```
