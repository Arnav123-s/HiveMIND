# What grows when the hive grows?

On one CPU core, growing from 8 to 32 to 128 distinct learned cells raised completion from **120 to 240 to 360 of the same 360 four-step jobs**. Every completed job had to get all 128 withheld inputs right. Giving the first eight skills sixteen physical copies apiece kept completion at 120. The copies earned their keep when an entire region disappeared. At 4,096 distinct cells, a regional search that could ask the larger hive for a missing partner completed **360/360**, at **1,492 correct jobs per CPU-second**. Searching the whole population from the start completed the same jobs at 719 per second. [Small-bank measurements](scale-measurements.json.gz) · [Regional measurements](region-measurements.json.gz) · [Two runnable colonies](engrams/scaled-colonies.zip)

Each neural cell in this experiment is a learned, reversible converter of one byte, with 32 ternary synapses and eight thresholds. A four-cell group implements a function that a single member was never trained on. This gives us a domain where every claimed answer can be independently checked. General conversation, tool choice from natural language, noisy signals and cross-field reasoning are substantially harder. I ran a separate meeting and pickup test to see whether a related way of organizing memory could improve a user-visible action. That test exercises a learned verb and an existing two-record operation.

## More skills per CPU-second

Five seeded populations each faced the same requests at all three sizes. One third of the supported benchmark requested only skills from the original eight. Another third needed a member from 9–32, and the last third needed a member from 33–128. The solver received the number of stages and public examples. It had to find the members and their order. The training data contained only individual conversions. Groups were composed on demand. A private exam used the remaining half of the input domain, disjoint from the public probe pool.

| Physical cells | Distinct skills | Two-step jobs correct / 360 | Four-step jobs correct / 360 | Four-step correct per CPU-second, ends only | Four-step correct per CPU-second, shared midpoint |
|---|---:|---:|---:|---:|---:|
| 8 | 8 | 120 | 120 | 2,172 | 1,835 |
| 32 | 32 | 240 | 240 | 2,038 | 2,179 |
| 128 | 128 | 360 | 360 | 558 | 2,274 |
| 128, copies of the first eight | 8 | 120 | 120 | 2,182 | 1,842 |

An endpoint-only search matches the possible first two stages against the possible last two stages running backwards. At 128 members its reusable pair index costs 128 KiB. In the shared-midpoint trial the instrument also exposes the byte at the boundary between two pairs. The hive can solve and check the front and back separately. A successful route reads six endpoint bytes and six additional midpoint bytes. Its reusable arrays cost 5 KiB for all 128 members. The exchange slowed the eight-member hive. At 128 it bought a **4.07×** throughput gain. A baseline trying at most 256 complete four-member programs per request solved **0/360** at 128. For two stages alone, the smaller index handled 4,586 correct jobs/s and the prebuilt pair index reached 5,010. The memory expense has a measurable return in that shorter workload. [Discovery code](../../experiments/hive_scale_router.py)

The CPU rates count completed correct jobs within five 0.25 CPU-second blocks per size and method. Each method received the same cyclic order at that size and seed, with a balance of all three skill ranges. Fast refusals earn zero credit but leave time for other requests. A job that crossed its deadline earned zero. The clock includes routing, reading and checking cell files on cache misses, transformation of 128 bytes, and scoring. Index building, training and simulated sensor wait are outside that clock. The rates are batch jobs on numeric arrays. Network framing, transport delays and language generation require separate budgets.

## Regions that can recruit across boundaries

I trained three further populations up to **4,096 distinct cells each**, divided into regions of 64. Each job supplied two regional hints, one per pair of stages. The fixture made 60% of tasks local, gave one stale hint on 20%, and placed a required partner outside the nominated region on the other 20%. The hints came from the task fixture. A deployed directory would have to learn or obtain them. Every route still had to match observed behavior. On a failed local search, the region could broaden just that pair's search and reuse the same readings. [Regional experiment](../../experiments/hive_scale_regions.py)

| Population | Global search, correct/s | Regional search only, correct/s | Local search with wider fallback, correct/s | Fixed exam, regional only / with fallback |
|---:|---:|---:|---:|---:|
| 128 | 2,166 | 1,993 | 2,130 | 216/360 · 360/360 |
| 1,024 | 1,467 | 1,865 | 1,836 | 216/360 · 360/360 |
| 4,096 | 719 | 1,939 | 1,492 | 216/360 · 360/360 |

A sealed region missed **all 72** stale-hint and **all 72** cross-region cases at each size. Widening one search recovered every one. At 4,096, the three individual runs with fallback achieved 1,445–1,550 correct/s. The global runs achieved 712–723. Global lookup was slightly faster at 128 on this particular task mix. Use a region as the first place to ask. A missed match should travel with the readings that have already been paid for.

Each large bank cost about 52,400–52,700 training observations. The algorithm chose probes that distinguished the remaining candidate neurons, using only outside before-and-after readings to learn the two internal updates. All **12,288/12,288** trained members exactly matched their teacher on every possible input. Using the same number of randomly ordered readings produced **740/12,288** exact cells. This advantage depends on a known threshold family, a reversible interface, noiseless measurements and the freedom to choose the next input. A same-budget random curriculum is a useful control whenever a new family is added. [Cell and training implementation](../../experiments/hive_scale_cells.py)

At 4,096, packed weights occupy 64 KiB. The shipped colony also contains 105,436 bytes of teaching records and a 319,302-byte JSON manifest. Its compiled masks and single-stage search arrays take 160 KiB. Keeping separate warm global and regional directories, as the fallback test did, doubles that figure before ordinary Python overhead. The entire Linux stress process peaked at **38.1 MiB**, including the teacher data and evaluation machinery. There were two live execution slots, and the search directory retained a functional representation of every skill. A comparable language-model test has to charge for whatever representation lets its directory inspect each specialist.

## What a newborn should learn

I gave eight colonies identical birth and death schedules, eight elders, two births per round for 24 rounds, and **14 checked readings per newborn**. The same budget paid for 672 new readings in each policy and seed. Weak children stayed alive. Regional notebooks kept earlier lessons available to later children. The workload shifted through three groups of paired services and then returned to the first. A policy saw only past and current requests when choosing lessons for the next round. The tasks supplied public service identities. I scored the actual two-stage outputs across all 256 inputs. [Birth and schooling experiment](../../experiments/hive_scale_births.py) · [Per-round records](scale-memory-and-life.json.gz)

| What the two newborns study | Jobs completed / 12,288 | Success when the first workload returned |
|---|---:|---:|
| A living parent's existing duty | 1,214 (9.9%) | 9.7% |
| Two randomly selected missing duties | 4,172 (34.0%) | 57.8% |
| The two missing duties with the most requests | 6,051 (49.2%) | 84.8% |
| Two duties that together would finish the most recent blocked jobs | **6,264 (51.0%)** | **84.9%** |

Joint schooling beat individual frequency on seven of eight seeds. Its biggest gain came when a new workload arrived. Two popular skills can each leave a different job half finished. Learning both halves of one blocked job gives somebody a result. Under joint schooling, **36 of the 412 living members** still lacked enough evidence for independent duty at the end. There were 36 deaths across the eight colonies in every policy. Death depended on the sampled lifespan. The number of births was an experimental control. Learning an entirely new architecture or producing a reliable new teacher still requires another mechanism. Only about half the jobs finished under the strongest policy.

## What a small engram can repair

A quick route passed all the clean in-library exams and abstained on all 240 foreign two- and four-stage devices. I also made 240 instruments behave like an existing program except at two byte values. One change fell somewhere in the public pool and one in the withheld pool. Up to six public observations led to **229 confidently wrong answers and 11 deferrals**. More identical workers would repeat the same mistake.

For a device being commissioned for repeated use, I gave a separate calibration step access to all 256 final readings. It tested an existing candidate and stored the two exceptional input/output pairs. If the earlier search had deferred, it tried three disjoint sets of witness inputs to find a base candidate, then checked the entire domain. Two exceptional inputs can spoil at most two of those sets. The stored recipe names the device revision and the content hashes of its component cells. Its exception table is four bytes. The complete serialized recipes, including identifiers, averaged **260 bytes**. All **240** altered instruments then replayed exactly, including the 11 earlier deferrals. All 240 unrelated instruments were refused. The altered cohort paid **61,440 final readings** and 12 additional midpoint bytes beyond the quick trials. Reusing this recipe requires the instrument to expose a trustworthy version or a fresh calibration. For language and other unbounded domains, finite examples support an estimate of residual error. [Certification and replay](../../experiments/hive_scale_certify.py)

I also removed the first eight packed cells from a packed archive shard in each run. With 128 distinct skills, cold workers initially completed **0/40** affected jobs and **40/40** unaffected jobs. Re-fitting from independent teaching records recovered **40/40** affected jobs. Another cold start reused the verified repairs. The archive with sixteen replicas of each of eight skills completed **40/40** affected jobs immediately using surviving copies. Losing both the unique weights and their teaching record prevented recovery in all five trials. The 16-byte packed weight is cheaper than the average 25.7-byte teaching log for this family. A second physical copy is the cheaper exact backup here. The teaching log additionally allows a fresh fit and exposes how the response was learned. These are local file-loss drills. The directory was built before the outage, and its compiled masks could themselves serve as a replica if that execution path were allowed. [Archive and recovery](../../experiments/hive_scale_archive.py)

## A speed improvement in the working hive

The normal engram recall path re-read and re-tokenized the entire JSONL catalog on every request. I added a per-file-generation inverted index. A query looks up overlapping words within the requested model family, computes the original Jaccard score, preserves its tie order and checks the current adapter files. An append or atomic replacement causes a rebuild. At **4,096 metadata records**, median warm CPU time on specific queries went from **15.45 ms to 0.178 ms**. On common queries it went from 16.63 ms to 0.849 ms. Cold build plus first lookup took 24.15 ms. The first lookup after append took 18.08 ms. The retained Python allocation was about 3.35 MiB. All **540** measured lookup results across five sizes exactly matched the previous implementation. The harness used real JSONL files and file-presence checks with empty adapter placeholders. [Production change](../../../team/engram.py) · [Paired benchmark](../../experiments/engram_index_scale.py)

Retrieval speed alone left an important failure intact. With 4,096 records, ordinary text lookup led to the correct SQLite update on **3/12** two-entry meeting or pickup requests. An experimental index keyed by the demonstrated verb and the two-record operation completed **12/12**. Both declined all 12 unsupported requests without a write. A previously unseen verb, “shuffle,” yielded **0/4** before teaching. One checked field exchange supplied the verb binding. The operation-aware route then completed **4/4 new phrasings** and declined four conditional or ambiguous requests. The final states were read from a reopened database. Repeating a command produced one revision. The 4,096-record catalog initially contained three executable verb records and 4,093 read-only notes. This tests retrieval of a known operation and its arguments. The calendar and pickup examples share a schema, and the grammar still comes from the earlier work-order study. [Durable work-order trial](../../experiments/hive_scale_work_orders.py) · [Queries, candidate lists and actual revisions](scale-memory-and-life.json.gz)

For the byte cells themselves, the fastest simple execution path depended on memory. At 128 cells a four-stage job over 128 values averaged **316 µs** in the median run with neural workers and **264 µs** with compiled masks in the same two-slot file-backed cache. Keeping all compiled masks resident reduced this to **30.6 µs**. Keeping a full 256-byte mapping per cell reached **7.2 µs**, using 32 KiB for the mappings. All paths checked the same outputs and these timings exclude discovery. A hot finite skill can be compiled to a table. A transformer has a very different input space. For the large models, the existing measurements of adapter switching and integer kernels remain the relevant baseline. [Earlier runtime and kernel study](continual-learning-and-speed.md)

## Where I would invest next

For general use, I would keep one conversation responsible for the user's current goal. A sub-hive should be able to return a verified result, pass along unfinished work, or identify the one question the user can answer. Compare that whole path against the existing single CPU model and an ordinary tool workflow at the same wall time and memory. Grade the saved file, the actual calendar, or the correctness of the answer.

1. **Give each sub-hive a public work contract and a way to ask for one missing result.** For the next test, start with calendar corrections, CSV reconciliation and file repair. Independently verify the actual saved state. Run each with an absent specialist, a delayed intermediate result and a misleading region hint. Count correct end states per CPU-minute, along with clarification turns, repeated actions, and communication bytes including headers.
2. **Let unresolved work direct practice without controlling who lives.** Keep a short record of which missing pair would have completed each failed request. Compare joint schooling with single-skill frequency on the same real requests. Reserve some schooling for rare duties and measure the gap between their service level and the overall average. A popular pair can otherwise absorb a whole training budget.
3. **Pay for stronger checks where a mistake will recur.** Store a counterexample alongside the positive demonstration, checkpoint the version and retain the old recipe. For open-ended tasks, hold out whole document sources or interaction patterns. Measure wrong actions that looked successful to the original checker. A probe designed to distinguish plausible alternatives gives the verifier a chance to discover an unseen exception.
4. **Teach the hive to discover its own useful boundaries.** The midpoint, service identities and contract names in these experiments were available in advance. Train a small sender to choose a useful intermediate signal on one tool family, then freeze it and test a different recipient or tool. Compare with the same number of random bytes, a direct tool call and no signal. A transferable gain here would bear more directly on the goal of a versatile hive.

## Reproduce or inspect

The scale studies use NumPy and the repository's Python modules. The timing runs used one process pinned to one core of a Xeon Platinum 8573C under a four-core quota. The smaller trial used seeds 611, 673, 701, 743 and 809. The larger trial used 929, 947 and 971, with a 0.4 CPU-second block per size, method and seed. Rates vary by CPU and filesystem cache. The raw results retain individual blocks.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m training.experiments.hive_scale --out /tmp/hive-scale-small
python -m training.experiments.hive_scale_regions --out /tmp/hive-scale-large
python -m training.experiments.hive_scale_births --out /tmp/hive-scale-births.json
python -m training.experiments.engram_index_scale --out /tmp/hive-scale-recall.json
python -m training.experiments.hive_scale_work_orders --out /tmp/hive-scale-orders.json
python -m pytest -q tests/test_hive_scale.py tests/test_engram_recall_index.py
```

To try a commissioned four-cell group without its original teachers, unpack the two colonies, then run the Python block from the repository. The archive contains both the packed weights and the independent observations used for regrowth.

```bash
unzip -q training/reports/rule_lab/engrams/scaled-colonies.zip -d /tmp/hive-live
```

```python
import hashlib, json
from pathlib import Path
from training.experiments.hive_scale_archive import Archive
from training.experiments.hive_scale_cells import BYTES
from training.experiments.hive_scale_certify import replay
from training.experiments.hive_scale_router import Directory

root = Path("/tmp/hive-live")
example = json.loads((root / "example.json").read_text())
directory = Directory(Archive(root / "small128"), example["anchors"])
output = replay(example["recipe"], directory, example["version"], BYTES)
assert hashlib.sha256(output.tobytes()).hexdigest() == example["expected_sha256"]
```
