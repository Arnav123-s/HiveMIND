# What the CPU hive learned

The field-work study tests whether the hive finishes unfamiliar scientific, programming and multi-step jobs. It includes frozen programs, reopened output files, external observations and a prospective monthly CO₂ forecast. [Field-work results](field-work.md) · [Run a complete job on a CPU](fieldwork/reproduce.md)

The long-term research plan starts from a failure shared by five writers. It tests whether a 7B cell can change strategy after seeing evidence, then lays out how to measure growth on unfamiliar whole jobs at a fixed CPU budget. [Learning new strategies](learning-new-strategies.md)

The scale study grew the population to **4,096 distinct learned ternary cells on one CPU core**. It measures when sub-hives should search locally, how two newborns can learn complementary skills, and how surviving cells can rebuild a missing specialist. A separate work-order trial and a faster production engram index connect the numeric experiments to the working hive. [Scaling the hive](scaling-the-hive.md) · [Runnable colonies](engrams/scaled-colonies.zip)

A new 38.0 MiB adapter learned a calibration procedure that the original data and code cells repeatedly failed to execute. The child completed all four fresh affine worlds from its weights, with an average of 15.0 seconds and two model calls per world. The original open pair completed zero, averaging 47.2 seconds and six calls. I would give the learned child a narrow specialist role. Its measurements transferred to the harder family, where its choice of a helper became the limiting step.

I ran the experiment on the existing g41 HiveMIND base in a separate Git worktree. Each cell could request measurements from a local simulator, hand ownership of a shared notebook to a peer, or submit coefficients. Each world advertised its equation family but hid its coefficients. A pass required the correct prediction at all eight private settings, all outside the allowed measurement grid. Six turns and four or five measurements were available to every arm. No remote model generated answers or judged them. [Experimental design](design.md) · [Measurements](results.json) · [Turn-by-turn transcripts](traces.jsonl.gz)

The follow-up rebuilt this child from its parent, tested sub-megabyte ternary records on new problems, and grew one small network from the memories of two specialists. [Engrams, reconstruction and BitNet results](engrams-and-bitnets.md)

The inference and learning study measures CPU time on the real 8B server and scratch stem, checks two custom integer kernels, and follows a routing policy through changing goals and delayed rewards. [Continual learning and inference speed](continual-learning-and-speed.md)

Two cells also learned to cooperate from separate inputs through a one-byte channel each. The communication study includes a runnable pair, incompatible signal conventions, late messages and a 1,024-cell sub-hive simulation. [Hive telepathy and sub-hives](hive-telepathy.md)

The construct study tests what can pass between cells as a neural signal, a weight edit, a style direction or an executable memory. It includes real 8B adapter mixtures, a three-byte polarity repair, and work orders that survive a worker dying after a write. [Constructs, surgery and conversation outcomes](constructs-and-surgery.md)

## The fixed comparison

Four affine worlds and four interaction worlds were shared by all seven configurations. An affine sensor adds separate contributions from x and y. The harder sensor also multiplies x by y and an unknown coefficient. Seconds are mean end-to-end time summed over the turns of one world, including adapter loads when they occurred.

| Configuration | Affine success | Interaction success | Seconds per affine world | Seconds per interaction world |
| --- | ---: | ---: | ---: | ---: |
| Data parent alone | 0/4 | 0/4 | 47.0 | 41.8 |
| Data and code parents, free handoff | 0/4 | 0/4 | 47.2 | 45.6 |
| Data and code parents, assigned roles | 0/4 | 0/4 | 52.0 | 43.4 |
| Same data weights in both roles, free handoff | 0/4 | 0/4 | 45.6 | 40.8 |
| Original pair with a written procedure | 2/4 | 0/4 | 42.2 | 58.1 |
| Trained child starts, free handoff | 4/4 | 0/4 | 15.0 | 47.8 |
| Data parent plus exact arithmetic worker | 4/4 | 0/4 | 6.3 | 41.3 |

On all four affine tests the child chose to keep the work, requested four measurements, and produced expressions that the common bounded calculator evaluated. On all four interaction tests it collected five measurements that uniquely determined the answer, then delegated to the original code cell. That peer failed all four. In world 101, the data implied coefficients `[4,-4,4,2]`. The peer submitted `[4,2,2,2]` five times despite a public counterexample. The original parents could acquire adequate affine evidence on the first turn as well. Repeated guesses consumed the remaining budget.

The untrained parents also ran into an interface failure on every interaction world. For example, the first reply nested both a valid list of four coordinates and a routing label inside `measure`. The original parser rejected the whole request, leaving even the exact worker with zero observations. I corrected the parser to recognize that specific envelope, retain its coordinates, and prefer the explicit outer routing field. Budget, bounds and duplicate checks still apply.

I tested the correction on four further interaction worlds, seeds 211 through 214. The parent with the corrected parser and exact worker passed **4/4**. With the same corrected parser, the two language-model parents passed **0/4**. The trained child with the original parser and exact worker passed **4/4**. These are live follow-up runs on new coefficients. An ordinary fixed-corner routine also solved all eight original worlds with the exact worker. The solver received only the public probes and the announced feature family. [One full calibration](example.json)

## What the cells learned

The first data cell repeatedly chose the four corners of a unit square. In the first teaching run, the code cell recovered the correct affine rule in one of six worlds. With expression support and public consistency feedback, the guided pair finished zero of six. Several changes to the interface occurred together, so that difference cannot isolate the effect of feedback.

The code cell also failed five attempts to write a reusable affine procedure. I supplied a search over short sums and differences. It inferred the expected coefficients from the six public measurement notebooks with an exact linear solver, then chose short expressions that matched every notebook. In the order (0,0), (0,1), (1,0), (1,1), it found `c = r0`, `a = r3 - r1` and `b = r3 - r2`. The first difference changes only x. The second changes only y. Each cancels the common offset. The stored procedure passed all 512 coefficient combinations in the simulator at all eight withheld settings. A fixed-corner arithmetic control passed all 4,096 interaction combinations. Those sweeps ran executable procedures, with zero language-model calls. [Reusable procedure](affine-procedure.json)

I used the checked procedure to produce seven training rows for a child of `g41data`. One row requests the measurements and six apply the expressions to different public notebooks. The child inherited 196 adapter tensors. All 196 source tensors matched the deployed parent after casting to its inference precision. Training updated 2,424,832 parameters in the last two transformer blocks. I verified that exactly 28 deployed tensors differed from the parent. Three CPU epochs took 293 seconds, peaked at 9.60 GiB of trainer RSS and reduced mean training loss from 1.35 to 0.16. The held-out scores above measure how much of that work reached the user.

## What happens when the world changes

I also ran a separate controller that receives no family label. It executes the stored procedure, takes one independent confirmation at (2,1), and tries the broader interaction model when a measurement disagrees. It saw four fresh sensors in each condition, using five measurements per sensor.

| Hidden change | Controller's behavior | Result |
| --- | --- | --- |
| New affine coefficients | Reused the stored procedure | 4/4 complete calibrations |
| Added an x-by-y interaction | Switched to the exact interaction worker | 4/4 complete calibrations |
| Added a quadratic term outside the two supported families | Reported insufficient model coverage | Abstained in 4/4 |
| Added a cubic term invisible everywhere it could probe | Accepted the affine result | 0/4 complete calibrations, two of eight private settings correct each time |

The last case adds `x*(x-1)*(x-2)`, which vanishes at all three permitted x values. Even a perfect checker of the shared notebook cannot distinguish the two worlds. A hive expected to discover new rules needs independent checks or permission to collect evidence where competing explanations make different predictions.

The same checked controller accepts a callable sensor. The example below triggers the change check and recovers all four coefficients.

```python
import json
from pathlib import Path
from training.experiments.rule_lab_recipe import calibrate

recipe = json.loads(Path("training/reports/rule_lab/affine-procedure.json").read_text())
receipt = calibrate(recipe, lambda x, y: 1 + 2*x - 3*y + 4*x*y)
assert receipt["coefficients"] == [1, 2, -3, 4]
```

## CPU footprint, recovery and ordinary tasks

The machine was a Xeon Platinum 8573C with a four-core quota and 16 GiB memory limit. Inference used one sequential private worker, one 2.03 GiB packed 8B base, and a cache limited to two adapter files. The largest observed main-run server RSS was 2.92 GiB. The local catalog held 26 entries including the trunk and the new child. I requested three distinct adapters in six short calls. Warm switches plus a short reply took about one second. Calls that had to rebuild the private server with a new resident set took 4.8–6.3 seconds. This runtime reopens the base on a miss. The worktree also retains about 15.3 GiB of unpacked weights for retraining.

In a separate run I killed the actual private worker immediately after the parent recorded four measurements. A fresh process reopened the notebook, and the trained child completed all eight predictions in one reply with zero repeated probes. I killed the worker again and the inference client automatically replaced it and answered the pending request. These tests cover process loss and notebook recovery. I supplied the parser repair, the solver, and the training pipeline. The outer experiment launcher also needed a relaunch between completed benchmark batches.

On four ordinary tasks the parent and child each scored 0/4 under strict JSON scoring. After stripping Markdown fences, both had exactly correct fields on 2/4, inventory and ordering. Both remembered the corrected day and room but returned “Cedar room” where the requested bare name was “Cedar”. Both incorrectly requested the booking date and time again. These eight short responses showed the same pattern before and after training. A general conversation evaluation is still open.

## What I would build next

1. **Change worker after a repeated failure.** Record the proposed answer, the contradicting observation and which worker produced it. If the same candidate returns against the same evidence, request new evidence or send the notebook to a worker with a different method. World 101 already had enough information for a correct answer on the first turn.
2. **Keep executable skills alongside trained cells.** A checked procedure can run without a model call. The child also learned to ask sensible questions on a different family. Measure those two benefits separately. Register what each skill accepts, how to verify its result, and the cases that previously fooled it.
3. **Give every newborn a place and regular turns.** A cell can grow up, take part and have children while it is still poor at its current work. Use checked outcomes to find good partners for particular duties. Let age, chance and available resources govern the population. Compare different team sizes at the level of the whole body. At this cell size, 1,000 distinct stored adapters would occupy approximately 37 GiB before the shared base and metadata. I exercised three distinct adapters with two resident slots. [Living population design and trial](hive-growth.md#the-life-of-a-cell)
4. **Test transfer on a real task where evidence can change.** I would next give the hive an incomplete calendar request, let it ask one clarifying question, change a constraint mid-task, and interrupt it after the first saved action. Score the final calendar, duplicate actions, number of clarifications and CPU time. Use fresh calendars for promotion, then repeat the same experiment on file repair and data reconciliation. Track both old and new tasks across successive generations.

This experiment tests one learned child, exact feedback and a small family of equations. The eight primary worlds and four follow-up worlds measure a specific behavior. The finite-grid sweeps establish the executable methods' coverage within that family. Cross-field reasoning, sustained conversation and unattended evolution across generations need different outcome tests.

## Running the experiment again

I recomputed the hidden answers and measurement budgets for all 81 archived episodes, including 56 primary runs, 12 follow-up runs, 12 teaching runs and the interrupted run. All 17 targeted automated tests passed. The deployable child is stored locally under `runs/rule-lab/catalog/t80+labchild.gguf`, with SHA-256 `89d024b332f81522a0716820e016709760016679602cdbf15313c64f5340b922`. The Git branch includes the learning code, learned executable procedure and evidence. The model binaries live in the worktree's ignored run directory.

From this worktree the existing CPU environment, model files and independent adapter catalog are available at the paths below. Use a fresh output directory to repeat an experiment. Reusing its output directory resumes its saved notebooks.

```bash
cd /workspace/HiveMIND-rule-lab
PY=/workspace/HiveMIND/.venv/bin/python
LAB=runs/rule-lab
RT=/workspace/scratch/hivemind-runtime/ik_llama.cpp
CPU=(--binary "$RT/build/bin/llama-server" --base "$LAB/assets/base.gguf" --catalog "$LAB/catalog")

"$PY" -m training.experiments.rule_lab "${CPU[@]}" \
  --out "$LAB/replay-parent" --families affine interaction --seeds 101 102 103 104 \
  --modes guided open solo solver

"$PY" -m training.experiments.rule_lab "${CPU[@]}" \
  --out "$LAB/replay-child" --cells t80+labchild t80+g41code \
  --families affine interaction --seeds 101 102 103 104 --modes open
```

To repeat the fresh interaction follow-up, activate the alternate measurement format for the parent. The child plus exact-worker arm uses the original format.

```bash
"$PY" -m training.experiments.rule_lab "${CPU[@]}" \
  --out "$LAB/replay-format" --families interaction --seeds 211 212 213 214 \
  --modes solver open --accept-probe-envelope

"$PY" -m training.experiments.rule_lab "${CPU[@]}" \
  --out "$LAB/replay-child-solver" --families interaction --seeds 211 212 213 214 \
  --modes solver --cells t80+labchild t80+g41code
```

For the same-weights control pass `--cells t80+g41data t80+g41data`. For the written-method arm use the parent and pass `--method "$LAB/procedure-v2/method.txt"`. The following commands reconstruct the procedure and child from the preserved development receipts and exercise recovery on seed 98.

```bash
"$PY" -m training.experiments.rule_lab_recipe "${CPU[@]}" \
  --source "$LAB/teaching" --out "$LAB/replay-procedure"

HIVE_TERNARY_HOME=/workspace/scratch/hivemind-runtime \
  "$PY" -m training.experiments.rule_lab_train --source "$LAB/teaching" \
  --recipe "$LAB/replay-procedure/learner.json" --unpacked "$LAB/assets/unpacked" \
  --parent "$LAB/assets/g41data.safetensors" --out "$LAB/replay-training" \
  --converter "$RT/convert_lora_to_gguf.py" --deploy "$LAB/catalog/t80+replaychild.gguf"

"$PY" -m training.experiments.rule_lab_checks "${CPU[@]}" \
  --recipe "$LAB/procedure-v2/learner.json" --out "$LAB/replay-checks"

"$PY" -m pytest -q tests/test_rule_lab.py tests/test_ternary_restart.py
```

The learning script needs the earlier successful affine demonstration from protocol 2. It is included in the compressed traces. To rebuild the source directory on another machine, extract the records whose `cohort` is `teaching` and write each `episode` value to its recorded `source` filename. The packed 8B base, the unpacked training snapshot and the original HiveMIND adapters are external model assets. Their revisions and hashes are in the results. [Packed base](https://huggingface.co/prism-ml/Ternary-Bonsai-8B-gguf/tree/c2aefbeb4b24469cd11579c3384b990404c17a30) · [Training snapshot](https://huggingface.co/prism-ml/Ternary-Bonsai-8B-unpacked/tree/ac20f03fc62e872399218b659c8e949dfca05769) · [HiveMIND weights](https://github.com/Arnav123-s/HiveMIND/releases/tag/hive-grown)
