# What the worker archive can recover

On 12 independently written handoff scenarios, 40 workers produced **18 regular files explicitly requested by the user**, counting each seat's copy. Fourteen file digests were distinct. Every available file matched the hash recorded by the stock handoff when the worker finished. The original growth workflow's actual diagnostic upload patterns retained **none of the 18**. The proposed evidence collector independently recovered **18/18**, with each file stored under its source seat. Using the exact proposed gate command and its new upload glob, the reconstructed gate ZIP contained all 18 files and all 11 expected manifests. The manifests recorded the other 28 requested seat/file slots as missing. There were 11 named-file requests and one text-only request.

User-visible outcomes stayed **four correct, two wrong and six withheld**. We checked the public directory, report and decision bytes before and after collection. The archive describes what each worker produced and makes no judgment about its correctness. [Frozen protocol](protocol.md) · [Worker snapshots and independent specifications](panel/) · [Receipts](results.json)

| Stock handoff example | What happened before capture | What the new record contributes |
| --- | --- | --- |
| One worker wrote a correct museum placard | Other workers supplied no evidence. The system withheld the placard. | The one real file survived under that worker's seat. |
| Two workers agreed on the wrong kettle setting | Both enabled a beep the user wanted disabled. The stock system shipped it. | Both wrong copies were preserved. Agreement did not change their meaning. |
| Two files requested for an entrance display | One worker wrote the HTML and another wrote the welcome note. The system withheld the incomplete submissions. | Each partial submission stayed separate, with the missing item recorded. |
| Two different herb-list ZIPs | One archive had the correct readme and the other had an erratum. The stock system withheld. | Both binary ZIPs remained independently inspectable. |
| Ordered loading-bay TSV | Stock delivery sorted two workers' identical unordered rows and returned the right file. | The raw worker rows survived, distinguishable from the sorted file the user received. |
| Reused directory | An old counter.md remained physically visible after a new decline, although the new returned file list was empty. | The collector consulted only the newly recorded seat directories and excluded the old counter. |
| Text-only request | Stock returned the requested word and also published an unrequested worker note. This failed the strict no-file expectation. | No evidence directory was needed, and the collector did not remove the note. |

Three of the six declined jobs contained a complete worker bundle matching the externally held key. The other declines contained a missing bundle, a split bundle, or an incorrect sole file. This distinction is visible to the evaluator after the fact. Promoting any candidate containing a plausible file would also promote wrong work.

## Reproduction

The runner replaces the member's model generation with predefined local worker outputs and actual regular files. It invokes the public `solo.first` path, including ordinary seat scheduling, current-directory isolation, file inspection, pair selection, ordering, publication and returned claims. Each case has a fresh temporary repository-shaped tree. It then creates a local ZIP using the actual positive gate artifact selection patterns from the unmodified workflow, executes the proposed workflow's actual `python -m training.member_evidence` command against the recorded task/member layout, reconstructs the updated gate ZIP, and checks each returned file against the worker's independently supplied bytes. The baseline archive had real member driver scripts and reports. The workflow file selection was reconstructed locally. [Executable audit](run.py)

The stock checkout must be pinned to `4cbd41cb2e27d263f102801c0a7a008268d0b1aa`, and the runner verifies its source files against Git. The evidence collector used in this test has SHA-256 `42635401038b4122dd8553e71c97e70b1ea672e25b4f8d823765d59c8a99b9a4`. The independent scenario generator and keys were sealed before the collector was inspected.


Use a clean stock checkout at that commit and a separate checkout of the standalone evidence proposal with its workflow. The audit only writes its result and temporary working directories.

```sh
python training/experiments/verified_growth/delivery_confirmation/run.py \
  --stock /path/to/stock-4cbd41c \
  --candidate /path/to/evidence/training/member_evidence.py \
  --workflow /path/to/evidence/.github/workflows/grow.yml \
  --out /tmp/hive-neutral-handoff.json
```

The original code and workflow comparisons are pinned in the receipt. The default candidate digest selects the initially frozen implementation. To audit a later review revision, pass its independently obtained digest with `--expected-candidate-sha` and specify a separate output file.

A second run reproduced the complete initial receipt byte for byte. We also repeated the public gate command on the reviewed error-handling revision. Every per-seat file record, copy, grade and archive member matched. Only the recorded candidate source digest changed. [Review revision recheck](review-recheck.json)
