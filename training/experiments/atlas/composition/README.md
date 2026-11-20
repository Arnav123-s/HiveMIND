# Can three learned factors produce a code the model never saw?

**All seven native configurations scored 0/6 on the unseen combinations.** On the remaining 12 prompts, combining all three factors scored 4/12, the same as the single joint head and the format head alone. All 18 inputs have new wording and numbers. A direct implementation of the supplied three-bit codebook returns all 18 codes correctly. [Frozen protocol](protocol.md) · [Exact training and evaluation panel](run.py) · [Native outputs](results.json)

| Actual 8B CPU configuration | Familiar combinations, /12 | Unseen combinations, /6 |
|---|---:|---:|
| Base | 0 | 0 |
| Joint rank-four head trained on full codes | 4 | 0 |
| Source head | 2 | 0 |
| Threshold head | 3 | 0 |
| Format head | 4 | 0 |
| Three heads, one-third scale each | 4 | 0 |
| Three heads, full scale each | 4 | 0 |

The service code starts at A. A mirror port adds four letters, a queue of eight or more samples adds two, and a current form adds one. Calibration uses 18 examples spanning six of the eight combinations. The factor heads have a human-supplied mapping from each bit to the output letters, including the two letters missing from training. The joint head learns from observed labels. The native server returns one greedy token over the entire vocabulary. The grader compares the stripped token to the required capital letter. This is a small conditional-label experiment. It has no multi-step planning, free-text rendering or learned layer-band specialization.

The source head returned C on all 18 prompts. No configuration emitted E, F, G or H anywhere, so every mirror-port input failed. Under full-strength composition the three unseen H cases all became D, which preserves the threshold and form bits and misses the port bit.

The original HTTP run returned six complete seven-arm rows before its transport stopped responding while the server reported an idle slot. We saved all six, checksum-verified the four already fitted GGUFs, then continued using the same CPU executable and request settings. Every continuation request set four LoRA scales, read back all four, and decoded on a graph-reuse-disabled native server with two threads. The continuation records each arm separately and retries transport failures on a fresh owned server. We retained the original six first observations for the primary score and re-read their 42 tokens for comparison. All 42 were identical. Across the continuation and duplicate check there were 126 successful one-token decodes, six recorded timeout attempts and 568.4 seconds summed across probes including timeout waits. Exact fitting wall time was lost when the original run stopped. [Original stdout](interrupted.log) · [All individual readbacks with scales, usage and elapsed time](readbacks.jsonl) · [Fitted GGUFs, compressed](weights.zip)

## Does top-two routing help the existing domain heads?

We applied Arrow's top-two selection to the model's **archived held-out output-layer states** in a separate historical replay. These 18 questions cover six trained domain heads. For each actual FP16 LoRA update, the first right singular vector supplies its routing direction. The absolute dot product with the last-token state ranks the experts. A softmax over the two highest scores sets their weights. No calibration on the 18 labels was used. Two primary heads in this historical library later failed their shipment gate. [Routing protocol](routing-protocol.md) · [Arrow, Algorithm 2](https://arxiv.org/html/2405.11157v1) · [Original domain study](../../../reports/domain-engrams/README.md)

| First-token policy | Correct labels allowing case and whitespace, /18 | Exact target token ID, /18 |
|---|---:|---:|
| Base | 14 | 4 |
| Equal mean of six heads | 14 | 4 |
| Arrow top two | 15 | 6 |
| Single intended domain head given by the evaluator | 15 | 9 |

Arrow included the intended head in **11/18** shortlists and ranked it first on **7/18**. It rescued one appointment response, changing “Thank” to “confirm”. It also changed the capitalization of one already-correct answer. There were no new incorrect normalized labels. The paired base and intended-head argmax matched all 36 previously recorded native token IDs. The replay preserves the highest outside-vocabulary competitor and every vocabulary row the six LoRAs can alter, which suffices to reconstruct the unrestricted argmax. These are numerical counterfactuals from actual native activations and weights. They measure neither HTTP serving speed nor multilayer routing in a running network. [Input provenance](arrow-inputs.json) · [Per-case scores, projections and mixtures](arrow-results.json)

## Transformer blocks and residual steering

We opened the released G49 code, data and trunk GGUFs. Each contains 196 LoRA tensors, spanning the same seven projections in every transformer block from 22 through 35. Code and data use rank 16, trunk uses rank 32. Every pair has 14 shared blocks out of 14 in the union. The four composition-trial fits above update only the final output projection. No disjoint-band treatment was measured on either set. Restricting the existing G49 adapters to different blocks would discard part of each learned update. A controlled test would need predeclared matched-capacity overlapping and disjoint treatments, plus held-out isolated-skill and joint-skill cases. [Block inventory](bands.json) · [G49 release](https://github.com/Arnav123-s/HiveMIND/releases/tag/hive-grown)

Contrastive Activation Addition learns a residual direction from paired examples of a behavior and adds it during generation. None of these LoRAs is a verification steering vector. The pinned native server supports loading a control vector with a scale and layer range, but none was applied in either composition trial. The separate Atlas steering study addresses that question. [Steering experiment](../steering/protocol.md) · [CAA paper](https://aclanthology.org/2024.acl-long.828/) · [Pinned runtime source](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/examples/server/server.cpp)

## Reproduce

From this directory, supply the pinned T80 model and llama-server executable identified by SHA-256 in the result. This example starts a fresh native score of all 126 arms. Reusing the same checkpoint resumes an interrupted replay.

```sh
work=$(mktemp -d)
unzip -q weights.zip -d "$work/weights"
touch "$work/no-original-rows"
python resume.py --model "$HIVE_MODEL" --runtime "$HIVE_LLAMA_SERVER" \
  --weights "$work/weights" --original "$work/no-original-rows" \
  --checkpoint "$work/readbacks.jsonl" --out "$work/composition.json"
OPENBLAS_NUM_THREADS=1 python arrow.py --out "$work/routing.json"
```

For the primary hybrid score, omit `--original` to retain the six archived rows alongside new readbacks. The separate routing replay requires NumPy and reads the bundled compressed sufficient logits and states. The original fitting script and primary protocol stay intact. [Native continuation](resume.py) · [Routing replay and packaging](arrow.py) · [Release inventory reader](bands.py)
