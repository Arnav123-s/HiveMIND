# What a neural cell can pass to another

The most successful transplant in this study was a relationship between two signals. A second cell recovered a damaged polarity detector from a foreign encoder, a surviving output head, and 512 recorded responses. On five fresh seeds, it selected the same signal pair each time and reached **99.2%** accuracy. The older 1,024-weight connector reached **93.9%**. The study also uncovered a common failure in merging language specialists. Two copies of the very same adapter can cancel completely if their stored factors are averaged in different coordinates. [Repair experiment](../../experiments/engram_output_repair.py) · [Adapter surgery](../../experiments/engram_lora_surgery.py)

## What to put in an engram

In neuroscience, an engram is a physical trace of experience involved in later recall. In this repository, a checked task can produce a small LoRA weight edit. DeepSeek uses **Engram** for another design, a learned memory table retrieved by token sequences and gated by context. These uses point to different engineering choices. An archive can preserve a change, a cue can retrieve it, and the running cell can decide how strongly to apply it. A record of behavior can teach a different architecture even when the original weights cannot be transplanted. [Memory engrams](https://pubmed.ncbi.nlm.nih.gov/31896692/) · [HiveMIND's engram writer](../../../team/engram.py) · [Conditional memory via scalable lookup](https://arxiv.org/abs/2601.07372)

| Representation | What the hive can do with it | What it depends on |
|---|---|---|
| Weight edit or task vector | Reproduce a change relative to a particular ancestor, or compose compatible edits | Base fingerprint, tensor layout, quantizer and coordinate system |
| Activation direction | Steer a running cell or transmit a measured feature for one turn | Layer, normalization, signal convention, recipient and gain |
| Input–output trace | Train a different cell to reproduce observed behavior | Informative examples, especially at decision boundaries |
| A latent code for a shared weight generator | Grow task-specific weights from a short inherited vector | A trained generator, a related family of cells, and the cost of retaining the generator |
| Conditional lookup or executable procedure | Recall a fact or reapply a checked operation with few CPU cycles | A reliable cue, arguments, scope and current task revision |
| A record that refers to other engrams | Reassemble a larger skill from independently replaceable parts | Versioned references, recoverable ancestors and an end-to-end test |

“An engram of the weights” can be a lossless delta. “Weights of the engrams” can mean a router learning how strongly to activate each memory in context. “An engram as a vector” still needs a choice of space. A vector of parameter differences, a vector inside the running network and a vector of responses to standardized probes have different meanings. I would use the response vector for searching across lineages, keep weight edits for known descendants, and retain the original observations for teaching new kinds of cells. Test candidate memories with an intervention. Remove one, transplant it, reverse it or replace it with a scrambled control, then measure the change in the completed task. [Task arithmetic](https://arxiv.org/abs/2212.04089) · [Function vectors](https://arxiv.org/abs/2310.15213) · [Rank-one model editing](https://arxiv.org/abs/2202.05262)

A **hypernetwork** makes your developmental idea literal in software. A shared network reads a cell's vector and emits some of that cell's weights. A strong next test would train one generator on related adapter families, hold out an entire lineage, and compare task recovery against storing the adapter or replaying example outputs. Charge the hive for the generator, the individual codes, and any correction each child still needs. This study tested direct and behavioral repairs. A learned developmental generator remains an experiment. [HyperNetworks](https://arxiv.org/abs/1609.09106)

## Repair the behavior the surviving head reads

I discarded the recipient encoder and used twelve signed channels from a separately trained, differently sized donor. Every repair saw the same 512 saved FP16 recipient logits. The new method considered all twelve channels and all 78 pairwise products. It selected terms by their ability to predict the old responses, chose model size using 128 reserved responses, and refit on all 512. It wrote the recovered scalar into a single active coordinate of the surviving head. No true task labels or recipient hidden activations entered the repair.

| Five confirmation seeds | Balance, ordinary | Balance, boundary | Polarity, ordinary | Polarity, boundary |
|---|---:|---:|---:|---:|
| Intact recipient | 98.5% | 74.7% | 93.8% | 83.5% |
| Original 1,024-weight ternary connector | 98.2% | **71.9%** | 93.9% | 80.4% |
| Dense linear or quadratic fit | 96.2% | 62.9% | 84.5% | 60.9% |
| Select a few useful terms | 98.0% | 68.7% | **99.2%** | **96.5%** |
| Same sparse method fed the original sensors | 97.9% | 67.6% | 99.5% | 96.5% |

The bold polarity results are measured against the simulator's true answers. The compact repair agreed with the intact polarity teacher on 93.8% of ordinary inputs. The simple relationship sometimes corrected the teacher's mistakes. It did not reconstruct the teacher's exact computation. Each seed has 4,096 fresh cases and 4,096 near the decision boundaries. I developed the sparse alternative after observing the dense fit on five earlier seeds, where sparse polarity accuracy was 96.8% ordinary and 89.1% near the boundary.

The successful polarity patch on every confirmation seed stored one feature index and one FP16 coefficient, **three bytes** once the interfaces and decoder exist. The shipped complete donor-front/recipient-head archive is **1,952 bytes**. The median sparse polarity fit took approximately 7 ms, versus 404 ms for the old connector on the same confirmation seeds in this run. A second task needed six terms and retained less of its difficult boundary behavior. This method suits a low-dimensional decision with a structured signal. Rich hidden state and many independent outputs would require additional directions. [Runnable example archive](engrams/polarity-sparse.npz) · [Measurements](construct-measurements.json.gz)

## Weight surgery, activation surgery and interference

For a linear readout with hidden state `h` and weights `W`, adding an input-dependent activation `V A h` produces `W(h + V A h) = (W + W V A)h`. This gives one precise connection between vector surgery and weight surgery. I tested it on the checked-in 192-dimensional BitNet language stem. Across four directory sizes and five assignments each, the largest discrepancy between the two implementations was about 0.0000201 over the entire 4,096-token vocabulary on unrelated prompts. The identity applies at this linear boundary. Intervening earlier, across a nonlinearity or a quantizer, requires a new test. [Code and wording](../../experiments/engram_vector_surgery.py)

I gave two shifts of a fictional service different routing colors for each of 64 named items. At this size, summing independently fitted association edits recalled **34.5%** of the four-way answers. Jointly fitting one edit per shift on canonical names recalled **100%**. One unconditioned edit serving both contradictory assignments got **50.0%**. A named directory also got **100%**. Joint fitting on two full question phrasings per item reached 100% training recall and only **34.8%** on three new phrasings. The known-name result assumes the item and shift have been resolved. It measures associative storage. It gives no comparable evidence for understanding an unnamed concept.

Per shift, the 64-name patch used 3,072 bytes in FP32. Eight-bit row-scaled coefficients used **784 bytes** and retained 100%. A two-plane ternary patch used **208 bytes** and retained **90.8%**. These sizes exclude the shared stem, tokenizer, known-name directory and labels. After a quarter of the mappings changed, sequential rank-one updates correctly changed 45.0% of those entries and preserved 73.5% of the unaffected answers. Recompiling the live records recovered 100% on both. Keeping the patches continuously active also had a cost. Among 128 unrelated prompts, steering the entire hidden vector retained the baseline's top token 39.4% of the time. Editing just the four output rows retained it 81.4%. A task-scoped switch can leave both edits off during ordinary conversation.

A LoRA on the 8B model stores factors `A` and `B` whose effect is proportional to `BA`. Negating both preserves the adapter. Averaging the factors of an adapter and its sign-flipped twin produces zero. I measured all 98 projections of the actual data and words adapters. The error against their intended equal-weight mixture was **53.1%** for factor averaging, and **4.7%** for the best rank-16 approximation to the two effective maps together. The corresponding parent/calibration-child errors were 2.84% and 0.92%. The method uses a small QR and SVD per projection. It can emit a native same-rank GGUF, or the runtime can apply both original adapters at half strength. The absolute angle between two flattened adapter files is a poor measure of what the cells share. [Composition implementation](../../experiments/engram_lora_surgery.py) · [Native task exam](../../experiments/engram_fusion_exam.py)

**The better geometric merge still lost the specialist's skill.** I served two native GGUF mixtures of the calibration child and words member at the original rank. In this pair factor averaging had 53.0% effective-map error and SVD had 4.8%. I also served the exact 50:50 reference by applying both original adapters simultaneously. All three mixtures failed all four fresh calibration worlds. Serving the child alone recovered three. These task scores are the reason I would preserve individually addressable cells after consolidation.

| Real 8B configuration | Calibration worlds passed | Ordinary requests with correct content | Combined |
|---|---:|---:|---:|
| Calibration child | 3/4 | 2/4 | 5/8 |
| Words member | 0/4 | 3/4 | 3/8 |
| Both adapters at half strength | 0/4 | 2/4 | 2/8 |
| Average the factors | 0/4 | 3/4 | 3/8 |
| Compose effective weights and compress | 0/4 | 2/4 | 2/8 |
| Route calibration to child, ordinary to words | **3/4** | **3/4** | **6/8** |

Routing is a paired replay of the appropriate measured call using the public task family. It assumes that family is known. The ordinary requests were four existing retention probes. The content column accepts a single Markdown fence around otherwise correct JSON. Every native arm scored 0/4 on the strict ordinary JSON contract. The mixtures and original members used the same prompts, base, CPU server and grading. Different adapter strengths or task-dependent per-layer gains remain open tests. [Per-projection errors, native replies and routing replay](construct-measurements.json.gz)

## Can one cell lend another a conversational style?

I extracted 35 directions of length 4,096 from the real 8B words member, using twelve pairs of formal and casual utterances expressing the same event. The generator averaged contrastive activations and normalized each layer's direction. I injected the result into layers 10–30 on both the original cell and its data-specialist sibling. Positive and negative gain, a same-norm coordinate scramble, the unmodified model and direct style instructions all received the same prompts. The receipts preserve the actual replies. Two fixed marker lists score visible formality and casualness. A separate check requires the requested day and place and rejects a conflicting weekday or explicit cancellation. This test covers one conversational trait on short confirmation messages. [Extraction and transfer code](../../experiments/hive_persona.py) · [Extracted direction](engrams/formality-direction.gguf) · [Full responses and controls](formality-replies.json) · [Persona vector research](https://www.anthropic.com/research/persona-vectors)

On the sibling's eight messages, the baseline, both signs at gain 1.5, and the scramble each produced **one formal-marked reply, zero casual-marked replies, and eight replies with both facts**. Explicitly requesting the style produced **7/8 formal** or **8/8 casual**, each with both facts retained. Selecting a method on four source-cell prompts chose the simple style instruction in both directions. On the four additional sibling prompts, both selections passed **4/4**.

**Increasing the gain made the neural transplant work on those four appointment prompts.** At +12 the sibling produced four formal-marked replies. At −12 it produced four casual-marked replies. All eight retained both facts. An equally strong, coordinate-scrambled vector yielded one formal-marked reply and zero casual ones. Same-magnitude scrambling matters here because injecting a large unrelated signal can also perturb a model. The gain was selected as a follow-up to the weak 1.5 result.

I froze that gain and changed the topics to a badge code, ticket assignment, approved budget and parcel tracking number. At +12 the cell omitted the locker code and budget amount, preserving the two requested literals on **2/4**. At −12 all four replies contained both literals and casual markers. One assigned the ticket to Jo even though Rowan was the assignee. A second used several sentences. Both the unmodified model and the high-gain scramble retained the literals on 4/4. Literal presence, register and faithful completion must be scored separately.

For a tool-confirmed action I therefore tested a conservative renderer. It accepts a reply if it preserves the complete authoritative proposition and adds an approved style wrapper. Otherwise it renders the proposition from the work order. All eight signed-vector replies needed rendering under this strict rule. The resulting **8/8** retained the assignment or values, used the requested register and fit in one sentence. The ticket reply became “Hey Jo, ticket K427 has been assigned to Rowan.” This result came from the supplied work-order facts and template. It trades freedom to paraphrase for a check that catches reversed roles.

A second successful transplant used behavior as the engram. I took the donor's actual replies to two earlier requests and gave them to the sibling as examples, without telling it the style's name. On four new cases it produced the intended register and both correct facts **4/4 formal and 4/4 casual**. For the same workshop, it wrote “I confirm that the workshop is scheduled for Saturday at Summit.” in one setting and “Hey Sam, the workshop is on Saturday at Summit—see you there!” in the other. The examples required extra prompt tokens. This gives the hive a portable fallback when a transferred neural direction has little observable effect.

## One cell as a neuron or a synapse in a larger hive

Five pairs of small ternary cells each saw two disjoint banks of observations. Each sender produced an eight-bit message. I replaced one sender's message with the message from another example while leaving the receiver and its other input alone. Its output agreed on **every trial** with physically substituting that sender's raw observations and running the whole network again. On cases where the true joint decision changed, reading the substitute signal got **96.4%** right. Ignoring it got **1.1%**. Silencing a sender during ordinary operation reduced joint accuracy from **96.9% to 36.8%**. This is evidence for an extracted signal with a causal role in these two tasks. [Interchange test](../../experiments/hive_interchange.py)

I also let the recipient request two more bits per sender only while the unseen bits could still change a decision. It retained every eight-bit decision on **all 65,536 possible code pairs per reader**, using **7.53 total payload bits on average** in place of 16 on the sampled tasks. It needed 1.88 rounds. With individually framed requests and responses, traffic grew from **20 to 55.3 bytes per task**. For these two channels, the two receiver tables cost 128 KiB in bytes. Batch the refinement requests or use fixed-width local signals when message overhead dominates. Enumerating every joint code scales exponentially with the number of senders, so larger groups need small local readers or different bounds.

Architecturally, a cell with its own state and an output can serve as a **node**. A cell translating another cell's message into a receiver-specific effect can serve as an **edge**. The same specialist can fill either role in different tasks. Give each sub-hive a bounded number of neighbors and a few shared signal meanings. Let uncommon knowledge remain in individually recoverable cells. Route urgent work by measured reliability, while keeping reproduction, rest and survival on the population's own lifecycle. [Earlier sub-hive and outage tests](hive-telepathy.md) · [Population experiment](hive-growth.md)

## Turn a failed conversation into a checked skill

The task was to finish two meeting or pickup records after a user revised a previous instruction. The intake worker committed the first edit to SQLite and exited with code 37 before acknowledging it. A successor read the record and only then received the user's revision. Both neural arms saw the full conversation, opening records, current draft, allowed values and the same opportunity to clarify. A complete pass required both final entries to match, including every unaffected field. Identically worded ambiguous pairs had opposite correct intentions. A lucky guess without asking counted as a failure. The crash was real. The calendar and pickup services were local simulations with atomic receipts. Real external services would need compatible idempotency keys or reconciliation. [Work order and receipt code](../../experiments/hive_commitments.py) · [Paired CPU protocol](../../experiments/hive_commitment_bench.py)

The plain 8B decoder copied the example placeholders `day` and `site` and completed **0/28**. Giving the same model a list of legal transactions and an open-ended fallback completed **1/28**. I then supplied an executable correction vocabulary that could reverse, transfer or copy the first edit, keep parts of it, or request the missing item. This approach used more human domain knowledge. It completed **28/28** on the two development cohorts and **13/14** new phrasings. The rule-based cell asked before applying all six ambiguous intentions across the three cohorts. It also deferred all eight unsupported or conditional requests. The fixture set represents a small two-record language with 13 distinct public transcripts in each cohort. [Executable vocabulary](../../experiments/hive_work_order_rules.py) · [New phrasings and unsupported cases](../../experiments/hive_work_order_replay.py)

After seeing the placeholder failure on the first cohort, I removed the placeholders and restricted native decoding to legal fields and operations. The full-state decoder still completed **0/28**, asking for an item in 26 conversations. The constrained operation selector improved to **6/28**, using 28 model calls and 334 generated tokens. It never asked which item. A seventh output had the right final state by guessing on an ambiguous pair. A correct candidate was present in 23 menus, so poor selection was a larger problem than menu coverage. The executable interpreter used zero model calls and averaged **40 microseconds of warm CPU time per request** over 4,200 replays, excluding storage, worker startup and user wait. End-to-end server timings are retained in the traces. Other experiments shared the four-core quota during parts of those runs.

The new wording it missed was “Trade the venues between the two reservations.” I gave it a different, checked example in which two sites exchanged places. Comparing the before and after records identified a field exchange and bound the new verb to the existing operation. The learned record repaired the missed conversation, made **six more exchanges** across dates and locations, and deferred **four** conditional or ambiguous requests. The verb and the choice of the known operation came from one demonstration. The field schema and operation itself were already implemented. This is a practical way for a growing hive to turn a checked correction into a reusable capability. It also leaves a trace a different cell can inspect or revoke. [Work-order evidence](work-order-traces.json.gz)

## Repair a bad reinforcement signal

I replayed the previous two-skill body on 24 new streams of 1,024 tasks. Each stream changed and later restored local duties. One verifier at a randomly chosen affected station always credited a favored worker. Every policy had exactly **128** independent outcome checks and received its feedback eight turns late. Trusting the primary reported **100%** success at that station after duties returned. Actual success was **48.8%**. Simply substituting the occasional audit left that outcome at 48.8%. Excluding unverified feedback from a station after an observed contradiction and directing later audits there reached **76.3%**, with the same budget. Overall task success rose from 87.1% to 88.8%. [Audit and routing experiment](../../experiments/hive_reward_audits.py)

When independent audits themselves flipped 3% of outcomes, a single contradiction became a poor reason to distrust a station. Accumulating evidence across audits reduced the mean number of healthy stations flagged from **0.92 to 0.08** per stream in the double-fault condition. Fault-site success was **63.9%**, compared with 61.8% for acting on the first mismatch and 48.8% for trusting the primary. Track whether an outcome can actually be checked independently, bind it to the worker and revision that acted, and spend extra checks where evidence disagrees. The synthetic fault still left substantial headroom. Independent ground truth on open-ended conversations remains a separate requirement.

## Experiments to run over successive generations

1. **Give a working cell a portable construct record.** Store the cue, layer or tool interface, gain, positive examples, near misses, and a counterfactual outcome. Have another lineage receive it. Score correct transfer, ordinary behavior when the cue is absent, and the number of examples a new recipient needs. Let a failed transplant retire the connection for that job while the donor continues its life.
2. **Keep a notebook of independent successful changes and periodically compile them.** Use cheap receipts for new facts and procedures, scoped neural directions for repeatable preferences, and a new adapter only when the task benefits from practice. Compare eight successive writes with eight independent memories plus a joint refit at equal bytes. Track the worst retained skill as well as the average. Retain a reversible version until the new one passes.
3. **Grow regional groups under a fixed CPU and message budget.** Try 8, 32 and 128 archived cells with the same resident compute. Let neighboring cells exchange a cheap signal, fetch its evidence when a decision is close, and take over a committed work order after an outage. Count completed novel tasks per CPU-minute, unanswered requests, stale actions, message bytes including headers, and the rarest skill that survives. For long-running reinforcement learning, occasionally check the final user-visible outcome with an independent verifier before increasing a memory's influence. The prior reward experiment shows why the primary verifier alone is insufficient. [Continual reward experiment](continual-learning-and-speed.md)

## Reproduce the experiments

Use this branch and the assets from the [original CPU study](README.md#running-the-experiment-again). The 8B tests use the pinned ik_llama.cpp server and its standard `llama-cvector-generator` target. Use a fresh output directory. The extracted formality direction and the small cross-cell polarity repair can be downloaded separately. The 8B mixtures can be recreated from the words adapter and the calibration child. The child can itself be rebuilt with the `engram_regrow restore` command from the data parent, matching base and [exact child archive](engrams/affine-exact.zip).

```bash
PY=/workspace/HiveMIND/.venv/bin/python
RT=/workspace/scratch/hivemind-runtime/ik_llama.cpp
LAB=runs/rule-lab
OUT="$LAB/construct-replay"
CPU=(--binary "$RT/build/bin/llama-server" --base "$LAB/assets/base.gguf")
CAT=(--catalog "$LAB/catalog")
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

"$PY" -m training.experiments.engram_output_repair --out "$OUT/repair.json" --example "$OUT/polarity.npz" \
  --seeds 263 277 293 307 331 347 359 373 389 401
"$PY" -m training.experiments.engram_vector_surgery --out "$OUT/vectors.json"
"$PY" -m training.experiments.hive_interchange --out "$OUT/interchange.json"
"$PY" -m training.experiments.hive_reward_audits --memory training/reports/rule_lab/engrams/two-teachers.npz \
  --out "$OUT/audits.json"
"$PY" -m training.experiments.engram_lora_surgery "${CAT[@]}" --out "$OUT/weights.json" --build-catalog "$OUT/mixtures"
"$PY" -m training.experiments.engram_fusion_exam "${CPU[@]}" --catalog "$OUT/mixtures" --out "$OUT/fusion"
"$PY" -m training.experiments.hive_commitment_bench "${CPU[@]}" "${CAT[@]}" --out "$OUT/plain"
"$PY" -m training.experiments.hive_commitment_bench "${CPU[@]}" "${CAT[@]}" --out "$OUT/constrained" --constrained
"$PY" -m training.experiments.hive_work_order_replay --out "$OUT/executable"
"$PY" -m training.experiments.hive_persona extract --generator "$RT/build/bin/llama-cvector-generator" \
  --base "$LAB/assets/base.gguf" "${CAT[@]}" --out "$OUT/formality"
"$PY" -m training.experiments.hive_persona grade "${CPU[@]}" "${CAT[@]}" --out "$OUT/formality"
"$PY" -m training.experiments.hive_persona examples "${CPU[@]}" "${CAT[@]}" --out "$OUT/formality"
"$PY" -m training.experiments.hive_persona stress "${CPU[@]}" "${CAT[@]}" --out "$OUT/formality"
"$PY" -m training.experiments.hive_persona confirm "${CPU[@]}" "${CAT[@]}" --out "$OUT/formality"
"$PY" -m training.experiments.hive_persona verify --out "$OUT/formality"
```

To replay the small repair without its teachers, pass the bytes of [polarity-sparse.npz](engrams/polarity-sparse.npz) to `training.experiments.engram_output_repair.restore`. Its returned function accepts a tensor with twelve input columns.

The full repository suite passed **459 tests with one skip** in 4m 20s after the native inference jobs finished. With two inference servers sharing the quota, an earlier run's time-limited training test completed two updates and missed its four-update minimum. The isolated rerun passed that test. I also loaded the shipped polarity archive in a fresh process and reproduced its ordinary and boundary scores without either original teacher.
