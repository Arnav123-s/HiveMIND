# Warm lexical recall on two synthetic catalogs

This comparison calls the public recall functions in two separate Python processes on the same generated data. Its baseline is Git commit `2ea296f5fc038eb0e7d5a17279021ffd43b68294`, with SHA-256 `c5847171fea91c86464e3ae2d00f65ec6914f785388015c44f023f98f2371829` for `team/engram.py`. The frozen file was extracted before the candidate optimization. Model inference and embedding retrieval are outside this test.

Both versions returned identical ordered names and activation scales for all **360 warm calls** (120 distinct catalog/query combinations across three repetitions) and all **18 mutation checks**. The first baseline-only run, a paired isolated-snapshot run and a second run from the working checkout produced the same answer digests. No native model ran. [Measured results](results.json)

| Catalog records | Original CPU for 180 warm calls | Indexed CPU for 180 warm calls | Speedup | Original cold lookup | Indexed cold lookup |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 128 | 943.3 ms | 96.7 ms | 9.75× | 10.78 ms | 3.77 ms |
| 1024 | 7,614.1 ms | 515.1 ms | 14.78× | 60.35 ms | 17.37 ms |

| Query family at 1,024 records | Original median | Indexed median |
| --- | ---: | ---: |
| specific | 39.170 ms | 0.247 ms |
| common | 39.625 ms | 1.710 ms |
| absent | 38.329 ms | 0.134 ms |
| lineage | 39.502 ms | 0.316 ms |
| tie_cutoff | 38.099 ms | 0.359 ms |
| integrity | 42.871 ms | 0.158 ms |
| label | 40.099 ms | 0.168 ms |

The speedup column divides total CPU time for the full warm mix. Family medians summarize individual requests. Queries with a zero cutoff may include entries with no overlapping terms, so totals include work that a sparse postings list alone cannot skip.

The catalogs hold 128 and 1,024 total records. Each contains ordinary tasks, mixed owners and bases, tied candidates, inactive records and verified and unverified label edits. Some weights have a SHA-256 index entry. Files contain small inert bytes and the routing code uses real filesystem metadata and content checks. Timings measure lookup for these files and this filesystem. They do not establish latency for loading large adapters or generating answers.

Each size gets 60 queries covering specific, common and absent terms, lexical ties at three score thresholds, top-k limiting, parent/child ownership, exact-task selection, verified label output and inactive or ineligible files. Each query runs three times after a cold lookup. The harness compares the actual ordered outputs and scales between versions, including empty results. Nine further checks exercise appended, changed, deleted, restored and folded weight files, and the optional shared weight. The same-size overwrite restores the original modification timestamp while changing content, to test whether recall rechecks integrity. [Harness](compare.py)

## Reproduce

From the repository root with Python 3, run these commands on a machine that can read and write temporary files. Each process pins itself to one available CPU on platforms supporting affinity. The reported clock counts process CPU time. Digest checks and ordering are deterministic, while CPU timings vary.

```sh
reference_dir=$(mktemp -d)
git archive 2ea296f5fc038eb0e7d5a17279021ffd43b68294 team | tar -x -C "$reference_dir"
python training/reports/domain-memory/recall/compare.py --reference "$reference_dir" \
  --candidate . --out /tmp/hive-lexical-recall.json
```
