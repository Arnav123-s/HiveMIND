# Independent date wording evaluation

On 13 questions with unique calendar answers, the strict calculator returned two correct answers and the same calculator with the frozen wording adapter returned six. No delivery regressed. Both arms withheld all five genuinely indeterminate or invalid questions and made zero incorrect deliveries.

| Fresh request group | Questions | Strict correct | With wording correct |
| --- | ---: | ---: | ---: |
| Direct weekday or elapsed days, including conversational paraphrases | 10 | 2 | 6 |
| Inclusive count, workweek count, or weekday of the following day | 3 | 0 | 0 |
| Invalid date or insufficient information | 5 | 5 appropriate withholds | 5 appropriate withholds |

The added forms recognized a day/month/year appointment, an ISO date followed by “fall on”, an imperative weekday query, and elapsed days over a leap day. Four direct calendar requests were still missed, including the bus-ticket question, “gap in days”, a hostel stay and two events on the same date. All seven answerable misses remain in the denominator.

The judge generated the 18 new questions and answer keys independently using the standard library calendar. These are separate from the earlier 18 mixed-service questions. Business-day and inclusive-count semantics receive credit only for the requested value. This hand-authored panel measures the selected phrasings and provides limited evidence on how often real users will encounter them. [Questions](panel.json) · [Keys](keys.json) · [Prospective scoring rules](protocol.md) · [Freeze hashes](manifest.sha256) · [All comparisons and source hashes](results.json)

To replay the strict calculation and the same calculation after optional normalization, run the following from the repository root. The runner verifies the question, key, protocol and adapter digests. It requires no SDK, model, or network. Results include the exact calculator and adapter hashes. The recorded initial comparison used service `83fd3d63`, strict arithmetic `d1f10652`, and adapter `90ffee46`.

```sh
python -m training.experiments.atlas.service.wording_eval.run --out /tmp/hive-date-wording-results.json
```
