# A recoverable parser delivery in generation 48

A user asked for a small arithmetic language. The original hive sent an unconfirmed answer. Four newly written checks of the stated contract scored the three workers' final recorded attempts **1/4, 4/4 and 0/4**. The sole qualifier, worker 2, printed **10** in its original run and copied its own script to the requested calc.py module. Its recorded independent exam grade was a pass. The replay made zero new model calls. This was a retrospective test on one task, and the result delivered in the historical run did not change.

## Evidence and limitations

The grade archives contain pass/fail labels. The separate work archive contains the worker scripts, the original task and execution logs. This package includes exactly the three final source attempts, the task, four probes, and the observed replay results. The manifest gives GitHub's full-archive SHA-256, the archive entry for every included original, and its extracted SHA-256. The saved source filenames use a text extension. [Original run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44371926721) · [Work archive 14482488264](https://github.com/Arnav123-s/HiveMIND/actions/runs/44371926721/artifacts/14482488264)

The selector takes the highest numbered archived attempt per worker and requires exactly one to pass every probe. The probes were fixed from the specification before opening any worker source. The analyst already knew the members' grade labels from an earlier archive review. The selection code uses only public contract examples and observed behavior. A prospective trial should freeze checker construction before anyone sees the outcome labels.

All three final scripts contain the instruction to copy their own bytes to calc.py. Worker 2 executed that instruction successfully and its original stdout was 10. Worker 1 raised a TypeError on evaluation, and worker 3's last attempt had a SyntaxError before its copy could run. The final on-disk modules themselves were not archived. The pilot compares the final source attempts, not a reconstructed module. For the selected worker, copying itself establishes which bytes it produced. Agreeing with four examples by itself does not guarantee correctness on arbitrary expressions.

## Reproduce

Run from this folder in the research checkout. The replay uses Python 3.13.9 inside Wasmtime, with a read-only Python standard library and a fixed instruction budget for each candidate. No model, GitHub token or source archive is needed to score the bundled bytes.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install wasmtime==36.0.0
curl -fL 'https://github.com/brettcannon/cpython-wasi-build/releases/download/v3.13.9/python-3.13.9-wasi_sdk-24.zip' -o wasi.zip
echo 'f974d681668b8a51bf548474c9999630fe83a316155a4e937eaff57ea3ea4f39  wasi.zip' | sha256sum -c -
unzip -q wasi.zip -d wasi
python reproduce.py --sdk wasi
```

To authenticate the source against the original work archive while it is available, download artifact 14482488264 via GitHub, then pass its path to the same command.

```sh
python reproduce.py --sdk wasi --archive /path/to/gate-work-after-3.zip
```

The selector should report worker 2. The three per-worker pass vectors are [true, false, false, false], [true, true, true, true], and [false, false, false, false]. Execution times depend on the CPU. The replay uses the [existing guest harness](../../../../training/experiments/fieldwork/guest.py).
