# Hive telepathy and sub-hives

Two separate CPU cells learned to pass short signals to a common reader. Each saw only its own four sensor readings. Each sent **one byte** in the eight-bit experiment. Together they got both requested decisions right on **96.6%** of fresh cases. A centralized network with all eight readings got **96.8%**. This tests direct communication on two numerical jobs. A shared conversational understanding is a further target. [Measurements](telepathy-measurements.json) · [Training, message protocol and topology](../../experiments/hive_signals.py)

## What the signal carried

One job asked whether the two banks had opposite polarities. The other asked whether their combined total was positive. A local reading alone leaves real uncertainty about both. Each sender used a small ternary layer with eight-bit inputs. A shared reader learned to use the pair of signals. During training, only the correctness targets for the two final decisions supervised the system. The senders received neither a local target nor the other bank's readings. This experiment used supervised learning through the communication channel. Learning such channels from delayed reinforcement is a separate problem. [Learning to Communicate with Deep Multi-Agent Reinforcement Learning](https://arxiv.org/abs/1605.06676)

| What reaches the decision maker | Opposite polarities | Positive combined total | Both correct |
|---|---:|---:|---:|
| One bank's raw input | 49.5% | 75.0% | 33.6% |
| Learned one-bit signal from each bank | 98.3% | 75.2% | 74.1% |
| Two bits each | 95.0% | 85.1% | 81.8% |
| Four bits each | 98.7% | 93.8% | 92.5% |
| Eight bits each | 99.1% | 97.5% | **96.6%** |
| A floating-point scalar each | 99.0% | 97.4% | 96.4% |
| Centralized network with both raw inputs | 97.4% | 99.4% | 96.8% |

These are means across five model seeds, with 8,192 training examples and 4,096 fresh cases per seed. One bit was enough to relay a sign. Magnitude matters when one bank is positive and the other negative, so the second job benefited from additional bits. A transparent four-bit protocol given the true local formula achieved **96.7%** on both jobs. Use an explicit signal where the quantity is already known. Learned signals are worth testing where the useful intermediate quantity is unknown.

## When a different sub-hive speaks

I exchanged the second sender between independently trained pairs. On this simple distribution, the original conventions happened to match. Cross-pair joint accuracy averaged **92.9%** in the four-bit experiment. I then created a second, equally capable convention by reversing one channel and compensating for it in the donor's reader. Every donor decision stayed identical. Directly connecting that channel to the original reader dropped joint accuracy to **0.7%**. Fitting a scale and offset on 64 shared inputs brought it back to **92.6%**. The calibration used pairs of signals, with no task labels. A changing channel can be healthy inside its own group and unusable by another. A small shared calibration set gives neighboring groups a way to check. [Zero-shot coordination and learned conventions](https://proceedings.mlr.press/v119/hu20a.html)

I exercised 4,096 task IDs per seed and deliberately gave one in eight requests a previous task's message or a message from an incompatible version. Accepting the payload without checking gave **83.3%** joint accuracy. Checking the task, sender, role and version and retrying the affected messages recovered **92.5%**. Without a retry, coverage was 87.5%, with both answers correct on 80.8% of all requested cases. Retries assumed a compatible sender was still reachable. A version tag cannot detect a sender that silently changes meaning under the same version.

The runnable four-bit example has two separate senders and a reader. Each sender can load just its own weights. The reader accepts asynchronous arrival order and recognizes duplicate or conflicting messages. A single four-bit code occupies a byte in this format, and its task and routing fields bring the application frame to **10 bytes**, before transport overhead. The saved 2,496-byte model bundle was replayed on 128 cases through independently loaded components. [Four-bit pair](engrams/four-bit-pair.npz)

```python
from pathlib import Path
from training.experiments.hive_signals import emit, interpret, load_reader, load_sender

p = Path("training/reports/rule_lab/engrams/four-bit-pair.npz")
left = emit(load_sender(p, 0), 0, 47, [1., 2., 0., 0.])
right = emit(load_sender(p, 1), 1, 47, [-2., 1., 0., 0.])
decisions = interpret(load_reader(p), 47, [right, left])
```

## How sub-hives can scale

I counted directed link transmissions on a four-way tree, with every leaf taking a turn as the requester. Global addresses route directly to two known specialists. Local replication places a compatible instance of each specialist in each of four regional sub-hives. The broadcast comparison sends the request across the tree once and receives replies from only the two relevant workers. These are simulated message counts with known addresses. They omit queueing, discovery, model execution and synchronization costs.

| Cells | Broadcast request plus two replies | Address two global specialists | Address two regional replicas |
|---:|---:|---:|---:|
| 16 | 26.8 | 13.5 | 6.0 |
| 64 | 94.7 | 21.4 | 13.5 |
| 256 | 354.7 | 29.3 | 21.4 |
| 1,024 | **1,382.7** | **37.3** | **29.3** |

No router needed more than five neighbors. When the root went offline, every region could still reach its two local workers. The two global primaries deliberately lived in different regions, so no region could reach both during that partition. The local approach paid for **eight worker instances instead of two** and assumed their message schemas stayed compatible. Deployment should count the storage, stale replicas and repair traffic along with message savings.

## What I would build next

1. **Give each sub-hive a local purpose and a small set of shared signals.** A conversation group might publish which commitment changed, which fields are still uncertain and where its evidence lives. Let the action group request the exact text or tool receipt when it needs more detail. Train and evaluate both ends on completed user tasks.
2. **Keep signals cheap and make escalation selective.** Compare one, four and eight bits, a small ordinary typed message, and an on-demand full notebook at equal compute and transmission budgets. Save longer messages for cases where finer evidence changes the reader's decision. Measure joint correctness on unfamiliar combinations as well as individual cell accuracy.
3. **Let new cells learn the group's language without making conformity a survival test.** Give new neighbors a small public set of shared examples. Store channel versions and calibration traces with their engrams. A cell can keep its own internal representation and learn a boundary translator to a neighboring group.
4. **Keep task state recoverable.** Signals can coordinate the current step. Keep user commitments, checked actions and outstanding work in a durable task notebook. Test sub-hive partitions, stale messages, independent retraining, duplicate work and a group rejoining after a long absence. Track correct completed tasks per CPU-minute alongside message volume.

Reproduce the learned-signal tests, protocol faults and topology counts with `python -m training.experiments.hive_signals --out /tmp/hive-signals.json --example /tmp/four-bit-pair.npz`.
