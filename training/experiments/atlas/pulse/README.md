# How many workers should answer a pulse question?

On 55 previously unexamined G51 and G52 questions, stopping when the remaining votes could no longer change the result **matched all 55 four-worker choices with 122 of 220 recorded worker calls**. Four of its 54 deliveries were wrong. The existing crash-reserve strategy, applied to the same four candidates and answer grouping, made every one of the same choices and bought precisely the same seats. The actual after-body delivered the same counts with 114 completed workers. This experiment supports stopping early relative to an always-four reference. It gives no reason to replace the current worker policy.

| G51 + G52 | Right | Wrong | Withheld | Worker calls | Archived worker interval sum |
| --- | ---: | ---: | ---: | ---: | ---: |
| First two, require agreement | 43 | 1 | 11 | 110 | 2,535 s |
| Fixed three, plurality | 50 | 4 | 1 | 165 | 3,517 s |
| Fixed four, plurality | 50 | 4 | 1 | 220 | 4,643 s |
| Fixed four, withhold ties | 46 | 3 | 6 | 220 | 4,643 s |
| Certified early stopping, two to four | 50 | 4 | 1 | 122 | 2,862 s |
| Current crash trigger, common four-seat pool | 50 | 4 | 1 | 122 | 2,862 s |
| Actual archived after-body delivery | 50 | 4 | 1 | 114 | 2,976 s original full-run wall time |

The stopping policy finished 44 tasks after two workers, ten after three, and one after four. Its 44.5% reduction in calls against always-four was 41.7–47.2% in a descriptive 95% paired bootstrap over the 16 pulse shards. The corresponding reduction in summed recorded intervals was 38.4%. The intervals include overhead between successive worker completions on the original machines. They project sequential cost on the archived work. The original after-body wall clock includes startup and its own delivery stage, so it is reported separately.

**The difficult questions expose the limit.** Among 43 easy questions the policy delivered 42 right and one wrong. Among 12 hard questions it delivered eight right, three wrong and withheld one. For the G52 mail-configuration query three workers printed an empty host and zero keys. On a G51 word-frequency query, two workers produced passing answers, yet the tie went to a failing earlier response. Of the 55 questions, 52 had at least one passing worker. A certifiable vote decision need not be a correct world answer. [Per-question decisions](decisions.json.gz) · [Counts, comparisons and negative results](results.json)

## What was compared

Each pulse shard paired the original trained after-body and its before-body on identical prompts. We took their first two independent submissions each, in order: after 1, after 2, before 1, before 2. Every evaluation panel had four distinct cell names. Some cells share ancestors and can make correlated mistakes. The four outputs actually ran, but the mixed committee is a retrospective replay of two separate runs. Choosing from the recorded after-body answers without the before-body is the operational baseline.

The decision function receives a stream of output strings. It requires two matching votes, collapses whitespace/case and unambiguous numeric spelling, and releases a real worker’s original printed answer. Among tied classes the earliest submission wins. The early-stop rule enumerates every possible remaining ballot including silence and previously unseen classes. It returns early only if all completions select the same original submission or all withhold. This costs no grader calls. We verified equality with fixed-four on every real case and on all 625 four-worker streams over four abstract answers and silence. A tie-withholding control measures the consequence of the chosen tie rule. [Policy](policy.py) · [Protocol frozen before opening the evaluation](protocol.md)

Main already preserves completed answers at the time cap and can seat up to two extra workers after its initial three when a crash leaves an answer without agreement. Its rich text and file comparisons differ from this experiment’s exact answer grouping. The common-pool control applies its crash trigger with the same four seats and votes as the challenger. The actual archived after-body row is the original delivered report, independently regraded, including its original seat ordering. The repository’s separate tiny-cell cascade is another strategy: it escalates using label confidence, and its threshold calculation also receives the incumbent’s measured test accuracy. This pulse study fits no threshold and passes no grades into selection. [Current cap and crash-reserve implementation](../../../../team/solo.py) · [Pulse generation and grading](../../../exam.py) · [Existing confidence cascade](../../../cells_cascade.py)

The G50 engineering split had 27 eligible tasks. G51 and G52 contributed 128 fresh pulse questions. We excluded 71 file-producing, live-source, or other out-of-scope checks and two exact repeats of previously included prompts, leaving **55/128** unique deterministic text tasks. All 55 had four attributable candidate outputs. The archive’s individual verdicts and the independent rerun of the seeded exam checks matched on all 328 submissions across engineering and evaluation. The exam has known limits: for some numeric questions its checker looks for the required number in the output. It does not certify arbitrary prose. [Cohort by shard](cohort.json) · [48 original GitHub artifact IDs and SHA-256 digests](artifacts.json) · [G50](https://github.com/Arnav123-s/HiveMIND/actions/runs/44474079616) · [G51](https://github.com/Arnav123-s/HiveMIND/actions/runs/44525337919) · [G52](https://github.com/Arnav123-s/HiveMIND/actions/runs/44594712108)

## Reproduce

From the repository root, regrade the included small, losslessly compressed projection with the commands below. Selection finishes for all questions before the external assessment ledger is opened. The checked task makers reproduce every scored prompt byte for byte. Re-extraction also verifies all 48 original ZIP digests, reads the actual board answer events and recovers longer answers from archived stdout only when uniquely attributable.

```sh
python training/experiments/atlas/pulse/evaluate.py
# Optional: rebuild the projections from original Actions artifacts (with authenticated gh).
python training/experiments/atlas/pulse/extract.py --fetch --raw /tmp/hive-pulse-archives
python training/experiments/atlas/pulse/evaluate.py
```

GitHub Actions archives can expire. The included text panels and assessment ledger preserve the observed evidence used for replay. [Worker texts and timing](panels.json.gz) · [External assessment and actual reports](assessment.json.gz)

A separately frozen follow-up tested a narrower route that can actually undercut the ordinary after-body. On the complete G49 pulse, independently checking the first worker’s whole calendar or arithmetic answer saved 8 of 141 completed worker calls and retained the same 49 correct, seven wrong and eight withheld deliveries. [Separate one-worker study and calculator-only control](one_checked/README.md)
