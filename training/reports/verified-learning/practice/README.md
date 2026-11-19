# One nightly practice program qualified for everyday use

A member running `t80+g47trunk` wrote a function to merge overlapping or touching closed integer intervals during generation 48 practice. We extracted its first submitted `merge` definition byte-for-byte, kept its original comments, and added a checked JSON entry point. It passed 4 public examples and 72 fresh qualification cases in CPU WebAssembly. A second checker then confirmed all 1,110 previously unseen cases in a bounded exhaustive panel. [Original training run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44371926721) · [Recorded result](result.json)

The source is submission `members/work/member1_1.py` from practice task `h10004810_02` in artifact 14462321019, `practice-work-10.zip`. The bundled ZIP contains the original worker submission, task, and practice receipt. The manifest identifies each by SHA-256 and also identifies the original full archive. The original exercise asked for two functions. We qualified only `merge`. [Provenance](manifest.json) · [Original files](training-record.zip)

## Run it

Set up the fieldwork WebAssembly runtime with `python scripts/setup_fieldwork.py`. To reproduce the recorded result offline in a temporary bank, run this from the repository root, using a Python environment with `wasmtime` installed.

```sh
python training/reports/verified-learning/practice/reproduce.py
```

The checker accepts `--sdk PATH` for an existing compatible CPython WASI distribution. To qualify and keep the program in your local skill bank, unpack the included practice record and import the task.

```sh
python -m zipfile -e training/reports/verified-learning/practice/training-record.zip /tmp/hive-practice
./hive practice-import --practice-task-dir /tmp/hive-practice/practice_10004810/h10004810_02 --contract intervals.merge
./hive --once 'Run merge_intervals with [[4,8],[8,10],[12,13]]'
```

That input produces `[[4,10],[12,13]]`. The import draws a new qualification seed by default. Pass `--seed 6084116933787393751` to repeat the recorded draw. An explicitly specified `--bank DIR` selects the destination. For a future local training run, enable the same qualification path using `python training/grow.py practice --practice-bank DIR` or set `HIVE_PRACTICE_BANK=DIR`. A matching interval practice task records its qualification receipt in `practice.json`. Training is a separate operation from replaying or importing this record.

## What was measured

The adapter chooses the first plain top-level `merge` definition in member and submission order, before it scores any candidates. It uses the practice receipt only for model attribution. Its independent qualification decides admission. Candidate code receives inputs inside the existing WASI runtime. Sibling functions and the demonstration printed at module scope are excluded from the extracted method.

The qualification checker joins connected components in a graph of overlapping intervals. Its fresh inputs include unordered pairs, singleton points, large signed endpoints, containment, touching, duplicates and one-unit gaps. The second checker represents coverage on the half-integer lattice. It enumerates ordered sequences of up to three intervals with endpoints in `{-2,0,1,4}`, removing inputs seen in qualification or public examples. Distinct intervals such as `[1,2]` and `[3,4]` stay separate. [Checks and replay](reproduce.py)

This demonstration establishes reuse for one published contract from one archived training submission. The adapter accepts integer pairs in ascending endpoint order and handles only the interval-merging practice contract. The extra panel is exhaustive within its stated finite domain. The nightly hook is opt-in, and this experiment made no checkpoint or hosted workflow change.
