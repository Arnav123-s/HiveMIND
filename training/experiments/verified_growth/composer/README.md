# Select a program from a table question

This tool receives an English request and a flat CSV or JSON table. It chooses operations, binds the actual column names and category values, executes the resulting program, and can save the requested JSON file. On the independent panel, a handwritten planner solved **13/18** primary requests on *both* table editions. The factorized learned planner solved **11/18**, tying a classifier that recalls entire seen operation pairs. The stronger handwritten result is the default in the checked file publisher. [Independent grader](../transfer/README.md) · [Frozen planning protocol](protocol.md)

## Try it

From the repository root:

```sh
printf 'supplier,units,aisle\nFir,4,East\nElm,3,East\nElm,2,West\n' > /tmp/hive-orders.csv
python -m training.experiments.verified_growth.composer.checked_files /tmp/hive-orders.csv \
  'Sum units by supplier. Save as totals.json.' --out-dir /tmp/hive-supplier-results
```

The file contains `{"Fir": 4, "Elm": 5}`. The CLI also prints the selected operations and the published path. Existing files are protected against overwrite. Use `--mode learned` for the factorized classifier or `--mode native --server http://127.0.0.1:PORT` when a compatible t80 CPU server is running. A directory-qualified output filename, an absent filename or an unsupported computation leads to a refusal. The historical trial's `solver` command can return scalar values directly without naming an output file. [Checked file publisher](checked_files.py) · [Historical solver](solver.py)

## What is learned?

The two small linear classifiers fit English requests with human-provided labels. One chooses to count records or sum a numeric column. The other chooses a scalar, grouped mapping, highest group or lowest group. They can choose a pair that never occurred as a complete training label. The flat classifier uses the same words, training rows and optimization method but can choose only observed complete pairs. The explicit cue rules and the independent-agreement arm supply simpler controls. The native model also chooses two operators, using a fixed grammar and the exact request plus header names. The model receives neither the rows nor the answer. The selected operators are then shared by all rows without further inference. [Training examples and optimizer](learner.py) · [Native prompt and grammar](native.py)

Field binding, type checks, exact equality filtering, tie handling, execution and file publication are human-authored. The grouped numeric reduction reuses the earlier atlas primitive. A plan that fits the types can still answer a different question from the one the user meant. In the previous 72/72 study, the same program generated both the request and the executable plan. This test supplies only the independent user's English and data. [Original program generator](../../atlas/proposer/README.md)

The blind grader ran each request on two independently changed table editions, retained failures, and scored the entire request as correct only when both answers matched its separately computed SQL results. An additional one-example study supplies a third table with its externally known answer and asks which frozen programs that demonstration can distinguish. The constant, unlabelled agreement, known-library and exhaustive typed comparisons account for information supplied by the user. [Qualification protocol](qualification.md) · [Chooser](qualification.py)

After the original implementation and external evaluation were frozen, two development controls exposed a publication issue and a numeric issue. An absolute requested path could yield an answer without its file. A 41-digit integer sum silently lost its last two units under the default decimal precision. The checked publisher requires a safe named result and sizes decimal precision from the numeric input and row count. It returned the full integer and withheld ambiguous path requests. These four checks are post-study controls. [Original and corrected receipts](publishing-controls.json)
