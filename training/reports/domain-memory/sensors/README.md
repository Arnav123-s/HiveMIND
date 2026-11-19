# Check two sensor banks locally

```sh
./hive --once 'Check sensor banks [2,1,0,7] and [0,2,0,0]'
```

The raw measurements in this example are 3 and −2. Exactly one is positive, and their sum is positive. The saved senders emit four-bit codes 0 and 0. Their trained receiver predicts the first decision correctly and the second incorrectly. HiveMIND prints the raw answers and identifies the learned disagreement. The calculation runs locally and works without an 8B reasoning model, Torch or NumPy.

Supply two arrays of four JSON numbers with absolute value up to one trillion and up to twelve decimal places. The raw protocol defines bank X as `x0 + x1 − x2` and bank Y as `y0 − y1 + y2`. It asks whether exactly one value is strictly positive and whether their sum is strictly positive. Zero counts as nonpositive. The fourth entries are reserved by the raw formula. They still affect the trained sender's input scaling, which uses all four readings. If the pinned asset cannot be read or verified, the response identifies that it used only the raw calculation.

## What the learned pair does

The serving asset contains both sender weights and biases from the previously saved four-bit archive. The exporter runs the original trained receiver on all 256 ordered pairs of four-bit codes and stores its two decisions for each. The serving senders reproduce the original activation quantization, learned scalar transformation and four-bit rounding. The independent check uses decimal arithmetic on the supplied readings. Its two equations are part of the specified protocol. This numeric pair has a fixed measurement layout. The text domain router handles a separate task, as does the earlier eight-bit sensor study. [Archived model](../../rule_lab/engrams/four-bit-pair.npz) · [Exporter](export.py)

| Fresh requests | Both original learned decisions correct | Disagreements disclosed and corrected | Both final answers correct |
| --- | ---: | ---: | ---: |
| Independent Gaussian coordinates | 3,709/4,096 | 387 | 4,096/4,096 |
| Near individual decision boundaries, some with large reserved inputs | 48/256 | 208 | 256/256 |
| Exact or near-zero sum | 19/32 | 13 | 32/32 |

All 4,384 requests used the public conversation entry point. Both emitted codes and both interpreted decisions matched the original saved PyTorch senders and reader on every row. The external grader computed ground truth using integer millionths. The boundary groups were deliberately constructed to expose quantization errors. These counts measure agreement on this specific protocol and panel. [Machine-readable results and examples](results.json) · [Grader](check.py)

## Reproduce

The ordinary CLI requires only Python's standard library. Re-exporting or checking the reference archive requires the experiment's NumPy and CPU PyTorch dependencies. From the repository root, run the following commands in that environment.

```sh
p=training/reports/domain-memory/sensors
python "$p/export.py" --output /tmp/hive-four-bit-export.json
cmp /tmp/hive-four-bit-export.json team/assets/sensor-banks-four-bit.json
python "$p/check.py" --output /tmp/hive-four-bit-check.json
cmp /tmp/hive-four-bit-check.json "$p/results.json"
```
