# Fresh confirmation on shipping and arithmetic decisions

The shipping experiment delivered all 11 eligible requests on each of two banks and correctly withheld the other 21. A handwritten kilogram adapter achieved the same answer coverage. The compiled trace reduced execution cost when only one shipping method was available. Arithmetic verification rescued one correct minority answer on 26 independently written tasks. Its language parser reached the checker on just two questions, leaving 16 wrong or unjustified answers in the final output. [Prospective protocol](protocol.md) · [Frozen digests](checksums.json)

## Shipping

Each bank received the same 32 requests. Fourteen followed the public kilogram grammar, 17 were malformed, underspecified or different requests, and one used the existing explicit method interface. Which requests have a unique deliverable answer depends on the versions in the bank. The single-bank and mixed-bank totals both happen to be 11 eligible and 21 ineligible. The original arm used the released saved-method path inside the experimental wrapper. A separate handwritten adapter converted units and called that path. The cold guarded arm had no artifact. The warm arm had separate side-exit and qualification examples before the first panel call. [Questions and external answer labels](shipping.json) · [Separate qualification packet](credential.json)

| Bank | Policy | Correct / eligible | Wrong releases | Justified abstentions / 21 | WASI calls | Guest inputs |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Per parcel | Original | 1/11 | 0 | 21 | 1 | 1 |
| Per parcel | Handwritten | 11/11 | 0 | 21 | 20 | 29 |
| Per parcel | Guarded, cold | 11/11 | 0 | 21 | 20 | 29 |
| Per parcel | Guarded, warm | 11/11 | 0 | 21 | 15 | 19 |
| Per parcel and pooled | Original | 0/11 | 0 | 21 | 2 | 2 |
| Per parcel and pooled | Handwritten | 11/11 | 0 | 21 | 39 | 57 |
| Per parcel and pooled | Guarded, cold | 11/11 | 0 | 21 | 39 | 57 |
| Per parcel and pooled | Guarded, warm | 11/11 | 0 | 21 | 39 | 57 |

The released single bank contained the real retained per-parcel program. For the mixed bank, another program passed ordinary fieldwork admission using public and reserved pooled bills. Each policy had fresh state and the same real CPython WASI guest. The fee oracle used decimal arithmetic and a ceiling for each parcel or the pooled shipment. An explicit pooled request on the single per-parcel bank had to withhold, even when the current input happened to give the same number under both rules. The negative cases also included a second deliverable, ambiguous alternatives, invalid units and a 17-parcel request. [Per-request results and qualification receipts](shipping-results.json)

The opt-in terminal command returned 430 cents for the new two-parcel kilogram request. The ordinary local `./hive --once` command still returned 610 cents for the legacy saved-method request. Both exited successfully with no model available. [Terminal outputs](cli.json) · [CLI reproduction](cli.py)

The single-parent warm arm reused the compiled path on ten requests. Fuel fell from 20.45 billion to 15.37 billion per panel batch. Six successful warm-ups across the two viable conventions, three unsuccessful pooled warm-ups and the qualification attempts together cost 14 guest calls and 14.32 billion fuel. Recovering those costs takes about three batches of this same request mix. The mixed bank retained both versions and published no compiled sibling. It incurred preparation cost without a subsequent per-request saving. The execution-only times for handwritten and warm serving were 7.67 and 4.21 seconds on the single bank, and 20.54 and 15.96 seconds on the mixed bank. These single runs shared a CPU with other work; calls, inputs and fuel are the more reproducible costs.

## Dissent

Four fixed worker candidates accompanied each of 26 requests. Exactly 23 had a single answer under the requested format, and 21 of those contained that answer among the supplied candidates. This is a controlled test of the actual decision component and WASI arithmetic checker. Candidate strings were authored before the implementation was inspected. No language model generated them during the replay. [Requests, candidate outputs and answer keys](dissent.json)

| Policy | Correct / 23 | Wrong / 23 | No answer / 23 | Unjustified answers / 3 | Charged seats | WASI calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Current agreement | 6 | 14 | 3 | 3 | 63 | 0 |
| Diverse seating | 4 | 16 | 3 | 3 | 66 | 0 |
| Reordered control | 6 | 14 | 3 | 3 | 64 | 0 |
| Verified dissent | 7 | 13 | 3 | 3 | 62 | 1 |

The prime sum from 61 through 79 was 351. The existing agreement chose a shared wrong proposal. The actual checker validated 351, the minority answer, for the single gain. One other question matched the verifier but had no proposed value. The other 24 questions fell through to the agreement rule. On 18 affirmative closed tasks, verified delivery had six correct, nine wrong and three misses. On five meaning shifts it had one correct and four wrong. The final three requests had no single justified answer among the proposals, and all three received an unsupported agreement. The one checked delivery was correct. The one real WASI call consumed 1.15 billion fuel and the verified replay took 13.59 seconds including first-use guest compilation. Charged seats count inspected proposals in a replay. [Per-request outputs, checks and seats](dissent-results.json)

The strict preregistered hurdle passed by one paired answer with no increased wrong releases. The one discordant outcome gives a two-sided exact paired sign-test value of 1.00. These controlled inputs establish a successful rescue and expose limited verifier coverage. They give little information about average performance across natural model outputs.

## The remaining hard problems

The trial began from the isolated merge of G52 main `4cbd41c` and the reviewed learning branch. On the official G52 exam, both original and candidate systems delivered 32/32 easy and 20/32 hard jobs. The candidate passed 1/30 on the fixed held-out exam, compared with 2/30 before, and both got 0/7 untaught hard pulse tasks. On the 12 failed hard jobs after training, a recorded member solved two and no recorded member solved the other ten. Better selection could recover at most those two using the existing observed candidates. New hard practice also trailed established kinds, at 11/53 first-attempt successes versus 28/43. The arithmetic and shipping panels exercise narrow independently checkable contracts; they do not evaluate those held-out hard tasks. [Official G52 record](../../../../docs/reads/g52.md) · [Logged generation](https://github.com/Arnav123-s/HiveMIND/actions/runs/44594712108)

## Reproduce

With the project's Python environment and pinned CPython WASI SDK, the following calls start from fresh temporary banks. Output files contain per-case receipts; elapsed times and some guest fuel can vary between runs.

```sh
python training/experiments/atlas/confirmation/shipping.py --sdk /path/to/python-wasi --out /tmp/atlas-independent-shipping.json
python training/experiments/atlas/confirmation/dissent.py --sdk /path/to/python-wasi --out /tmp/atlas-independent-dissent.json
```

The source-hash checks intentionally pin the tested implementations. The panel exercises experimental opt-in interfaces; it makes no default-product or neural-training claim. [Shipping runner](shipping.py) · [Dissent runner](dissent.py)
