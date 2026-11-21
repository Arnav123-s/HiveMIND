# Which G58 training examples the token limit removed

All 20 hosted slice counts reproduce exactly from the retained G58 row archive, the t80 tokenizer and the trainer at the run commit. The 1,152-token limit excluded **1,512 of 77,523 slice presentations (1.95%)**. Those copies represent **157 distinct exchanges, 81 exact requests and 11 task kinds**. A request can have several different outputs or repair turns, and a training exchange can be selected for several slices.

| Excluded exchange | Distinct exchanges | Slice presentations |
| --- | ---: | ---: |
| First program | 71 | 580 |
| Correction after feedback | 35 | 280 |
| Parent-specific repair produced by the trainer | 32 | 500 |
| Completion turn | 19 | 152 |

Across all shards, the trainer selected 8,638 distinct exchanges for 3,206 requests before the length check. **Nine requests lost every available exchange**. Six asked for server-log classification, two asked for several tasks at once, and one asked for contact extraction. The other 72 affected requests retained an eligible alternative. In 38 cases that alternative included a first program.

The largest groups were multipart tasks (73 exchanges, 796 presentations), log counting into a file (28, 231) and grid regions (21, 199). Of all 157 excluded exchanges, 124 were offered eight times. The current-generation contribution was one first program from G58, seen on every slice. Thirty-two repairs inherited from earlier generations accounted for a further 500 presentations. The remainder were older training examples. Full lengths of the excluded exchanges ranged from 1,155 to 2,872 tokens.

The trainer removes duplicate exchanges, holds back lessons and forms its shard before tokenizing. It counts the instructions, input, dialogue and target together. On longer correction dialogues it may shorten an earlier assistant program, while preserving the input request and target. Every counted exclusion still exceeded the cap after the trainer's existing shortening attempts. External reading and judged pairs enter later. These counts describe pre-training admission. The cancelled run did not publish evidence of which individual admitted rows it reached.

The identity table gives SHA-256 hashes of each exchange and exact request, its generation and seed, the full unshortened prompt and target lengths, its slice multiplicity and whether a shorter alternative for that request passed admission. Exchange identity follows the trainer's duplicate equivalence, omitting the system message and including all later messages, output and rejected response if present. The replay tokenizes the actual normalized system message. The archived source is GitHub Actions artifact 14689844285, with hashes in the receipt. [Per-slice comparison and all 11 kinds](audit.json) · [Affected exchanges](excluded.csv) · [Original run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44857277686)

## Can the two shortest exclusions actually train?

The two shortest excluded first programs were both 1,155 tokens. The original encoder rejected both at 1,152, then accepted the identical token sequences at 1,155. These are archived practice turns. The small trial used both unedited source lines, the G58 source child's parent adapter, the G55 trunk and the production t80 training code.

| Original first program | Prompt tokens | Target tokens | Guard mode | Full forward and backward |
| --- | ---: | ---: | --- | ---: |
| G58 log counts | 1,000 | 155 | Checkpoint | 147.725 s |
| G51 palindromes and grid regions | 349 | 806 | Checkpoint | 156.683 s |

The four-thread float32 CPU completed two passes and one accumulated optimizer update, with zero memory skips or swap. The resulting 196 tensors differed from the initialized adapter at all 16,973,824 scalar positions. Peak process RSS was **10.83 GiB**, minimum independently sampled cgroup-adjusted headroom was **3.85 GiB**, and loading through GGUF export took **397.745 seconds**. The worker kept its 2 GiB guard reserve on a 16 GiB machine. Both tasks already had low training loss. These two completed passes provide no estimate of held-out accuracy or full-generation runtime.

The initial preflight stopped before the base finished loading. Advising the OS to discard clean cache pages from the four immutable model inputs alone released 6.36 GiB. The successful retry repeated that file-scoped advice during loading. It used the same weight bytes, training kernels and one-GiB emergency stop. The original run used the default 1,152 limit and published no trained adapter. [Frozen protocol](PROTOCOL.md) · [Input identities](protocol.json) · [Memory preflight](preflight.json) · [Two-row native receipt](native.json)

## Reproduce

Run with the repository training dependencies, the exact GitHub artifact ZIP, the pinned local unpacked t80 snapshot and the G53 source-parent and G55 trunk adapters. The model and adapter digests are recorded in the protocol. The native worker writes the adapter into a new scratch directory. It does not modify the body or call an external service.

```sh
study=training/experiments/hosted_generation/lengths
python "$study/audit.py" --archive "$archive" --tokenizer "$snapshot" --summary /tmp/lengths-summary.json --identities /tmp/lengths-excluded.csv
python "$study/native.py" --archive "$archive" --adapters "$adapter_dir" --hf-home "$hf_cache" --runtime "$ternary_home" --scratch "$new_directory" --release-weight-pages
```
