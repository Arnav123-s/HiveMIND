# Choosing between an old answer and six retained specialists

The older specialist study fixed six of nine selected mistakes and still ended level with the incumbent on questions excluded from fitting. Here the incumbent and six specialist heads keep their original weights throughout. Only the chooser learns: after a whole batch has received answers, an external source reveals the correct word and the chooser updates its record. Every new answer from an archive chooser must have been produced by an actual member.

On 48 previously published questions, the incumbent and always taking the requested domain's adapted specialist both scored **38/48**. The latter gained five and lost five. The most conservative feedback chooser also scored **38/48**, preserving every starting success. A less restrictive chooser that used earlier labeled neighbors to choose among actual member outputs scored **40/48**, gaining four correct answers and losing two. Picking the right member with knowledge of each answer would yield **43/48**. The five genuinely recoverable misses justify measuring choice separately from member skill. [Frozen protocol](protocol.md) · [Chooser implementation](route.py)

## Independent confirmation on the real 8B model

On **18 newly authored requests**, a chooser using the nearest externally labeled example reached **17/18** by selecting actual archived member outputs, up from **15/18** for the incumbent. Both changed answers were correct. No current or previous single head scored above 15. This chooser reached the archive's 17/18 ceiling here. A stricter feedback gate scored **16/18**, matching the simpler policy that replaces only words outside the allowed set. The unconstrained neighbor classifier supplied labels directly and scored **18/18**. These are six previously taught three-way decision tasks, three new questions per domain. They contribute no official unseen-task-kind credits. [All per-question decisions and four prior waves](results.json) · [Independent panel](fresh.json) · [Frozen native measurements](fresh-states.npz)

| Final 18 | Correct | Newly correct / previously correct lost |
| --- | ---: | ---: |
| Incumbent | 15 | 0 / 0 |
| Requested domain's newest head | 15 | 2 / 2 |
| Highest earlier scoring head | 15 | 1 / 1 |
| Fixed random head per request | 15 | 0 / 0 |
| Invalid-word fallback / guarded feedback | 16 / 16 | 1 / 0 in each |
| Nearest earlier label among emitted answers | 17 | 2 / 0 |
| Direct nearest earlier label | 18 | 3 / 0 |
| Base restricted to three allowed tokens | 16 | 1 / 0 |
| Hindsight over all emitted answers | 17 | 2 / 0 |

For a sample at minus twelve degrees Celsius, only the physics specialist gave “solid”; most members emitted “at.” For a controller waiting 0.000007 seconds, the engineering specialist supplied the correct unit “us” when the incumbent said “ns.” The neighbor-based selector found both. A water sample equilibrated at 121 degrees Celsius exposed the candidate ceiling: every head issued “liquid.” The direct classifier supplied “gas.” These few examples distinguish valid selection, shared member failure and a direct learned answer.

**Effect of accumulating feedback.** Freezing the memory at its 42 original teaching labels produced the same 40/48 and 17/18 for the archive-constrained neighbor chooser, including identical per-request correctness. Growing the *direct* label classifier with the earlier feedback cost one correct answer on the 48 published requests (40 to 39) and gained one on the fresh 18 (17 to 18). The new terminal gain was a machine-learning split request: the direct classifier changed “train” to “test” for a partition opened only after model and threshold selection. Revisiting the previous 48 after four waves, the archive-constrained neighbor chooser and feedback guard retained their original correctness case for case. The direct classifier gained two and lost one on that revisit, excluding the identical question from neighbor lookup. This is externally supervised feedback, with a cross-cohort tradeoff. Consecutive improvements on independent generations remain unobserved. [Individual counterexamples, retention and static-vs-growing controls](audit.json)

The original independent panel digest was shared before the primary chooser's code freeze; its file path was given to the experimenter afterward. No answers were disclosed to the primary chooser within the final batch. Replacing every label of a current batch with dummy labels reproduced the exact decision digest for every wave. The 18 new questions had zero exact wording overlaps with the 90-item historical corpus. Its historical control prompt reproduced all editable canonical logits with maximum absolute difference zero. The fresh cache alone occupies roughly 271 KiB. [Audit source](audit.py) · [Native extractor](extract.py)

## How the chooser learns

The six domain instructions explicitly name their three legal output words. Forty-two old or correction examples in six domains were available to the study. Eighteen fitted the common incumbent, and twelve selected training cases fitted the archived specialists. All six specialist slots and the incumbent are kept. Only three sets of weights are distinct: the original update assigned changes to engineering and physics, while the other four slots retained a byte-identical copy of the incumbent. Across the archival panel, members disagreed on eleven of the 48 inputs. On any subsequent request the same real native 8B hidden state and unrestricted base logits score all seven candidate heads. The resulting complete-vocabulary greedy words are compared after case normalization. The model's output vocabulary is never restricted when recording a member answer. [Earlier repair study](../../atlas/retention/README.md) · [Native scoring calibration](../../atlas/islands/README.md)

A previous example supplies a possible answer based on cosine similarity of its native representation. The chooser considers that word only when at least one member actually emitted it. If the incumbent's word is outside the three legal choices, an eligible replacement cannot spoil a previously exact answer. With a legal incumbent, the guarded policy requires at least two prior wins and zero prior losses for this domain and incumbent word before it switches. A global best-member table, a fixed seeded random member, the designated specialist, a statically typed fallback, and an unguarded neighbor-based chooser provide controls. The two direct classifiers can return a word that no member produced. They predict directly from previous labeled neighbors or select the most likely allowed canonical base token.

Four waves of twelve disjoint questions are ordered by a frozen hash, then scored with one-wave-delayed feedback. Previous questions join future neighbor and support calculations. None of the 48 entered the fitted heads, but all had been publicly studied before this experiment. Everyone uses the same externally checked labels after each full wave. This full-information assumption would require a source of trustworthy feedback in use. The experiment concerns short, closed-set labels; it does not evaluate choosing long-form programs or answers whose correctness depends on external facts.

| Archived four-wave policy | Correct /48 | Newly correct | Earlier successes lost |
| --- | ---: | ---: | ---: |
| Incumbent | 38 | 0 | 0 |
| Latest domain head | 38 | 5 | 5 |
| Most successful head on earlier waves | 38 | 0 | 0 |
| Fixed random member per question | 37 | 0 | 1 |
| Invalid-word repair only | 38 | 0 | 0 |
| Paired feedback guard | 38 | 0 | 0 |
| Nearest earlier label restricted to emitted answers | 40 | 4 | 2 |
| Nearest earlier label directly | 39 | 7 | 6 |
| Base token restricted to declared labels | 39 | 2 | 1 |
| Hindsight over all seven heads | 43 | 5 | 0 |

All six unguarded disagreement proposals in the historical stream failed to earn the two-win allowance before they were served. Their outcome was four helpful switches and two harmful ones. In each release the strict gate used the incumbent word; keeping the old head alone would have reproduced the same historical success. There were no wrong-answer abstentions in this setup; unmatched or unsupported proposals fell back to the incumbent.

## Using a measured quantity to choose a retained answer

A second rule came from a concrete failure in the archival study. An incumbent's word “liquid” could be right at +81 C and wrong at −13 C. Pooling both mistakes and successes under the word alone gave the strict feedback rule too little information. This exploratory chooser parses one temperature or timing quantity and indexes externally labeled past examples by that quantity. It accepts the same label seen at a repeated exact quantity or between surrounding known quantities that carry the same label. It defers on extrapolation, conflict or unsupported phrasing. The parser knows Celsius and time units; all mappings from measured values to output labels come from previous observations. Matched labels can either select an existing member answer or be returned directly as a comparator. [Secondary protocol](quantity-protocol.md) · [Source](quantity.py)

Against the 48 archival questions the quantity chooser reached **42/48**, gaining four and losing zero to the incumbent. Two of its switches recovered engineering unit labels and two recovered water-phase labels. Directly returning the same supported labels delivered **44/48**, gaining six and losing zero; in two engineering cases the archive had no correct word to select. Eighteen of the 48 had usable numeric evidence, including many on which everyone already agreed. The historical analysis influenced this rule. These results are development evidence, and the numerical support assumption can fail outside the examples. The stored heads made four of those correct words available. A direct rule supplied words that were absent from the archive on the other two cases.

The independent 18 did not confirm the quantity chooser's historical gain. Both the quantity chooser and the direct quantity rule scored 15/18, matching the incumbent with zero changes. Only one prompt met its supported numeric conditions; the incumbent was already correct on it. The ordinary wording of physics and timing requests often includes a second number or contextual condition. The primary embedding-based policies covered those cases better. The quantity arm was specified after examining archived mistakes and after receiving access to the confirmation panel's location. It was frozen while fresh extraction was still in progress, before grades were examined; its evidentiary status differs from the primary test. [All numeric qualifications and wave scores](quantity-results.json)

## Reproducing the checks

The experiment needs the repository's Python environment with NumPy. From the repository root:

```sh
P=training/experiments/verified_growth/routing
python "$P/route.py" --panel "$P/fresh.json" --cache "$P/fresh-states.npz" --out /tmp/hive-routing.json
python "$P/measure_quantity.py" --panel "$P/fresh.json" --cache "$P/fresh-states.npz" --out /tmp/hive-quantity.json
python "$P/audit.py" --out /tmp/hive-routing-audit.json
```

Rebuilding the checked-in confirmation cache uses the pinned t80 GGUF and ik_llama.cpp CPU build. Set `MODEL` to the model and `BUILD` to its CMake build directory containing `src/libllama.a` and `ggml/src/libggml.a`. The collector compiles its single-thread extractor and renders each question with the historical 8B system message and the domain's original choice instruction. One original control prompt checks feature agreement and canonical logits against the published archive. The label field is ignored by extraction. The compact cache retains all 4,096 feature components, all editable output-token logits, and the highest untouched token's logit, identity and spelling. These are sufficient for each output-only adapter's exact greedy decision. Native extraction uses one full model per group, while applying each head to a cached state is inexpensive. This study supplies no measured end-to-end generation-speed change.

```sh
python "$P/extract.py" --model "$MODEL" --build "$BUILD" --panel "$P/fresh.json" --out /tmp/hive-routing-states.npz
```
