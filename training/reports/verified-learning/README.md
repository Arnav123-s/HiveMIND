# Can the hive learn to repair a different program?

**Yes, for a measured kind of mistake.** An 8B coding cell fixed two programs that counted entries when the task required adding their quantities. The two corrections qualified independently and taught the hive a reusable edit. A third program calculated a deposit as seven times the number of boxes listed, even when a list entry represented several boxes. Before the lessons it delivered none of 24 new answers. After one lesson it still delivered none. After two, the hive revisited the very same draft with the model off, changed the calculation to seven times the sum and delivered **24/24 correct answers**. Disabling the learned edit took it back to zero. An unrelated queue problem stayed unsolved. People supplied the problem descriptions, faulty starting drafts and checks. The model supplied both correct programs. [Frozen protocol, model outputs and replay](native-lessons/README.md)

A buyer gave the hive several prices and asked for the spread. A real CPU coding cell wrote a working method, passed 12 separate qualification tests, and got all 40 fresh orders right. Chat then used its saved method with the language model disabled. A transit request was harder. The same cell twice wrote a program that counted an expired ticket as valid at the exact minute of expiry. A correction learned from two other tasks fixed that program, which then passed its 12 qualification checks and all 40 fresh ticket orders. Library fees and sensor streaks still failed qualification. [Live drafts, prompts, receipts and replay](live/README.md)

The cells share one 8-billion-parameter model. Each specialist adds a small separately trained set of weights, so two cells can solve different problems or repeat the same mistake. A checked program can enter a shared library available to every cell and to chat. A repeated correction can change which edits the hive tries on its next failed program. The experiments below measured changes in that library and repair process. The original training and shared model remain the starting point. [Generation 48](../../../docs/reads/g48.md) · [Earlier architecture, experiments and research](https://github.com/Arnav123-s/HiveMIND/pull/109)

## Try it

From the repository root, install the WebAssembly guest once. It runs proposed Python methods with an instruction limit and a read-only standard library. This path works on a CPU.

```sh
python scripts/setup_fieldwork.py
HIVE_BANK=training/reports/verified-learning/live/example-bank ./hive --once 'Run quote_spread with {"quotes":[229,184,207]}'
HIVE_BANK=training/reports/verified-learning/live/example-bank ./hive --once 'Run transit_tickets with {"minutes":[1200,1250,1217,1300]}'
```

The expected results are **45** and **3**. Each reply identifies the checked program and the inputs used. To run the included price order through its public examples and independent qualification cases, use the following command. Its output file contains 24.

```sh
./hive fieldwork --spec training/reports/verified-learning/live/quote-spread.json \
  --bank training/reports/verified-learning/live/example-bank --out runs/price-demo
```

To **earn** a method in your own bank, use an installed hive member and a fresh output directory. The file below is a small working example of the order format. Its `examples` are visible to the writer. Its `validation` inputs and answers remain outside the writer's prompt. Its `jobs` specify the actual deliveries.

```sh
./hive fieldwork --member auto --concise --spec training/reports/verified-learning/live/quote-spread.json \
  --out runs/price-learning
./hive --once 'Run quote_spread with {"quotes":[310,260,275]}'
```

After a successful admission, the second command returns 50. Both commands default to the same local bank. Point `HIVE_BANK` at another directory to switch banks. An empty value or `off` disables the default bank. A fieldwork `--bank` argument selects that command's bank explicitly. If several descriptions share a name, chat shows their identifiers. An explicit call such as `Run name@identifier with {"field":12}` selects the intended description. If implementations of that contract still disagree, the hive asks for an observation that resolves the difference.

## What grows

1. **A writer receives a public counterexample.** If a proposal fails, the next writer receives its actual source and first public failure. With `--member auto` the runner uses the installed coding specialist and shared member when available. Repeat `--member` with specific installed members to choose the rotation. Only one model needs to be resident at a time.
2. **A working method earns a place.** The guest runs the program on separate qualification cases, then delivers the jobs. A new program is admitted only when all succeed and the public and qualification input sets are disjoint. Earlier versions stay addressable. Publishing a bank record is atomic, retries are idempotent, and an interrupted writer cannot replace a checked program.
3. **An independently confirmed correction can teach a repair.** The hive compares a failed writer proposal with the actual writer correction that qualified. If they differ by a supported expression edit, it replaces the task's operand names with slots. For example, the reusable change may be “count entries → add values” or “strict boundary → inclusive boundary”. Activating a rule requires corroboration from two different contract descriptions, failed drafts and qualification input sets. Reordered or repeated copies of a qualification set count once. Two different sets can still overlap. A program fixed by the repair mechanism can itself enter the bank, but its machine-applied edit cannot vote to corroborate itself.
4. **A later request can use that repair.** At most eight candidate programs are scored against public examples by default. A winning candidate must still pass independent qualification. The existing arithmetic repair and an adapter for a writer that mistakenly decodes an already decoded input are handcrafted proposals. They compete within the same budget. The receipt distinguishes those from a learned expression. Working methods and new repair rules are separate kinds of progress.
5. **Previously failed work gets another chance.** Repeat `--spec` for several work orders in teaching order. After that pass, the runner revisits earlier public failures when new repair knowledge is available. It uses the original drafts and calls no writer a second time. Completed work replays from its receipt. A request that stopped waiting for a worker can also use a matching method another order has since earned. An independent qualification failure is withheld. The runner does not feed that hidden answer back into the writer.

The executable record is in each work directory's `receipt.json`. It contains public and qualification counts, the selected source digest, individual job results and, where applicable, the parent draft, rule support, number of candidate checks and earlier searches. `--repair-budget 2` limits the search to two public candidate checks. `--no-learned-repairs` keeps the built-in repairs and disables learned proposals and new rule acquisition.

## What this connects to the existing hive

| Earlier achievement | New measured behavior |
|---|---|
| Cells already wrote programs and received feedback. | One cell wrote a camera timer that returned zero at the instant of a strobe. A peer used one failed example to correct it and passed 28/28 fresh jobs. Retrying the original cell with the identical feedback yielded byte-identical corrected code. The accompanying savings problem remained unsolved. [Native peer study](peer/README.md) |
| Nightly practice already recorded working programs. | The local training command can now qualify an interval-merging program for ordinary chat. An actual generation 48 practice submission passed 72 fresh checks and all 1,110 separate cases in a bounded exhaustive test. The opt-in bridge currently handles this one contract. [Original submission, run and instructions](practice/README.md) |
| Earlier shipping and invoice methods already survived corrections. | In separate ordinary CLI processes the hive selected per-parcel, pooled and per-parcel pricing again, returning 430, 520 and 430 cents. An invoice with conflicting answers and no stated convention was withheld. [Version-switching exercise](switching/README.md) |
| Chat could already execute an installed saved program. | A local replay of the proposed GitHub chat workflow served price and ticket questions before fetching the model. Unrelated requests proceeded to model setup. The hosted shortcut ships with those two checked programs. [Hosted replay](hosted.md) |

Learning reusable operations from programs follows earlier work on library learning and learning from paired errors and corrections. Here the learned edit is small enough to inspect. Its contribution can be tested by switching it off and replaying the exact same failed program. This builds on the project's earlier fixed shipping repair, shared program library, and controlled specialist experiments. [DreamCoder](https://arxiv.org/abs/2006.08381) · [Break-It-Fix-It](https://arxiv.org/abs/2106.06600) · [Earlier HiveMIND trials](../retained-skills/README.md)

## What improved on fresh tasks?

A separate agent wrote and froze 20 contracts, 100 public examples, 140 qualification cases and 320 private jobs, without seeing the training pairs, repair implementation or earlier results. Each task started with a private copy of the same teaching bank. Four authored training contracts gave the hive two independently confirmed examples each of a count correction and a boundary correction. New test tasks received one authored faulty or already-correct draft and the same two-candidate allowance in both arms. A receipt counted as correct only when the actual returned result or file passed the independent check. [Frozen study and all outcomes](experiment/README.md)

| On the 20 fresh contracts | Built-in repairs | Built-in and learned repairs |
|---|---:|---:|
| Completely correct contracts | 4/20 | 10/20 |
| Correct private outputs delivered | 64/320 | 160/320 |
| Incorrect private outputs delivered | 0 | 0 |
| Private outputs withheld | 256 | 160 |
| Already-correct controls preserved | 3/3 | 3/3 |
| Actual guest batches / individual inputs evaluated | 29 / 197 | 51 / 387 |

Six contracts changed from failure to success, with no regressions on this set. The learned arm had more applicable proposals and consequently ran more checks at the same cap. A human who supplied the two correct rules beforehand also recovered those six contracts. The gain shown here is being able to acquire the operations from corrections. There is no measured advantage over a human who already supplies those operations and the same built-in fallbacks.

An earlier six-task panel exposed a limit. One donor read a value directly from a dictionary and another used a local variable. The first version failed to recognize the same correction and solved 3/6. After extending the matcher to named dictionaries with fixed string keys, it solved 6/6 on that now-disclosed panel. The 20 fresh contracts above were the separate check. The hive also returned all 48 old-skill outputs correctly when revisited. [Initial, revised and fixed-rule comparisons](experiment/README.md)

## Limits that affect a real user

- **Finite tests can agree with a wrong program.** In a deliberately weak qualification test, counting sacks and summing their weights yielded the same number for every teaching and qualification input. Both primary arms then released 20 wrong answers on fresh inputs. New examples that distinguish plausible rules matter more than repeating easy examples.
- **Challenging an answer has a measurable cost.** With `--challenge 2`, the hive can check two alternative programs derived from verified past corrections. On the exposed sack example this withheld all 20 wrong files. On six new orders it caught none of eight wrong outputs and withheld six correct ones. It remains opt-in. A disagreement receipt includes the actual input and both answers so a user can supply a distinguishing example. [Fresh and original challenge results](experiment/challenge.md)
- **Training examples are not proof of autonomous invention.** The controlled study supplied faulty drafts and independently correct training proposals. The live study used seven real model drafts across four work orders. The model wrote the price method on its own, and the transfer-to-transit result used repair rules derived from the authored training pairs. The live transfer replay followed inspection of the failures. The ordinary language model's weights were unchanged throughout these experiments.
- **A name or a vote alone can be misleading.** Source identity, input shape and unit checks help. Under uncertain wording, the free-text shipping route gave 11/29 valid quotes and made zero calls on the 29 deliberately unsuitable requests in two earlier development panels. That lost five correct quotes compared with the previous reader while avoiding its eight wrong argument lists and 18 out-of-scope calls. Exact invocation remains available for every registered method.
- **The learning mechanism has a boundary.** It can learn certain small arithmetic, comparison and collection edits. It cannot yet invent arbitrary algorithms, prove a result from its own confidence, or demonstrate open-ended recursive improvement. A saved program is exact executable memory. A compact rule improves how the hive repairs other programs. Neither establishes that the nightly model training has improved on unrelated science or coding tasks.
