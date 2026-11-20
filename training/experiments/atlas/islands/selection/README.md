# Does market pricing choose better training examples?

LMSR pricing selected five different examples from a selector with identical valuations and fixed prices. It covered all 60 training neighborhoods. The migrated specialist heads then answered **23/30**, one fewer than the fixed-price control, and scored within the range of five class-balanced random halves. Both elastic-pull settings gave the same result on the paired comparison. Pricing changed which examples the hive studied; wider coverage did not improve these answers.

All selectors chose 30 of the same 60 labeled training examples, with the same quota in every domain and answer class. The original three-generation fit, held-out examples, scorer and migration were unchanged. Five random seeds were fixed before testing. As in the parent study, the specialist was supplied the true domain. All 30 test questions were known from earlier research and were excluded from selection and training. This is an exploratory feature-based replay. [Frozen selection protocol](protocol.md) · [Original island study](../README.md)

| Selector | Pull | Migrated specialist /30 | Earlier /18 | Supplementary /12 | Shared trunk /30 | Selector CPU ms |
|---|---:|---:|---:|---:|---:|---:|
| Hard examples | 0.5 | 24 | 15 | 9 | 20 | 0.75 |
| Uncertainty + rarity, fixed prices | 0.5 | 24 | 15 | 9 | 20 | 11.44 |
| Uncertainty + rarity, LMSR | 0.5 | 23 | 15 | 8 | 20 | 12.10 |
| Five random halves, mean | 0.5 | 23.2 | 14.8 | 8.4 | 19.2 | 0.30 |
| Hard examples | 0.1 | 24 | 15 | 9 | 19 | 0.70 |
| Uncertainty + rarity, fixed prices | 0.1 | 24 | 15 | 9 | 19 | 10.81 |
| Uncertainty + rarity, LMSR | 0.1 | 23 | 15 | 8 | 19 | 11.41 |
| Five random halves, mean | 0.1 | 23.2 | 15.0 | 8.2 | 19.2 | 0.29 |

In seed order 23, 29, 31, 37, 41, the random specialist scores were **23, 23, 23, 23, 24** with normal pull and **24, 23, 23, 23, 23** with weaker pull. The existing full-60 training control scored 23 with either pull. The earlier hard-half result of 24 is 0.8 question above the random mean; a randomly selected half also reached 24 at both pulls. These are repeated selections on the same small test set.

## What the market bought

Each training item stands for one of 60 mutually exclusive demand outcomes. An example buys half a share of itself and a quarter of each of its two nearest neighbors in centered training-state cosine space. Lower-density examples receive a scarcity term in their value. The market begins uniformly with zero shares outstanding, liquidity 0.5 and 15 cash units. For each of 30 selections, it buys the quota-eligible example offering the most fixed uncertainty-plus-rarity value per current bundle marginal price. Execution debits the exact LMSR cost difference. The fixed-price control uses the same offers and quotas with every outcome price held at 1/60. This market simulates an allocation rule; no trader forecast was settled against a separately realized demand. [Market equations and tie rules](protocol.md) · [LMSR background](https://hanson.gmu.edu/mktscore.pdf)

| Selector | Distinct training items covered by purchased bundles /60 | Mean nearest selected cosine |
|---|---:|---:|
| Hard examples | 52 | 0.835 |
| Fixed prices | 57 | 0.807 |
| LMSR | 60 | 0.804 |
| Random seeds, range | 54–56 | 0.807–0.842 |

LMSR and fixed prices retained 25 of the same 30 examples. In 23 trade steps, current prices changed the winner relative to applying uniform prices to the *same remaining offers*. The realized cost was 0.526915 cash units; closing prices ranged from 0.00958 to 0.02604. The ledger records every bundle, marginal quote, finite charge and closing balance. Compared with fixed pricing, only one correctness decision changed, on the same supplementary water question under both pulls. The shared trunks' correctness decisions were identical. Spending, coverage and lower cosine overlap are properties of the selector. They were measured separately from held-out answer correctness. [Raw subsets, ledger, cases and paired contrasts](results.json)

Selection CPU and fitting were measured in the same process as the matched controls, single-threaded, over five rotating trials after warm-up. In the primary 0.5-pull arm, median total CPU including training was 55.82 ms for LMSR, 57.52 ms with fixed prices, and 46.22 ms for the original hard selector. The two feature-based selectors pay for the same nearest-neighbor search and candidate processing. Native feature extraction took place in the prior study and is excluded here.

## Reproduce

```sh
python training/experiments/atlas/islands/selection/compare.py --out /tmp/selection-replay.json
```

The runner checks the original hard arm's selected samples and all migrated specialist and trunk predictions against the archived receipt. The new arms use the same calibrated unrestricted first-token evaluator. [Runner](compare.py) · [Native token calibration](../calibration.json)
