# Can the hive learn a correction and still use the old method?

Imagine an invoice where the buyer asks you to round tax on each line. Another buyer asks you to add the lines and round the tax once. Both rules are legitimate. A useful assistant can remember both and tell when the information it received is insufficient to choose.

## What happens in ordinary chat

Generation 47 has one shared 8-billion-parameter model and an active list of 24 specialists. Each specialist is a small set of learned changes to that model. They trained on overlapping examples, with extra practice in code, tables and data, writing, or finding information. Children start from an older version and can mix with the hive’s shared version. Extra training can improve one answer while spoiling another.

In hosted chat the base model handles conversation. For work, the runner loads a shared version plus one representative of each of the four specialties. Normally the shared version and the specialist whose training best matches words in the request each write and run their own solution. A third can break a disagreement. Checking the actual file catches some mistakes that agreement on the printed answer misses. The hive can still accept a mistake shared by all its workers. [Active generation](../../../cells/body.json) · [Choosing workers](../../../team/ternary.py) · [Checking a delivery](../checked-delivery/reproduce.md)

## What an unchanged score hid

We opened the 16 original exam archives and compared the actual deliveries on the same 64 prompts. The parent and generation 47 scored 47/64 apiece. They solved 45 in common. The older hive alone passed a file edit and a rounded percentage calculation. The newer hive alone passed a cache program and a grid program. Both missed 15. Knowing the correct choice after the fact would yield 49/64. Picking a version by how its task category had performed on the other seven groups of exam jobs still yielded 47/64. Arbiters that see a category alone have little to go on in this sample. [Job identities, entire comparison and individual choices](g47.json)

## Where the old and corrected methods can be used

For structured programming requests, the user can give the hive a task name, a description, example inputs and expected outputs. Independent checks can be supplied separately. The fieldwork command runs saved programs against those examples before it releases job results. The examples describe what the user means for this particular request. An old method can be right for an old convention even after a different method has been learned.

The general chat model and these saved programs have different kinds of memory. A passing program can be saved exactly and called again. Additional training can still make a model forget. The matching exam jobs measure that separately each generation. [Fieldwork setup and input format](../rule_lab/fieldwork/reproduce.md)

**Invoice test.** We supplied two small programs for the same invoice task, one for each rounding convention. Each earned its place by passing separate tests. The old terminal made the right decision on **3/6 requests**. The revised terminal made the right decision on **6/6**, returned **14/14 required files**, and switched back to the earlier method on new bills. On an ambiguous order both versions passed the supplied examples, then predicted **2 cents and 3 cents** on the same bill. The revised terminal named the bill and both amounts and withheld the batch. A proposed replacement that failed both independent checks never displaced the existing programs. These tests used human-written programs and zero model calls. [Frozen cases](work-order-cases.json) · [Outputs from both versions](work-orders.json)

**Can a cell learn a method worth keeping?** We asked the generation 47 coding specialist to write a shipping-fee calculator. Its first version multiplied a price before rounding a parcel’s weight up to the next 500 grams. It charged 429 cents for a parcel that should cost 340. Given that public example it returned the same faulty function again. Across two different shipping conventions and four model attempts, none qualified. [All four attempts](shipping-live.json)

We then added one narrow kind of correction. After generated code fails the public examples, the hive can test a different grouping of integer multiplication and division. It keeps the original source and checks a proposed fix against examples the code writer never saw. The per-parcel program improved from **4/100 to 100/100 fresh shipments** and passed all 12 separate qualification cases. There was only one eligible edit, so taking the first edit also scored 100/100. Three correct control programs stayed intact and passed 72/72 checks. In another correct calculation, blindly applying the available edit lowered the score from 24/24 to 0/24. [Independent shipping evaluation](shipping-eval/)

The second shipping convention charges on the combined weight. Its model-written program tried to decode already-decoded input and failed **all 100** fresh cases. Reusing the repaired per-parcel method for those jobs would pass only **38/100**. The hive withheld that method for the combined-weight request. Keeping a known program is useful only when there is enough evidence that its rule applies.

## Run the saved shipping method

The earned program lives in the included bank. The normal terminal reused it on a different set of **16/16 shipments** with zero new model calls. To run the same example from the repository root, use the Python WebAssembly runtime installed in the [fieldwork setup](../rule_lab/fieldwork/reproduce.md), then run the command below. The result for each shipment is in `runs/example-shipping/receipt.json`. To try your own weights, copy the example order, change its jobs, and choose a fresh output directory. [Example order](shipping/per-parcel.json) · [Actual learning and reuse receipts](shipping/runtime.json)

```sh
./hive fieldwork --sdk runs/fieldwork-assets/wasi \
  --bank training/reports/retained-skills/shipping/bank \
  --spec training/reports/retained-skills/shipping/per-parcel.json \
  --out runs/example-shipping
```

All 880 repository tests passed with the optional WebAssembly and native CPU checks enabled. The final checkout also reproduced the six invoice decisions, every fresh shipping score and output hash, and the 16 deliveries using the packaged method.
