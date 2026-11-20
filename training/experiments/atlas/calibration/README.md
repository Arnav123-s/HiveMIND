# Can archived agreement safely decide when to answer?

On 28 G52 jobs, a 90% split-conformal gate delivered **21 correct, one wrong and six withheld**. Simply releasing the four-seat plurality gave **27 correct, one wrong and none withheld**. The conformal gate removed six correct answers and kept the one shared mistake. The existing full after-body actually delivered 27 correct and withheld one on the same jobs. This experiment found no reason to replace it with the calibrated rule. [Frozen protocol](protocol.md) · [Per-job decisions, grades and intervals](results.json)

## Answer quality and seat cost

The G50 development, G51 calibration and G52 test cohorts contain 27, 27 and 28 real stdout-answer jobs, respectively. All three have eight distinct seeds. Their seed IDs are disjoint. None of the 28 G52 prompts matches a normalized earlier prompt. The G52 subset includes 23 easy jobs and five hard jobs, selected by the published four-seat stdout cohort. It covers 28 of G52's 64 fresh pulse jobs. All methods see the same archived answers. Inference cost is represented by the number of seats whose recorded answers a rule would need. No new model calls were made. [Cohort definition](../pulse/protocol.md) · [Source workflow artifacts](../pulse/artifacts.json)

| G52 method | Correct | Wrong | Withheld | Delivered / 28 | Wrong among delivered | Seats |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| After trunk alone | 27 | 1 | 0 | 28 | 1/28 | 28 |
| Before trunk alone | 26 | 2 | 0 | 28 | 2/28 | 28 |
| Always release four-seat plurality | 27 | 1 | 0 | 28 | 1/28 | 112 |
| Two-seat corroboration | 24 | 0 | 4 | 24 | 0/24 | 56 |
| Three-seat agreement | 27 | 1 | 0 | 28 | 1/28 | 84 |
| Reserve-on-crash replay | 27 | 1 | 0 | 28 | 1/28 | 60 |
| Task-wise split conformal | 21 | 1 | 6 | 22 | 1/22 | 112 |
| Seed-wise split conformal | 0 | 0 | 28 | 0 | Undefined | 112 |
| G51-certified 10% selective risk | 0 | 0 | 28 | 0 | Undefined | 112 |
| Require all four to agree | 21 | 0 | 7 | 21 | 0/21 | 112 |
| Actual recorded after-body | 27 | 0 | 1 | 27 | 0/27 | 57 completed |
| Four-seat correctness oracle | 27 | 0 | 1 | 27 | 0/27 | 112 |

The after-body includes its ordinary task-aware checks and routing. The reserve row is the published vote replay on the four-seat pool. The oracle has access to the external checker on all proposals and is an upper bound for selecting one of those four original outputs. No selection rule can recover the 28th correct answer from these candidates alone. Across the five hard jobs, the after trunk gave four correct and one wrong; the conformal gate gave three correct, one wrong and one withheld.

## What the probability statement covers

For each job, the target is binary: whether the fixed plurality proposal passed the actual seat checker. A missing proposal has target false and cannot be released. The heuristic score uses only the winning vote count minus the runner-up count. G51 calibrates the true-label nonconformity quantile at 0.75. The conformal prediction set can include “wrong,” “correct,” or both; the system releases only a nonempty candidate with the singleton set “correct.” This estimates coverage of a binary fact about a proposed answer. It does not construct a set containing the true open-ended answer text when every worker misses. [Implementation](run.py) · [Conformal prediction background](https://arxiv.org/abs/2107.07511)

On G52 the prediction set contained the true binary label on 27/28 jobs (96.4%). There were 22 singleton and six two-label sets. The fraction of incorrect accepted jobs was 1/22 (4.5%), compared with 1/28 (3.6%) for always releasing the plurality. Under an illustrative independent, identically distributed job model, the two-sided 95% exact intervals are 81.7–99.9% for conformal set coverage and 0.1–22.8% for selective risk. The two-seat rule's zero observed errors still has an upper endpoint of 14.2% on 24 deliveries. These intervals leave substantial uncertainty. [Exact binomial method](https://doi.org/10.1093/biomet/26.4.404)

A finite-sample split-conformal marginal guarantee requires exchangeability of calibration and future nonconformity scores given the development stage. G51 and G52 have different weights, overlapping ancestry, different tasks and multiple jobs per seed. Their exchangeability is unestablished. Seven of eight G52 seeds had all their task-level binary labels covered. Treating each G51 seed as one unit, the required 90% quantile has rank nine among eight observed seed maxima plus the infinity sentinel. Every test prediction set then contains both labels and the gate releases nothing. Arbitrary deployment shift permits all released answers to be wrong even if several related cells agree.

The separate selective-risk method tested five fixed margin thresholds on G51. The two highest thresholds each retained 16 jobs with zero observed errors. Even that result gives a multiplicity-adjusted one-sided 95% upper bound of 25.0%, above the 10% release target. With zero errors, this five-threshold procedure needs at least 44 independent accepted calibration examples to reach its 10% upper bound. A single threshold fixed in advance would need 29. No threshold qualified. Its realized selective risk is undefined because it issued no answers. Once the threshold decision is fixed, it could short-circuit to zero seats operationally. The table charges the four seats used to compute the recorded evidence consistently across scored abstention policies.

The one wrong test consensus came from a configuration-reading task. Three seats emitted the same empty value and zero keys; the fourth seat returned nothing. The text asked for the final host and the number of distinct keys under a named section. The agreement score was 0.875, high enough to release this wrong answer. The live after-body withheld it. All 21 four-of-four unanimous outputs happened to be correct here, but a shared misconception across four cells would defeat even that stricter rule. [Scored receipts, case g52/h20000521_00](results.json)

## Archived skills and Hedge

The archive indexed historical results by registered task kind and exact worker identity. On each new G52 prompt, it selected the present identity with the best smoothed historical correctness among candidates having at least two matching prior trials. It used G51's trunk in 13 cases and fell back to the G52 trunk on the other 15. It delivered the same 27 correct and one wrong as always choosing the G52 trunk, at one seat per job. This uses registered task kinds and verified historical labels. A free-form chat router would have to infer those kinds.

The separate Hedge comparison learned weights on four *roles* from G50 and G51. Its weights for after-trunk, after-specialist, before-trunk and before-specialist were 0.142, 0.353, 0.224 and 0.281 before opening G52. Weighted voting again delivered 27 correct and one wrong at 112 seats. The physical worker behind a role changes by generation. This replay provides no measured gain from role weighting.

These are historical routing tests on genuinely paired candidate records. They do not evaluate an evolutionary MAP-Elites search, or how absent historical workers would answer a new question. The G50 after trunk was absent from G52's recorded candidate pool; performance on its earlier, differently seeded jobs cannot fill that counterfactual. [Archive and weights by test case](results.json) · [MAP-Elites](https://arxiv.org/abs/1504.04909) · [Hedge](https://doi.org/10.1006/jcss.1997.1504)

## Reproduce

The standard-library runner loads the published pulse cohort, groups text with its existing answer normalizer, and materializes every G52 decision before looking up G52 seat verdicts. The report pins input digests and a digest of the ungraded predictions.

```sh
python training/experiments/atlas/calibration/run.py --out /tmp/atlas-calibration.json
cmp /tmp/atlas-calibration.json training/experiments/atlas/calibration/results.json
```
