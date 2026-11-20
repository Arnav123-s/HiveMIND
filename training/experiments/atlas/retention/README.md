# Fixing observed failures and retaining old answers

Giving priority to mistakes helped the six specialists fix **6 of 9** selected errors. One of the three previously correct selected answers regressed. On 48 questions excluded from all fits, the same policy gained five correct answers and lost five. It finished at **38/48**, equal to the incumbent. None of the eight adaptations improved the total. The distinction matters for any proposal to reward the hive for fixing a failure it has just seen.

Each arm inspected exactly 42 labeled examples and fitted exactly 12. The 42 comprised 18 previously learned examples across six domains and 24 newly introduced examples from water phase and hardware timing. Balanced replay sampled each current domain and label by a fixed hash. Priority replay used the same per-class capacity but selected actual incumbent errors first. Rehearsal spent six exposures preserving six earlier correct score vectors and six exposures on current examples. Without rehearsal all 12 went to current examples. The same selected data went to one broadly trained head or to six domain-specific heads. All evaluation was zero-shot from the resulting weights. No example bank was consulted during scoring. [Frozen protocol](protocol.md) · [Runner](study.py)

| Replay | Old examples rehearsed | Head | Selected mistakes repaired | Reserved /18 | Earlier checks /18 | Supplemental /12 | All /48 | Gains / losses vs incumbent | CPU ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| No adaptation | 0 | Incumbent | — | 17 | 14 | 7 | 38 | 0 / 0 | — |
| Balanced | 0 | Broad | 0/5 | 15 | 15 | 6 | 36 | 1 / 3 | 8.00 |
| Balanced | 0 | Specialists | 1/5 | 15 | 15 | 5 | 35 | 1 / 4 | 8.44 |
| Balanced | 6 | Broad | 1/1 | 16 | 14 | 7 | 37 | 0 / 1 | 7.87 |
| Balanced | 6 | Specialists | 1/1 | 16 | 14 | 7 | 37 | 0 / 1 | 11.41 |
| Priority | 0 | Broad | 2/9 | 15 | 14 | 7 | 36 | 2 / 4 | 7.39 |
| Priority | 0 | Specialists | 6/9 | 15 | 15 | 8 | 38 | 5 / 5 | 7.03 |
| Priority | 6 | Broad | 1/5 | 15 | 14 | 6 | 35 | 1 / 4 | 8.76 |
| Priority | 6 | Specialists | 1/5 | 15 | 14 | 6 | 35 | 2 / 5 | 11.52 |

The 18 newly reserved examples comprise one previously published teaching prompt per domain and label, excluded from this follow-on's initial fit, adaptation, and selection. Past researchers had already used these prompts. The other 30 were familiar from the island study. They include 18 older qualification questions and 12 supplementary water and timing questions. All eight arms regressed on the newly reserved panel. The bare base and the prefit incumbent were correct on the same 38 of 48 questions. These are paired small-sample results on public data. [Case-level predictions, selected IDs and timings](results.json)

Rehearsal preserved all six selected old answers in every arm that used it. That local success gave different outcomes elsewhere. For balanced specialists, rehearsal raised the excluded score from 35 to 37. For prioritized specialists it lowered the score from 38 to 35. Rehearsing six older cases consumed half of the current-data budget. This design measures that explicit tradeoff.

The broad head has 16,456 factor coefficients. Six forced-domain heads have 98,736 coefficients counted as separate stored heads. Their routing is given the true domain, and they share a copy of the same incumbent before adaptation. The specialists' advantage under priority without rehearsal was two excluded answers over the broad model with an identical example budget. The broad head scored one higher under balanced replay without rehearsal. Stored capacity and supplied domain identity therefore matter when comparing these alternatives. CPU numbers are median process milliseconds for inspecting 42 cached endpoints, selecting rows, and fitting, across seven rotated, one-thread runs. Prior 8B feature extraction, evaluation, and the shared initial fit are excluded.

## Feedback routing

Before scoring, the routing comparison fixed balanced replay with six rehearsed cases as its source of broad and specialist predictions. There were 48 distinct inputs, two resident expert slots, and two post-answer checks per input under every policy. Fixed residency, LRU, and a decaying score based on *extra correct answers* all produced 37/48 in both input orders. Even a per-question oracle that could use either head scored 37/48. In this preselected condition, the two source policies were correct on exactly the same inputs.

| Input order | Fixed hits /48 | LRU hits /48 | Verified-success hits /48 |
|---|---:|---:|---:|
| Hash-interleaved domains | 12 | 17 | 0 |
| Contiguous domain blocks | 12 | 42 | 0 |

LRU evicted a resident 29 times on the interleaved stream and four times on the blocked stream. The verified-success table started empty and earned no positive edge to retain. This tests the bookkeeping and its available opportunity. It provides no evidence that traffic reinforcement improves answer accuracy.

## Scope and reproduction

This is an output-head experiment using the original Ternary-Bonsai-8B final states and unrestricted first-token logits. The prior calibration reproduced all 36 archived native token decisions. The current experiment measured changes in fitted weights without using the 8B generation lane. It tests selective replay, preservation of previously correct examples, supplied-domain specialization and a small feedback routing policy. A biological inheritance effect, faster relearning across generations, stochastic resonance, actual exploration, inferences per task, and generated-code repair remain unmeasured. The rehearsals are ordinary checked teaching examples from this corpus; the historical G41 release questions were never used. [Model and cache calibration](../islands/calibration.json) · [Prior island experiment](../islands/README.md)

```sh
python training/experiments/atlas/retention/study.py --out /tmp/retention-replay.json
```
