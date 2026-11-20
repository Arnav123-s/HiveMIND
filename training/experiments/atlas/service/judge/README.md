# Independent mixed-service evaluation

The combined model-free CLI delivered 10 of 12 answerable requests. The stock chat local prepass delivered one. Both withheld all six requests with insufficient information, unsupported conventions, or incompatible units. Nine cases improved and none regressed. Neither arm returned an incorrect value. The two misses were plainly answerable paraphrases about a weekday and a parcel quote.

| Original 18 requests | Correct deliveries | Wrong deliveries | Missed answerable requests | Appropriate withholds | Cold wall time | CPU time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Stock local prepass | 1 | 0 | 11 | 6 | 12.36 s | 12.20 s |
| Combined CLI | 10 | 0 | 2 | 6 | 122.26 s | 120.03 s |

Both arms ran in fresh processes with one CPU, identical bank and 60-second limit. The stock comparison exercises the normal local prepass without model fallback. These cold costs include interpreter startup and guest compilation. Median wall time on the original combined CLI was 3.29 seconds for the five calculator requests with a matched route and 13.52 seconds for six shipping-route requests. Two additional terminal invocations printed exactly `Wednesday` and `430 cents`. A requested pooled quote would have coincidentally matched the per-parcel price for that order. The CLI checked the selected convention and withheld it because the supplied bank contained only the per-parcel version.

The independent judge fixed the wording, expected answers, eligibility and scoring rules before seeing the combined CLI. The fixture scan found zero normalized prompt matches among 63,429 string values in 366 earlier tracked JSON artifacts. Eighteen purposefully chosen requests cannot establish a general error rate. [Protocol](protocol.md) · [Fixture hashes](commitment.json) · [Overlap scan](overlap.json) · [Raw replies, values, timings and terminal output](results.json)

## Reproduce the original run

Use the original revision to exercise the same entry points and certificate. Both subsequently changed. Install the project's Python dependencies and point the runner at an installed CPython WASI SDK containing `python.wasm`. The runner checks the source and fixture hashes before proceeding. Run from a checkout of the repository on Linux.

```sh
git worktree add --detach /tmp/hive-original-service ccd34f5702a67be64c0a5a3859e998f559b7d03a
cd /tmp/hive-original-service
python training/experiments/atlas/service/judge/run.py \
  --sdk /path/to/fieldwork-wasi \
  --service-sha256 2dfd7f08ca2c8574604b879cba808c52e604c2c6fb358f1391cbb0e3f9cfaea4 \
  --out /tmp/hive-original-service-results.json
```

The replay alternates arm order, records 36 scored replies and two extra unstructured terminal replies, and needs no model weights. Compare raw replies and verdict counts. Elapsed and CPU time depend on the host. [Pinned source digests](tested-source.json) · [Comparison design](comparison.md)
