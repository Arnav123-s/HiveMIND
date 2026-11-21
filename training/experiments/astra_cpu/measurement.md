# What CPU training recovered

Two full T80 CPU training runs began with the actual G56 sources-slice parent and trunk. They trained on the same two archived G56 responses in the same order and exported a 38 MiB GGUF. Chunking the answer projection reduced the long update's process RSS peak by 0.36 GiB. It took 3.94 seconds longer. The 196 final FP32 adapter tensors, containing 16,973,824 values, were bit-for-bit identical across runs. The adapter actually changed from its inherited starting state, with a squared update norm of 0.216936. The exported GGUF SHA-256 was `e4ff7f8fa51dbf0baca19d51732dfb1e29b724c7d601ae7cad36d6084c972f28` in both arms.

| G56 task | Tokens, total / answer | Stock peak process RSS | Chunked peak process RSS | Stock wall / process CPU | Chunked wall / process CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Find sentences and count their words | 475 / 188 | 12.158 GiB | 11.801 GiB | 62.81 / 117.58 s | 66.75 / 128.54 s |
| One-sentence pool closure summary | 198 / 29 | 10.420 GiB | 10.431 GiB | 31.61 / 53.22 s | 37.23 / 70.08 s |

The long answer used a maximum projection of 32 positions per block, down from 189. The 29-token short control took the stock path in both arms. Recorded training losses were 0.0306 and 0.0308 in both runs. The complete workers took 204.75 and 241.45 seconds including weight loading, parent/trunk mixing and file export. Process affinity and row selection were matched, but other processes shared the four-core host. Even the short control varied in CPU time. The per-worker process peak fell from 12.168 to 11.801 GiB. The whole cgroup's peak estimated nonreclaimable charge was 12.52 and 12.68 GiB respectively and included neighboring processes. These two updates measure training behavior and memory. They supply no user-task transfer or exam result. [Raw paired receipts](native-pair.json) · [Full tensor comparison](update-comparison.json) · [Projection routing](projection.json) · [Reproduction](native-replay.md)

## How the historical skip count was measured

The log line naming 563 refers to skipped **pass attempts** on G51 code slice zero. A subject could put the same row back and try it again. G55 and G56 show different counts. Each archive reconstructed exactly both the original number of slice rows and the logged post-encoding study size once externally obtained raw and judged examples were included.

| Real code slice zero | Archival shard rows | Encoded archival rows | External read + judged | Recorded completed passes | Recorded skipped attempts | Original static cap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| G51 (FP32) | 2,387 | 1,792 | 44 | 54 | 563 | 508 |
| G55 (16-bit) | 4,041 | 3,749 | 48 | 260 | 1,481 | 797 |
| G56 (16-bit) | 4,393 | 4,013 | 48 | 269 | 647 | 748 |

The G56 archive and job list also identify two training jobs that reached about 205 minutes and ended as cancelled: sources slice 0 of 2 and words2 slice 0 of 3. The code slice shown in the table succeeded. The log service returned `BlobNotFound` for both cancelled jobs, so their last row, memory profile and exact failure cause are unknown. [G56 sources job](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973/job/136466400966) · [G56 words2 job](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973/job/136466401072) · [All three code-slice logs](code-s0-logs.json)

Using the rounded amount of free memory logged at the start of training, the original fixed length cap plus guard admits 669 of 2,387 archive rows in G51. The candidate formula could admit 2,337 at that same moment, 580 through the ordinary path and 1,757 through checkpointing. Equivalent G55 figures are 3,741 → 3,943 of 4,041, and G56 figures are 3,946 → 4,295 of 4,393. These are single-snapshot calculations over unique archive entries. They do not replay the changing memory, curriculum order or repeated skips as the hosted trainer ran. [Full transition tables and sensitivity to rounding](admission.json) · [Original artifact hashes](archives.json)
