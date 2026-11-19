# CPU-trained domain engrams

These edits each target one small decision on the Ternary-Bonsai-8B body. The coding edit distinguishes mapping, filtering and summing a collection. The other five concern geometric measures, pure-water phase at one atmosphere, a next conversational move, a machine learning dataset split, and hardware timing units.

## What was fitted

[The exercises](exercises.json) contain six fitting questions and three separate qualification questions per decision, balanced across three labels. A human wrote both sets before feature collection. The six edits share a frozen 8B ternary backbone. Each edit is a 1,246,560-byte GGUF with FP16 low-rank factors on the **output projection**. The stored rank is four. Each task uses three nonzero output-label rows and has effective rank three.

The native tokenizer rendered each question with its task instruction and [the ordinary HiveMIND system message](system.txt). The trainer extracted the final 4,096-dimensional hidden state and fit a regularized least-squares map to three incremental token scores. The desired increment was 6 for the correct label and 0 for the others. The ridge factor was 0.10. The trainer froze these settings before running qualification. All six fits used CPU inference with a two-thread limit. [Trainer](../../domain_engram.py) · [Native feature extractor](../../domain_features.cpp)

The release gate required **three correct adapted predictions out of three and zero baseline regressions**. The native evaluator decoded the first unrestricted, greedy assistant token with the base alone and with the corresponding actual GGUF loaded at scale 1. Case and surrounding whitespace were folded for scoring. The evaluator reused an identical prefix and recomputed the final token with the loaded edit. An output-only edit leaves the model's key/value cache unchanged. Exact-token probabilities refer to the lowercase reference token, so a probability shift can reflect a change of capitalization. A tie establishes neither a new answer nor a capability gain.

## Primary results

| Scoped decision | Bare body | Loaded edit | Released in v1 |
| --- | ---: | ---: | --- |
| Python operation | 3/3 | 3/3 | Yes |
| Geometric measure | 3/3 | 3/3 | Yes |
| Water phase | 2/3 | 2/3 | No |
| Next conversation move | 2/3 | 3/3 | Yes |
| Dataset split | 3/3 | 3/3 | Yes |
| Hardware timing unit | 1/3 | 1/3 | No |
| **Total** | **14/18** | **15/18** | **4 of 6** |

There was one semantic gain and zero regressions. When a client had agreed to Thursday at three, the unedited first token was “Thank” and the edited first token was “confirm.” Both versions called pure water at −13 °C liquid. Both missed the unit corresponding to 1,000 nanoseconds and the unit corresponding to 1,000 microseconds. The release excluded the two edits with these failures. [All cases and observed first tokens](results.json) · [Frozen primary index](primary-index.jsonl)

A secondary check measured the weight edit's contribution to each of its three token scores. The expected label received the largest increase on **15/18** held-out questions. Always choosing one fixed label per domain gives 6/18 on this balanced set. This measures how the learned head responds to the question. The answer-level improvement is the single corrected result above. Graph-safe ordinary HTTP independently reproduced the appointment result as unedited “Thank,” edited “confirm,” and unedited “Thank” again. [Paired native logits](output-shifts.json)

For all 18 original checks, adding the released FP16 factors' full-vocabulary increment to independently collected base logits recovered the observed native adapted argmax. It also recovered all 18 when starting from the paired native OFF logits. [Full-vocabulary numerical control](primary-native-control.json)

## Corrective studies and release

The final index contains **five** checked weight edits, occupying 6,232,800 bytes beside one shared model. Its SHA-256 is `b87088bdf5727f14e68b93c05952c09367944ae168f7bfb9935dbc805f892ed9`. The water-phase correction became the fifth entry. Its 27 public teaching examples comprised the first nine released rows and 18 new, balanced examples. The independent author sealed nine new questions before the writer froze the candidate. All nine temperatures and all nine phrasings were absent from the teaching set.

| Water phase | Bare body | First edit | Corrective edit |
| --- | ---: | ---: | ---: |
| Original three, now included in teaching | 2/3 | 2/3 | 3/3 |
| Six independent primary questions | 2/6 | 4/6 | 6/6 |
| Three independent supplementary questions | 2/3 | 2/3 | 3/3 |

After the direct native comparison, the actual graph-safe HTTP generator answered **all 12/12** with the corrective edit. The original −13 °C question illustrates a difference between evaluation paths. Under prefix reuse in the direct native test the first edit returned “Liquid” and the corrective edit returned “Solid.” On the separately observed full HTTP prompt, the initial and corrective edits both returned the correct state with different capitalization. The new edit passed both paths. [Direct native records](water-v2/qualification.json) · [HTTP records](water-v2/serving-qualification.json) · [Release decision](water-v2/release.json)

The hardware timing correction also used 27 public examples. It corrected both old conversion errors, raising the original score from 1/3 to 3/3. On the six independently written questions, the bare body and first edit each scored 2/6, and the correction scored 3/6. Three incorrect conversions kept that weight out of the final store. [Direct native records](timing-v2/qualification.json) · [Release decision](timing-v2/release.json)

Both experiments fixed the weight bytes before receiving fresh questions and used one corrective candidate per subject. The numerical gates apply to three-label decisions under the specified conditions. [Correction protocol](correction-protocol.md) · [Final shipped index](../../../cells/engrams/index.jsonl)

## Reproduce

The release archives the 36 public training-state vectors and native token IDs. The first command rebuilds all six candidates without needing the 8B model. Compare the printed SHA-256 digests with the fit records. The second command extracts the states again and runs a paired serving cross-check through the native HTTP interface. Full-prompt HTTP prefill and direct native prefix reuse can produce different first tokens on the same question. The primary table reports direct native scores. Use an environment with NumPy and the repository's Python dependencies. Cross-platform linear algebra and native quantized kernels can differ in floating-point rounding.

```bash
OPENBLAS_NUM_THREADS=1 python training/reports/domain-engrams/rebuild.py --out /tmp/hive-domain-rebuild
OPENBLAS_NUM_THREADS=1 python training/reports/domain-engrams/rebuild.py --extract --check \
  --model /path/to/Ternary-Bonsai-8B-PQ2_0.gguf --runtime /path/to/llama-server \
  --threads 2 --out /tmp/hive-domain-native
```

The evaluated CPU base SHA-256 was `1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922`. The server was built from `ik_llama.cpp` revision `7aa7e01482db892b023bb9aace9a40567ab5297a` and had SHA-256 `0dc642d61dc39d51a8b5da348c43ba19d29f720b2a3ac790e0019351239da3b2`.

For the corrective studies, rebuild the new edit from its own 27 training states, then replay the exact original and independent questions with the compiled native comparison. The reporter checks the panel, base and candidate digests before replay.

```bash
OPENBLAS_NUM_THREADS=1 python training/reports/domain-engrams/correction.py \
  training/reports/domain-engrams/water-v2 --out /tmp/hive-water-v2.gguf
python training/reports/domain-engrams/qualify_corrective.py water-v2 \
  --panel training/reports/domain-engrams/physics-retention/panel.json \
  --model /path/to/Ternary-Bonsai-8B-PQ2_0.gguf --runtime /path/to/llama-server \
  --v1 /tmp/hive-domain-rebuild/t80+e_domain_physical_science.gguf \
  --v2 /tmp/hive-water-v2.gguf --out /tmp/hive-water-qualification.json
```

The initial corrective judge discovered a graph-cache issue in the pinned native engine. On consecutive same-shape one-token decodes, changing LoRA weights could reuse the previous edit's compute graph. The initial water diagnostic was stopped and excluded from every score. The corrected judge disables graph reuse and checks that switching from the original edit to the corrective edit and back restores the original token on every question. Each candidate also needs a graph-safe HTTP serving confirmation before it can enter the distributed index. [Invalid diagnostic rows](water-v2/invalid-graph-cache.tsv)

The timing replay uses `timing-v2`, `timing-retention/panel.json` and the original `t80+e_domain_computer_engineering.gguf`. A static build of the pinned native engine supplies the C++ comparison libraries. [Prospective protocol](correction-protocol.md) · [Independent commitments](correction-commitments.md)

## Serving replay

The [12 integration prompts](chat-cases.json) cover one open question and one explicit label-choice question per domain. These are public development examples. Their early routing behavior informed a change to the scope recognizer. The separately authored [practical answer panel](../domain-memory/answers/) evaluates broader transfer.

[The runner](serve.py) calls the regular chat interface, reads live adapter scales from the native server before every model call, and records the resulting text. The normal TALK/WORK decision stays active. The runner uses a dedicated local port, a 48-token final answer budget and a recorded sampling seed per call. The primary integration observations used one CPU thread. Each launch logs its thread setting. If it enters WORK, it requests two initial members, permits the ordinary third-member tie-break, and limits each draft to one 80-token turn. Use a normal t80 installation with member adapters available.

```bash
python training/reports/domain-engrams/serve.py --out /tmp/hive-domain-serve
```


The initial [Python](serving-primary/coding-open.json) and [geometry](serving-primary/math-open.json) receipts exposed an integration error. A verified adapter was active at scale 1 and produced the right first word in both cases. Its eight-token internal response continued with an explanation, so the original verifier rejected both. The ordinary answers then returned a working list comprehension instead of the requested Python built-in, and correctly identified volume. These two observed cases informed a change to the serving call's token budget. The initial replay stopped during a third request when concurrent jobs reached the machine's memory budget. It produced two complete receipts.


### User-facing results with the final five-edit bank

The frozen G49 integration replay used the trunk, coding and data cells from the released body on production source `cf7729c`. The machine ran all 12 ordinary messages through `talk.reply` on CPU. The answers gave the correct content on **9/12**, comprising **4/6 open questions** and **5/6 explicit choices**. Only **3/6** explicit choices produced both the correct decision and the requested single label. These public examples had informed routing development, so they measure this integration path. The replay made 39 native calls. Four requests went through the program-writing workers. All five shipped edits activated at least once, across eight requests. [Environment and member fingerprints](serving-final/environment.json) · [Rubric](serving-final/rubric.md) · [All judgments](serving-final/judgments.json)

| Domain | Ordinary open request | Explicit choice |
| --- | --- | --- |
| Python | The edit correctly advised `filter`, but the final answer recommended a list comprehension instead of the requested built-in. | Returned `filter`. |
| Geometry | Correctly identified volume. | Returned `volume`. |
| Pure water | The edited advisory's first token was “At” and was rejected. Two workers printed the false statement that water at 72 °C and one atmosphere is gas. The final reply reported that the programs agreed. | Correctly identified liquid but added an unrequested explanation of worker agreement. |
| Conversation | Gave a usable expression of thanks. | Returned `Thank`. |
| Machine learning | Named the validation split. Its explanation overstated the protection against evaluation bias when tuning. | Correctly returned validation but added a second paragraph. |
| Computer engineering | Correctly identified a microsecond and µs, with no timing edit installed. | Returned `ns` for a millionth of a second. |

The smoke test captured native scales separately from user-visible quality. A specialist can activate without producing a usable label, and the final generator can ignore a correct internal suggestion. Agreement between two programs that print an assertion does not check the underlying physics. The [unmodified open-water trace](serving-final/physics-open.json) remains in the 9/12 total. A separate replay on the corrected application returned “The water is liquid.” The activated edit again emitted “At,” and the deterministic equilibrium checker supplied the factual answer. [Post-fix comparison](../domain-memory/current-body/water-replay/comparison.json)
