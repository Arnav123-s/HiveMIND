# Three generations of CPU-trained specialist heads

The base answered 21 of 30 archived questions correctly. When the domain of each question was supplied, the six migrated specialist heads answered 23 with all 60 training examples and 24 with 30 selected examples. The one extra correct answer was a water-phase question. Reducing the pull toward the shared trunk from 0.5 to 0.1 produced no further gain after migration. Serving one merged head for everyone scored 20 or 19, below the base. These results give no basis for changing the live growth workflow.

| Training examples | Pull for 3 generations | Third-generation local /30 | Migrated local on 18 earlier anchors | Migrated local on 12 held out | Shared trunk /30 | Fit CPU ms | Total training CPU ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| 60, all | 0.5 | 21 | 15 | 8 | 20 | 22.51 | 54.55 |
| 60, all | 0.1 | 20 | 15 | 8 | 19 | 23.62 | 55.63 |
| 30, selected | 0.5 | 21 | 15 | 9 | 20 | 21.00 | 56.74 |
| 30, selected | 0.1 | 20 | 15 | 9 | 19 | 19.46 | 53.17 |

The bare base scored 14/18 on the earlier anchors and 7/12 on the other held-out cases. A centralized single fit on all 60 examples scored 15/18 and 7/12. The two half-budget arms made five previously wrong answers correct and lost two previously correct answers. Both losses were timing-unit questions. The four post-migration arms had the same per-case results on the 18 anchors. Compared with the bare base, each gained two of those earlier answers and lost one. All of the half-budget arm's one-question advantage over full training came from a single changed token decision on the 12 water and timing cases. There is no random half-sample arm to attribute that difference specifically to the selection rule.

## What was measured

Six islands learned the coding, geometry, water phase, conversational move, dataset split and timing-unit exercises. Each started with zero additional weights and updated its actual 18 × 4,096 output projection, stored in rank-four factors. Each generation introduced a different answer class on each island. The half-budget arms took the examples with the largest base-model error margins within each class. The full-budget arms saw every training example once. Each child began from its prior weights pulled toward the previous shared mean by 0.5 or 0.1. A final common migration averaged each island halfway toward the third trunk without further fitting. The supplied domain for each local prediction gives these scores an advantage over a general-purpose chat system that must recognize the task itself. [Frozen protocol](protocol.md) · [Runner](run.py)

The test uses archived final hidden states and logits from the real Ternary-Bonsai-8B CPU runtime. It fits and merges new head weights. For each proposed head, only 18 vocabulary items can change. Comparing their updated scores to the strongest untouched token recovers the unrestricted first-token argmax over all 151,669 entries for this cached linear projection. The score accepts capitalization and token whitespace variants; the receipt also includes the stricter canonical-token count. Rebuilding the six published original fits reproduced every previously measured native first token across 18 bare and 18 adapted cases. The four newly studied heads were scored with these cached states. No new end-to-end generation or live model training was performed. [Calibration by token ID](calibration.json) · [Native training and qualification provenance](../../../reports/domain-engrams/README.md)

All 30 evaluation examples were withheld from every fit in this study. The original 18 checks were already public; the other 12 are previously published teaching examples reserved prospectively here. They span only water and timing. Repeated per-round inspection used the frozen evaluator with no refitting. The experiment offers 30 paired observations from six narrow output contracts. It does not measure open-response quality, a learned router, long-term memory, full-network adaptation or production compute savings. [Examples, per-case predictions and run times](results.json)

## What happened in the merge

| Rows / pull | Rank 4 squared singular energy kept | Exact rank 32 trunk /30 | Pairwise cosine range | Rank 4 after alternating signs /30 |
|---|---:|---:|---:|---:|
| 60 / 0.5 | 95.96% | 20 | 0.059 to 0.519 | 19 |
| 60 / 0.1 | 91.37% | 19 | 0.004 to 0.134 | 19 |
| 30 / 0.5 | 94.62% | 20 | 0.049 to 0.439 | 19 |
| 30 / 0.1 | 89.06% | 19 | 0.004 to 0.112 | 19 |

Each arm had zero negative cosines among the 15 pairs of complete effective local weight matrices. Weaker pull made the final directions closer to orthogonal. Alternating the signs of whole specialists changed one final token in the 0.5-pull arms and zero in the 0.1-pull arms. Although rank-four truncation discarded 4–11% of the weight energy, recovering the full arithmetic mean at rank 32 changed none of the four aggregate scores. The recovered matrix's relative error was below 5 × 10⁻⁸ in every ordinary arm. The receipt records the complete spectra, relative errors, signed and unsigned scores at ranks 1, 4, 8, 16 and 32, alongside the ordinary training library's energy calculation. Averaging and diluting different specialists can cost decisions even when numerical truncation preserves their scores. [Repository QR/SVD merger](../../../merge.py)

One-thread median process CPU times come from nine rotated repetitions after a warm-up on an Intel Xeon Platinum 8370C, NumPy 2.5.5. Selecting half the inputs reduced fit time by 7% under the normal pull and 18% under weaker pull. The total includes selection, local fits, pulling weights and trunk merges. The half-budget total was 4% higher for ordinary pull and 4% lower for weak pull. Differences of this size overlap repeat-to-repeat variation. The shared merge cost limits any speed claim on this small problem. State extraction and native generation are excluded from all four costs.

## Reproduce

Run from the repository root with Python 3.12 and NumPy. The checked-in compact cache supplies the 18 original check features and sufficient logit values. The other 72 feature vectors come from existing published training archives.

```sh
python training/experiments/atlas/islands/run.py --out /tmp/island-replay.json
python training/experiments/atlas/islands/validate.py
```

The native base SHA-256 was `1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922`. The archive extractor used ik_llama.cpp revision `7aa7e01482db892b023bb9aace9a40567ab5297a`. The optional cache builder accepts the original raw feature and base-logit dumps plus the model's token vocabulary. Every feature already available in the public archives was checked for bitwise identity with its raw dump. SHA-256 values for the protocol, source and numeric inputs are stored in the results. [Cache builder](prepare_cache.py) · [Calibration runner](validate.py)
