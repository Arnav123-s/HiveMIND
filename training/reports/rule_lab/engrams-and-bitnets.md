# Can a hive remember and rebuild a neural cell?

The hive rebuilt a 38.04 MiB trained adapter exactly from a 4.26 MiB record and its parent. A 0.465 MiB ternary version retained the child's calibration skill on two sets of fresh problems. In a separate experiment, one small ternary network learned two different jobs from the outputs of two independent networks. The combined network used 560 weight connections and got both decisions right on 91.0% of fresh inputs. The two original networks used 832 connections together and got both right on 96.0%. These results support growing a library of recoverable specialists and consolidating selected skills on CPU. Broad conversation and reasoning remain open targets. [Measurements and scored replies](engrams/measurements.json)

## What a cell could inherit

In neuroscience an **engram** is a lasting physical change caused by an experience that contributes to later recall. A biological cell's DNA and a learned memory trace have different jobs. HiveMIND already uses the word for a particular engineering mechanism. After checked work, it trains a rank-4 ternary LoRA edit on the last eight layers, records the task text, and can activate up to two matching edits alongside a member. Its current lookup uses word-set overlap, requires matching base DNA and skips identical task text. The saved training examples, the backbone, and the software interpreting a patch all contribute information. [Biological definition](https://pubmed.ncbi.nlm.nih.gov/31896692/) · [HiveMIND's writer and lookup](../../../team/engram.py) · [Adapter activation](../../../team/solo.py)

I tried two ways to give your “DNA for a stem cell” idea a precise meaning. A **weight record** describes what to change in a particular ancestor and can reproduce the exact descendant. A **behavioral record** stores examples of what a cell does. A newly trained network can replay that record with a different internal shape. Its fidelity depends on which situations the examples cover. A surviving front half alone cannot determine its lost back half. Many possible back halves accept the same signals and give different answers.

There is a counting limit for exact recovery. Ten three-valued synapses can encode 59,049 states. Two independently chosen sets of ten have more than 3.4 billion possible combinations. The original ten synapses cannot identify every possible pair. Shared ancestry, repeated structure, a side memory, or accepting approximate behavior changes how much the hive has to store.

## 1. Regrow a real 8B hive member

The shared 2.03 GiB Ternary-Bonsai 8B backbone uses packed, group-scaled ternary weights. Its members also carry adapters. This experiment used the real data parent and the CPU-trained affine calibration child from this worktree. The child inherited 196 adapter tensors and changed 28 in the last two transformer blocks. Each archive identifies the parent and backbone by SHA-256. The exact archive preserves changed factor bits and header edits. The three approximate archives encode the differences in the adapter factors as positive and negative bit planes plus scales. Rebuilding applies the differences to the parent's factors before serving the resulting adapter. [Original training experiment](README.md) · [Reconstruction code](../../experiments/engram_regrow.py) · [Backbone representation](../../ternary_base.py)

| Adapter served | Extra archive with ancestors present | Relative error in the learned weight change | Interactive calibration, 4 worlds | Fresh fixed notebooks, 8 worlds |
|---|---:|---:|---:|---:|
| Data parent | — | — | 1/4 | 0/8 |
| Original child / exact rebuild | 4.256 MiB | 0% | 4/4 | 7/8 |
| Ternary, mean absolute weight change per factor | 0.471 MiB | 34.6% | 1/4 | 1/8 |
| Ternary, one fitted scale per factor | **0.465 MiB** | 30.2% | **4/4** | **7/8** |
| Ternary, fitted scale per group within each row | 0.760 MiB | 26.3% | 4/4 | 7/8 |

All interactive arms saw seeds 401–404. Each cell chose its own measurements and used the same tool and feedback allowance. A pass required predicting all eight hidden sensor settings correctly. The fixed notebooks used seeds 421–428, the same four public readings for each arm, and a single reply. The original child ran in the interactive control and its byte-identical rebuild ran in the fixed-notebook control. All five arms scored 0/4 on a harder law containing an interaction term. All also scored 0/4 on strict JSON for four ordinary requests. Allowing Markdown fences recovered correct content on 2/4, inventory and ordering. This is evidence for a learned procedure on one family. [Interactive protocol](../../experiments/rule_lab.py) · [Fixed notebooks and ordinary requests](../../experiments/engram_transfer.py)

The complete child compresses to 31.56 MiB with ordinary DEFLATE. The exact record is 7.4 times smaller even against that baseline. The fitted record contains **487,734 bytes**. It reconstructs FP16 factors for the current server. Its benefit here is disk storage and transfer. All variants still run the 8B backbone and materialize a full adapter. A native packed adapter kernel would need a separate speed and memory benchmark. [Exact record](engrams/affine-exact.zip) · [Fitted ternary record](engrams/affine-fitted.zip)

**Ancestry determines the savings.** I also rebuilt the existing words, code, and second data adapters from the same first data adapter. All three rebuilt exactly. All 196 tensors differed and their records cost 30.39–30.41 MiB each, about 96% of the cost of compressing their full files. A close parent made this child cheap. A hive with many lineages should measure each candidate parent and the full-file alternative before choosing what to retain. Keep reachable ancestors or periodic independent snapshots so the loss of one file can be repaired.

## 2. Replace the missing halves

I trained two independent ternary networks on the same 12 sensor values. Cell A had 24 hidden neurons and decided which of two banks had the larger total. Cell B had 40 hidden neurons and detected opposite polarities on two other channels. Both true answers exist for every input. The test used five independent initializations and datasets, 8,192 training inputs and 4,096 fresh inputs per seed. The table below uses the repository's original BitLinear training rule. Values are average task accuracy. [Half-network experiment](../../experiments/engram_halves.py)

| Repair | Restore A's job | Restore B's job |
|---|---:|---:|
| Own halves and correct wiring | **99.3%** | **90.9%** |
| Other cell's front wired into this back, cut or zero-padded to width | 53.8% | 49.4% |
| Same foreign front, linear connector fitted on 512 unlabeled paired activations | **76.9%** | 49.8% |

I removed **A's front and B's back at the same time**, kept their other halves, then restored each missing part from its own signs, scale and bias. Every restored output logit equaled its pre-removal deployed value on the test inputs, for every seed and all three quantizers. A second control scrambled the order of A's hidden neurons. The raw connection scored 53.3%. Restoring the known order recovered 99.3%. A donor half can be healthy and still speak a different internal language. Here a learned connector helped strongly in one direction and left the other near chance. Its calibration needed signals from both intact encoders, so those observations must be recorded before a permanent loss. The fitted connectors themselves cost about 4 KB each, a real expense at this scale. [Model stitching research](https://arxiv.org/abs/2106.07682)

An explicit one-bit request selecting A or B gave 95.1% accuracy with the original training rule. If the body must give just one binary answer and gets no indication which job is requested, even perfect knowledge is capped at 74.7% on these inputs under equally likely requests. The true answers disagree about half the time. A body can preserve both by providing two outputs, receiving a task cue, or asking for a distinguishing observation.

## 3. Grow one network from memories of two others

This experiment used the fitted-scale teachers. I recorded their two output logits on reproducible inputs and trained a new 40-neuron ternary network with one shared hidden layer and a two-output head. The student saw teacher responses and recovered inputs. Ground-truth test labels were reserved for evaluation. The shipped example includes the input seed, selected indices, input checksum, student seed, Torch version, and FP16 responses. It can grow the student after both teachers have gone. [Distillation experiment](../../experiments/engram_distill.py) · [Runnable two-teacher memory](engrams/two-teachers.npz) · [Knowledge distillation](https://arxiv.org/abs/1503.02531)

| Memory used to grow the student | Balance correct | Polarity correct | Both correct | Both correct near decision boundaries |
|---|---:|---:|---:|---:|
| Both independent teachers, intact | 99.6% | 96.3% | **96.0%** | **80.9%** |
| 64 random examples per teacher | 93.9% | 61.0% | 57.2% | 30.4% |
| 512 random | 97.5% | 85.7% | 83.6% | 44.7% |
| 512 including low-confidence examples | 98.5% | 90.6% | **89.2%** | **55.0%** |
| 4,096 random | 98.6% | 92.3% | **91.0%** | 59.9% |

Each column uses 4,096 new inputs per seed across five seeds. The boundary test puts the bank totals close together and brings one polarity channel close to zero. For the selective 512-example memory, the hive queried 4,096 candidates. It kept 256 ordinary inputs and 128 low-confidence inputs from each teacher. That raised joint accuracy on difficult inputs by **10.3 percentage points** over 512 random examples. The extra teacher queries and the indices have a cost. The selective trace averaged 4.57 KB and the 4,096-example trace averaged 16.52 KB. The two tiny teachers themselves occupied 4.17 KB in four packed layer archives. A behavioral trace can be worth keeping for teaching a different architecture even when saving the original weights is cheaper.

Both answers now come from 560 ternary weight connections per input, against 832 across the two full teachers. The counts exclude biases, scales and activation work. Selecting only one teacher is cheaper for its single task. These experiments use a shared input space, two tasks, and small feed-forward networks. An 8B model absorbing two arbitrary specialists with the same fidelity is a separate experiment.

## 4. Improve the bit networks where learning can adapt

The repository's scratch BitLinear rounds each weight to negative scale, zero or positive scale and rounds its inputs to eight bits. Its original scale is the average absolute value of **all** weights in a layer. The fitted rule alternates two steps. It chooses the nearest of the three levels for each weight and then sets the scale to the mean magnitude of the nonzero assignments. This changes how much room the cell gives its strongest connections. Independent per-row scales add metadata. [BitLinear and its stored format](../../scratch.py) · [Ternary Weight Networks](https://arxiv.org/abs/1605.04711) · [BitNet b1.58](https://arxiv.org/abs/2402.17764)

| Scale used while training new cells | Balance | Polarity | Both correct |
|---|---:|---:|---:|
| Original mean absolute weight | 99.3% | 90.9% | 90.3% |
| One fitted scale per layer | **99.6%** | **96.1%** | **95.7%** |
| One fitted scale per output row | 99.3% | 95.8% | 95.0% |

The comparison used identical initial weights and minibatches for each quantizer within each task and seed. Fitted single-scale polarity accuracy improved in all five seeds. More scales reduced numeric error on the 8B edit but gave the same task scores and cost 63% more bytes there. The small-network tests use PyTorch with rounded weights in floating-point operations. They measure behavior. The 8B tests use the native packed backbone kernel.

**A mature network reacts differently.** I applied the alternative scales after training to the actual checked-in scratch language stem. On 96 freshly generated task prompts from four separate families, the original stem's mean next-token loss was **5.050**. Global fitted scales raised loss to **8.325** and per-row scales raised it to **8.871**. Lower is better. A block-by-block choice made on 64 other prompts kept the original rule in all four blocks. The 2,841 scored test tokens measure prediction of task wording. Templates may have appeared in training. Keep each mature stem's quantization recipe with its weights and evaluate new recipes while growing offspring. [Stem evaluation](../../experiments/engram_stem.py)

## 5. Give the hive a way to recognize which memory applies

In the repository's earlier 32-task engram stream, memory off passed 17 and memory on passed 12. Only eight tasks logged a recall. On those same eight tasks each arm passed six, with one win in each direction. The first round had zero recalls and already differed by one correct answer. Those aggregate scores cannot isolate the effect of recalling an engram. A future stream should replay exactly the same pre-recall state with a real edit, an empty edit, and a plausible wrong edit, then score the final task. [Archived stream](../../experiments/engram_stream_31000.json) · [Original experiment](../../experiments/engram_stream.py)

I compared the real word-overlap lookup with matching **observed outputs** of the two trained cells. The small bank saw 12 requests it could serve and six it could not, repeated with five independently trained pairs. Some prompts used different words for the same operation. Others used identical wording for different jobs. The behavioral lookup received labeled example observations from the current instrument. It activated a cell only if exactly one candidate matched within the error allowance. [Recall experiment and complete request set](../../experiments/engram_recall_probes.py)

| Information available at recall | Correct selection among 60 known requests | Incorrect activation on 30 unsupported requests |
|---|---:|---:|
| Existing word overlap, first returned candidate | 10 | 10 |
| Two observed examples | 37 | 14 |
| Eight observed examples | 55 | 3 |
| Sixteen observed examples | 58 | 0 |

Two examples sometimes made recall worse on unsupported requests. Sixteen supplied useful discrimination in this two-cell bank. Real tasks frequently lack a labeled oracle, and a larger bank has more opportunities for accidental agreement. Use text to shortlist candidates, then check cheap observable behavior when a task supplies it. When no check is available, preserve the uncertainty and let a peer or the user resolve the ambiguous requirement.

## Next experiments for a growing hive

1. **Give each newborn two forms of inheritance.** Keep the cheapest verified weight record for faithful repair and a small teaching set for other architectures. Include counterexamples and the conditions under which the cell's method stops working. Keep membership and reproduction on their own lifecycle. A failed check changes which memory the body uses on that request. A living cell can still explore or contribute a negative example. [Population experiment](hive-growth.md)
2. **Teach cells a shared interface before attempting fusion.** Pick a recurring workflow, such as extracting changed commitments from a conversation and updating a calendar. Record typed inputs, intermediate decisions and final outcomes. Compare direct handoffs, a learned connector, and one distilled student on new conversations with corrections. Score both component skills and the completed update, including requests missing information. A small reserved pathway can carry features that one cell's compressed representation discards. Activation matching and partial merges are further candidates to test. [Model stitching](https://arxiv.org/abs/2106.07682) · [ZipIt!](https://arxiv.org/abs/2305.03053)
3. **Make recovery local and measure growth at a fixed CPU budget.** Grow the archive through 8, 32 and 128 cells while keeping the same number resident. Give small groups local skill indexes and one shared task notebook. Disable the most-used cell mid-task, then remove a common ancestor in a separate trial. Measure completed tasks per CPU-minute, cold-start and recovery latency, RAM, storage including ancestor copies, and rare-skill survival. Test periodic full snapshots against longer delta chains. An unbounded chain makes the descendants depend on every link.
4. **Let hard cases steer consolidation.** Maintain an ordinary replay sample plus examples of disagreement, low confidence and changing requirements. Compare identical archive-byte budgets as well as identical teacher-query budgets. A stable assistant needs a test where learning a new commitment does not erase an older unrelated one. Repeat ten generations, report the worst retained skill and the number of independently solved new tasks, and keep the original specialists available for rare situations. Population size alone cannot tell whether the body became more capable.

## Reproduce the work

Run from this isolated worktree. The pinned CPU server is ik_llama.cpp revision 7aa7e01. The study used a four-core quota and 16 GiB RAM. The model binaries and parent adapter are in the existing rule-lab asset directories. The full repository suite passed 443 tests with one skip, using the cached public t17 tokenizer and one OpenMP thread. I also rebuilt the shipped exact archive and compared the complete file, and replayed the two-teacher archive in a fresh Python process.

```bash
PY=/workspace/HiveMIND/.venv/bin/python
LAB=runs/rule-lab
STUDY="$LAB/engram-study"
PROOF=training/reports/rule_lab/engrams
RT=/workspace/scratch/hivemind-runtime/ik_llama.cpp/build/bin/llama-server
PARENT="$LAB/catalog/t80+g41data.gguf"
BASE="$LAB/assets/base.gguf"

"$PY" -m training.experiments.engram_regrow restore --base "$BASE" --parent "$PARENT" \
  --capsule "$PROOF/affine-exact.zip" --out "$STUDY/replay/exact.gguf"
cmp "$STUDY/replay/exact.gguf" "$LAB/catalog/t80+labchild.gguf"
"$PY" -m training.experiments.engram_regrow build --base "$BASE" --parent "$PARENT" \
  --child "$LAB/catalog/t80+labchild.gguf" --out "$STUDY/rebuilt"
"$PY" -m training.experiments.engram_regrow family --base "$BASE" --parent "$PARENT" \
  --children "$LAB/catalog/t80+g41words.gguf" "$LAB/catalog/t80+g41code.gguf" \
  "$LAB/catalog/t80+g41data2.gguf" --out "$STUDY/replay-family"

for cell in t80+g41data t80+labchild absmean fit groupfit
do
  catalog="$STUDY/rebuilt/catalog"
  case "$cell" in t80+*) catalog="$LAB/catalog" ;; esac
  "$PY" -m training.experiments.rule_lab --binary "$RT" --base "$BASE" --catalog "$catalog" \
    --cells "$cell" "$cell" --seeds 401 402 403 404 --modes open --families affine \
    --out "$STUDY/replay-live/$cell"
done
"$PY" -m training.experiments.engram_transfer --binary "$RT" --base "$BASE" \
  --catalog "$LAB/catalog" --rebuilt "$STUDY/rebuilt/catalog" --out "$STUDY/replay-transfer"
"$PY" -m training.experiments.engram_halves --out "$STUDY/replay-halves.json"
"$PY" -m training.experiments.engram_distill --out "$STUDY/replay-distill"
"$PY" -m training.experiments.engram_recall_probes --out "$STUDY/replay-recall.json"
"$PY" -m training.experiments.engram_stem --out "$STUDY/replay-stem.json"
```

To grow the two-output cell from the shipped behavioral record alone in the same environment, use the following code. The output columns are the bank comparison and the polarity disagreement respectively.

```python
from pathlib import Path
import torch
from training.experiments.engram_distill import replay

torch.set_num_threads(1)
cell = replay(Path("training/reports/rule_lab/engrams/two-teachers.npz").read_bytes())
readings = torch.tensor([[1., 2., 3., 0., 0., 1., -2., 3., 0., 0., 0., 0.]])
with torch.inference_mode():
    decisions = cell(readings) > 0
```
