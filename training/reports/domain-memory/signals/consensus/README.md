# Requiring both routers to agree

The serving rule emits a specialist only when the frozen two-sender model and the separate TF–IDF classifier name the same specialist. The TF–IDF classifier reads the same current request and latest prior user turn. The rule can reduce mistakes by abstaining on disagreements. It can also drop correct advice or preserve an error the models share.

**On 30 fresh requests, agreement preserved seven of eight correct advisories, avoided zero errors, and left 17 of 24 supported requests without advice.** The original pair and the two-method rule each produced only correct advice on this small panel. Both correctly abstained on all six unsupported requests. The preregistered confirmation criterion required higher emitted precision and retention of at least three quarters of correct advice. Only retention passed. [Frozen protocol](protocol.md) · [Per-request results](../consensus-results.json)

| Panel and method | Correct advice / issued | Wrong on supported | Spurious on open set | Supported without advice | Open-set abstentions | All exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original 60, pair | 23/26 | 2 | 1 | 23/48 | 11/12 | 34/60 |
| Original 60, same-view centroid | 26/34 | 7 | 1 | 15/48 | 11/12 | 37/60 |
| Original 60, require agreement | 20/21 | 1 | 0 | 27/48 | 12/12 | 32/60 |
| Fresh 30, pair | 8/8 | 0 | 0 | 16/24 | 6/6 | 14/30 |
| Fresh 30, same-view centroid | 9/11 | 2 | 0 | 13/24 | 6/6 | 15/30 |
| Fresh 30, require agreement | 7/7 | 0 | 0 | 17/24 | 6/6 | 13/30 |

On the original 60 the methods agreed on a named specialist 21 times, both abstained 23 times and disagreed 16 times. Requiring agreement filtered the film-director lookup sent to mathematics and the churn-calibration request sent to conversation. It also discarded correct advice on the sock guarantee, parity sequence and bicycle-braking problems. Both methods sent the explicit FPGA timing question to physical science. This is a retrospective use of the original panel, which had already informed the choice to test agreement.

On the fresh 30, the methods agreed on a specialist 7 times, abstained together 18 times and disagreed 5 times. Agreement dropped one correct suggestion to talk through a teammate's disappointment. It advised correctly on 5/6 ordinary requests, 1/6 difficult ones, 1/6 explicit topic corrections and 0/6 history-dependent requests. The number of issued suggestions is too small to infer a general precision advantage.

## Reproduce

The evaluator authored the 30 new rows after seeing the first audit and froze them before running the agreement helper. They contain four prompts per domain and six open-set prompts. Independent expected routes and explanations stay outside both classifiers. The evaluator fits the centroid from the documented public training material, obtains the two-sender decision through its public interface, computes the reference agreement and compares it with the actual serving helper on every case. The two match on all 90. [Inputs](cases.json) · [Key](keys.json) · [Grader](../consensus_eval.py)

```sh
p=training/reports/domain-memory/signals
python "$p/consensus_eval.py" --checkout . --output agreement-results.json
```
