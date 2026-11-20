# Verify one worker’s whole answer before buying a second

A G49 worker was asked what weekday 13 May 2027 would be. It printed “Thursday”. The calendar independently confirmed the complete answer, making the second worker unnecessary. Across **64 genuine G49 after-body pulse requests**, this policy would have saved **8 of 141 completed worker calls (5.7%)**. Both paths delivered 49 correct reports, seven incorrect reports and eight abstentions. [Recorded first answers and original reports](recorded.json.gz) · [Per-question outcomes](results.json)

| Scope | First outputs certified | Incorrect certifications | Actual completed workers | Workers with certificate |
| --- | ---: | ---: | ---: | ---: |
| All 64 G49 pulse tasks | 8 | 0 | 141 | 133 |
| 63 exact prompts absent from the earlier G50–52 text panels | 7 | 0 | 139 | 132 |
| Eight tasks in a supported contract | 8 | 0 | 16 | 8 |

The eight verified results covered two prices after a percentage change, two weekdays, two temperatures in Fahrenheit, one elapsed date interval and one greatest common divisor. The other 56 requests used their **original** after-body trajectory and delivery. They account for all seven wrong reports and eight abstentions. Archived timestamps attribute 69.51 seconds to the eight second seats, approximately 1.0% of the 6,880 seconds across all original runs. These are avoided intervals in a replay; there was no live wall-clock timing trial. Zero observed false certifications in eight positives leaves substantial uncertainty about other wording and outputs.

The rule receives only the literal request and the first worker’s full answer. It matches the whole request to a limited contract, computes the expected result from the constants in the request, and independently parses the whole answer. Extra claims, incompatible units, missing requested precision, ambiguous dates or unsupported tasks fall back to the other workers. It uses the repository writer’s existing calendar parser behind a full-date grammar. The GCD, decimal price, and temperature calculations use standard arithmetic. The verifier imports no exam code and does not use the task maker, seed, official grade, other workers or generated solution code. Fourteen adversarial or out-of-contract controls were rejected; five correct positive controls were accepted. [Certificate](certificate.py) · [Predeclared protocol](protocol.md) · [Controls and scorer](evaluate.py)

There is an important simpler control. Since this verifier computes the complete expected answer, the same handwritten calculator can deliver those eight answers without a first worker. On the same cohort, that retrospective diagnostic uses **125 workers**, gives the same 49/7/8 totals and avoids 16 calls. Keeping a first proposal is defensible if the system specifically needs its observed response or provenance. This evidence supports a limited verified calendar/arithmetic route; it does not establish learned reasoning or a general one-worker agreement policy.

The complete G49 after-body generation was omitted from the other pulse study before this rule and its protocol were frozen. One of its 64 prompts repeated an earlier projected task, and the deduplicated result above excludes it. The untouched scoring ledger regrades each certified worker with its independently regenerated exam task and checks its grade against the original worker verdict. Original grades are carried forward on every unmodified fallback. No synthetic input contributes to the 64-task result. [G49 workflow](https://github.com/Arnav123-s/HiveMIND/actions/runs/44428460725) · [Original artifact identities and checksums](artifacts.json)

From the repository root:

```sh
python training/experiments/atlas/pulse/one_checked/evaluate.py
# To regenerate recorded.json.gz from the eight original artifact ZIPs named <id>.zip:
python training/experiments/atlas/pulse/one_checked/evaluate.py --rebuild --raw /tmp/hive-pulse-archives
```
