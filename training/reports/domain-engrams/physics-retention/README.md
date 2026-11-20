# Independent water-phase correction check

The corrected edit produced an allowed, physically correct phase on all nine new pure-water questions at one atmosphere. The initial edit scored six. The three gains comprise two high-temperature samples previously called liquid, and one below-freezing sample also called liquid. All other v1-correct answers remained correct under the stated rubric.

| Matched native first-token check | Bare 8B | Initial edit | Corrective edit |
| --- | ---: | ---: | ---: |
| Six primary fresh descriptions | 2/6 | 4/6 | 6/6 |
| Three separately frozen supplementary descriptions | 2/3 | 2/3 | 3/3 |
| Three old checks included in corrective training | 2/3 | 2/3 | 3/3 |

The bare model twice said “Ice” where the caller required the label “solid”. These are format failures for a fixed-label interface, although “ice” identifies a physically appropriate state. The corrective gain over the initial edit on the three fresh cases reflects a change to the predicted phase. All nine temperatures and all nine full descriptions differ from each of the 27 teaching examples. The three old checks measure retention of taught inputs.

The test author sealed the panel before the trainer finished and released it only after independently hashing the frozen corrective GGUF (`5b96d40b60dd3b16c9f9d6ae493a0f0f88e02757a1f79b969e96471ea194ce8d`). Recomputing scores from raw decoded native pieces reproduced every group total. The valid run disabled native graph reuse and recovered the identical v1 token when reapplying v1 after v2 on every question. The study covers prompted first-token decisions on nine examples, with no phase-boundary, variable-pressure or other-substance test. [Prior commitment](commitment.sha256) · [Sealed inputs and keys](panel.json) · [Protocol](protocol.md) · [Native four-pass evidence](../water-v2/qualification.json)

The same corrective bytes subsequently returned **12/12 correct labels through the actual graph-safe HTTP serving path**, covering all nine fresh and three old questions with matching rendered prompts. All twelve were checked independently against their expected label from the recorded HTTP response. The distinct corrective edit was admitted to the starter bank. [HTTP receipts](../water-v2/serving-qualification.json) · [Release decision](../water-v2/release.json)
