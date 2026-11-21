# Replaying verified work and retaining older bodies

An older trunk added one potential correct answer across 188 archived requests. Replay lost old program preferences in the equal-cost G55 → G56 proxy. Both mechanisms are opt-in. These measurements cover recorded programs and worker outputs. The release test still requires three consecutive generations with less than 1% regression on old kinds and improvement beyond 58/64.

## Training

Set repository variable `HIVE_SELF_REPLAY=1` and `HIVE_SELF_REPLAY_RATIO=2`, `3`, or `4`. A ratio of four requests four fresh target rows per verified replay row. The trainer keeps separate counts for completed row passes, distinct rows, and answer tokens by source, including in each joined slice. Time or insufficient distinct examples can change the realized dose. The CPU runner handles slices with replay enabled.

The source body comes from the accepted checkout. A replay row must name one of its exact actors, precede the current generation, carry a practice or dream seed and contain a successful program. New collection records whether the actor and numbered file matched a unique independent passing verdict. In older published rows, a positive for a non-agreeing member establishes that a member check was used. Team-only or conflicting evidence, reserved families, held-back questions and repeats of new questions are ineligible. Each slice samples up to 400 old questions, interleaved by kind. The trainer preserves its row repetition ceiling, memory guard, and outside-reading allocation. When either pool is absent the regular sampler continues.

On released G55 and G56 rows, 17 old questions passed the current checks, disjoint from the preference questions and their programs. We reran PR 132's frozen byte-based program ranker with the live row scheduler, a stable order, and 30,000 target bytes per updated arm. PR 132 used two or four **old** rows per new row. This test uses two or four **fresh** rows per old row, matching the published Self-Replay ratio. The ranker had a constant row-loss signal for its scheduler. It was asked to rank the individually correct existing program above a rejected one. [Method paper](https://openbmb.cn/en/blog/self-replay-fine-tuning) · [Per-arm exposures](replay-results.json)

| Fresh rows per replay | Old preferences with simulated decay | Old preferences without decay | New preferences in both |
| --- | ---: | ---: | ---: |
| Fresh only | 112/169 | 115/169 | 6/7 |
| 2 | 110/169 | 107/169 | 6/7 |
| 4 | 106/169 | 106/169 | 6/7 |

The follow-up uses original G53–G56 archives, three chronological updates and two separate old panels. The larger decline did not recur, while replay's share of the byte budget again exceeded its row share. [Three-transition retention study](chronology/README.md)

## Archive and seating

Set `HIVE_ARCHIVE_K=3` to measure both incoming and current trunks on the same four development requests before either gate arm runs. Each request has a normal independent checker, two model turns, a 180-second subprocess limit and empty memory. The requests use four practice families, share no normalized question with the released G56 training rows, and are excluded from training while the archive is enabled. The probes run in parallel on eight hosted jobs. Their wall-clock and hosted-runner cost have not been measured in a full generation.

Each gate arm freezes its candidate set before fresh and held questions. Only complete receipts with matching protocol, prompt, actor, and adapter digest qualify. A dropped proposal never enters the saved archive. Keep the accepted body plus up to two distinct earlier bodies that maximize joint solved questions on that same panel. A redundant historical body yields its slot. Each snapshot names its generation, DNA, full cell list and released trunk bytes. Before seating, files are fetched and checked by SHA-256. The trunk always takes seat one. A historical trunk can take seat two for a request in an organ where it alone among the pair had an earlier verified win. The hive's existing agreement and delivery checks still decide the answer. Missing measurements, weights, evidence for the request's organ or a restricted roster preserve ordinary seating. A quarter of the panel is one task, so choices carry substantial uncertainty.

The hosted issue chat uses the same `HIVE_ARCHIVE_K=3` setting. It loads the current trunk and the newest cell of each organ, plus up to two recorded older trunks when the incumbent and archived file hashes match. A request can seat one of those older trunks as its second worker on the strength of its earlier checked result for that organ. A missing asset leaves the usual workers available. A user-specified subset only seats historical workers explicitly named in that subset.

We also compared real recorded worker answers for six kept bodies with available full paired archives (G45, G47, G48, G49, G53, G55). Each matched request had two individual trunk grades, the new body's second worker grade, and identical question text across arms. The first four seed blocks identified which organs had an older-trunk win missed by the newer trunk. The last four blocks supplied the assessment. Repeated normalized questions were excluded within each body pair. These offline diagnostic splits never write to the production archive or affect a release. [Per-generation counts and input hashes](archive-results.json)

| Across six body pairs | Result |
| --- | ---: |
| Development requests | 191 |
| Separate assessment requests | 188 |
| Older trunk selected for seat two | 40 |
| Either ordinary worker correct | 148/188 |
| Either worker correct with the historical selection | 149/188 |
| Newly available / lost correct answers | 1 / 0 |

The one additional answer came from G45. The later five runs tied. The recorded historical trunk produced its answer at seat one. Moving it to seat two could change the answer. The counts measure candidate availability, and the recorded original systems actually delivered 140/188. There is no measured extra delivery or three-generation retention result.

## Reproduce

For `--measure`, extract `training/experiments/astra_retention/replay.py` from commit `7fb2786e2203676238fcac5b301d0c3e232570d7` on PR 132. The runner verifies the file's SHA-256. The two inputs are the released `all-rows` artifacts, each extracted to JSONL. The fresh archives are directories such as `g45/gate-before-1.zip` and `g45/gate-after-1.zip`.

```sh
python -m training.experiments.replay_archive.replay --measure /tmp/pr132_measure.py --g55 /tmp/g55-rows.jsonl --g56 /tmp/g56-rows.jsonl
python -m training.experiments.replay_archive.history /tmp/hive-astra-fresh-zips
pytest -q tests/test_replay_archive.py
```
