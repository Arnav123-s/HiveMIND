# Can extra inputs disprove agreement about a file?

Two workers can print the same answer on a user's example while their Python files implement different behavior. We ran both files on additional, admissible inputs supplied with the request. Differing outputs disprove agreement. They leave open which file to send. [Protocol](protocol.md) · [Candidates and public probes](panel.py)

**Twelve constructed jobs covered eight simple functions.** Ten jobs had two workers with matching output on the primary example. The ordinary HiveMIND post-generation handoff accepted all ten and selected the first worker's file. The other jobs each had one reporting worker, and the normal handoff withheld both. The candidates were hand-written to exercise specific failure modes. The guest executed their actual primary examples and every admitted extra probe. [Sealed decisions, hashes and observed values](decisions.json)

| Probe result | Jobs | What actually happened |
| --- | ---: | --- |
| Contradicted | 4 | Doubling in both worker orders, making a slug, counting even numbers including duplicates |
| Matching observations | 3 | Distinct correct deduplication implementations, two identical-in-behavior absolute-value bugs, a wraparound error missed by the supplied inputs |
| Unknown | 5 | No additional input, invalid additional inputs, a wrong singleton, a correct singleton, and one guest exception |

For the doubling request, both files returned zero on the primary example. With 4 as an extra input one returned 0 and the other 8. Reversing worker order reversed the values. No expected output was available to the check on either job. For the absolute-value pair both returned 0 for −3, so even a probe at the actual defect produced matching observations. For a decimal dial both matched on 0 and 5; these probes missed the wraparound at 9. The guest exception was recorded as incomplete evidence under the frozen rule. [Per-job observations](decisions.json)

## Which files would reach the user?

An independent author received the eight public contracts and input bounds and supplied eight labeled examples for each. They could not see the candidate programs, public probes or policy. The additional probes above carried no answers. The independent keys were released after the sources and protocol were frozen. Keyless decisions were written before grading. A file counts as correct here if it passes all eight external examples for its function. Removing external inputs that happened to equal a job's primary or admitted secondary input leaves six to eight external examples per job and preserves all 12 first-file verdicts. [Independent examples](outside-grades.json) · [Graded outcomes](grades.json)

| Rule applied to the stock publication decision | Correct files sent | Wrong files sent | Withheld |
| --- | ---: | ---: | ---: |
| Ordinary handoff | 5 | 5 | 2 |
| Withhold only after observed disagreement | 3 | 3 | 6 |
| Require at least one extra input and all observed outputs to match | 1 | 2 | 9 |

The negative check caught two wrong shipments and suppressed two correct shipments. The share of correct shipments stayed at one half. All four vetoes demonstrated a real behavioral difference; twice the ordinary chooser had selected the correct worker already. Only one of the three files with matching extra observations passed the independent suite. Neither singleton was released. These twelve staged jobs measure the behavior of the decision rules on known failure modes. The original G52 jobs had a single reporting worker and no admissible extra inputs for a peer comparison. They earn zero additional confirmed deliveries here. [Original G52 investigation](../README.md)

## Reproduce

From the repository root, point `--sdk` at the fieldwork CPython/WASI guest directory. Each phase loads one guest, pinned to one CPU. Submitting reads only the panel, protocol and ordinary handoff. Scoring independently repeats the submission before opening the external keys. All candidate sources and all recorded decision fields are checked for exact replay except the instruction counter. On the first replay four of twelve counters varied with identical inputs and outputs. The original submission used 16 guest calls to compare 16 admitted input pairs, consuming 16,352,664,624 WASI fuel units for the extra probes. Each call accepts a batch of inputs. Primary examples and subsequent grading are excluded from this count. [Runner](compare.py)

```sh
python -m training.experiments.verified_growth.delivery_audit.probes.compare \
  --sdk /path/to/wasi --decisions /tmp/hive-probe-decisions.json
python -m training.experiments.verified_growth.delivery_audit.probes.compare \
  --sdk /path/to/wasi \
  --decisions training/experiments/verified_growth/delivery_audit/probes/decisions.json \
  --keys training/experiments/verified_growth/delivery_audit/probes/outside-grades.json \
  --grades /tmp/hive-probe-grades.json
```
