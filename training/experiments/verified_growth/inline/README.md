# Can an inline table reach the same solver as an attachment?

The frozen typed composer accepts a named table. The fixed exam supplies a user message and no attachments. This transport recognizes a single explicitly named literal CSV or TSV with a rectangular table, a simple header and an instruction naming a JSON output file. It sends the request and rows to the same planner and executor. An explicit source name is required even on fenced tables. The user’s requested destination is preserved. TSV is parsed using tabs, then represented as an in-memory CSV under the same basename for the existing input API. The transport itself creates no physical files. [Frozen protocol](protocol.md) · [Source](ingress.py)

On a development fixture, five plain or fenced table forms returned the same plan, raw value, filename and file bytes as the ordinary attachment. All 13 controls covering conflicting tables, malformed rows, ambiguous or negated outputs, and unsupported paths withheld the result. The source was frozen at SHA-256 `17d058b893caf48ce7e1f9c756c6de8101bdcf4e750fd19410461b7d1ba51498` before the independent evaluator disclosed its cases. [Development controls and receipts](controls.json)

On four independently written, sealed user messages the transport delivered **0/2 answerable tasks** and withheld both insufficient or unsupported requests. All four supplied fenced table contents without naming the input. The two answerable questions named the required JSON output. On the previously examined official 30-request cohort, the same bridge bound zero messages and changed no official grade. The official comparison is a retrospective interface diagnostic. [Independent panel](confirmation.json) · [Four decisions and products](confirmation-results.json)

In a separate diagnostic, the evaluator explicitly supplied a source name for each of the four original tables. The composer then handled both answerable requests. It produced the correct per-boat minute totals and the row count of four. It still declined the request for both a CSV and a plot. On the remaining request, the customer asked for rent in dollars and said the table supplied occupied days and no prices. The solver nonetheless produced `rent.json` containing **21**, the sum of the days column. The product had a valid JSON shape and a type-correct numeric operation. The numeric field represented the wrong quantity. Removing only an input guard would expose this failure. [All outputs and independent grades](confirmation-results.json)

Run with standard Python from the repository root.

````sh
python -m training.experiments.verified_growth.inline.controls
python -m training.experiments.verified_growth.inline.confirm
python -m training.experiments.verified_growth.inline.ingress <<'END'
Sum units by supplier. Save as totals.json.

```csv orders.csv
supplier,units
Fir,4
Elm,3
Elm,2
```
END
````

For programmatic use, `extract(message, {})` returns the normalized request and file map on a match. A caller can pass that pair unchanged to `composer.solver.run_files`. A miss returns `None` and leaves the existing system free to handle the request.
