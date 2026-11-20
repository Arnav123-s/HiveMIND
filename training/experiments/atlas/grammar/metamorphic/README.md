# Can consistency alone select a duration module?

Both recovered G52 modules passed every consistency check and then answered all 60 independent duration questions correctly. A deliberately wrong clock with **61 seconds per minute and 61 minutes per hour also passed all 24 checks**, but answered only the eight seconds-only questions correctly. [Sealed selection](selection.json) · [External grades and raw outputs](grade.json)

| Module | Consistency checks | Independent answers |
|---|---:|---:|
| G52 h20000523_03 | 24/24 | 60/60 |
| G52 h20000527_03 | 24/24 | 60/60 |
| Authored base-61 clock | 24/24 | 8/60 |
| Authored clock that wraps at midnight | 20/24 | 44/60 |

The relations checked both directions of a round trip and addition of disjoint unit fragments. They caught four failures of the wrapping clock. They specify that parsing and formatting agree and can add quantities, while leaving the exchange rate between units undetermined. The predeclared SHA-256 tie-break selected a correct module when choosing among the two genuine candidates and selected the base-61 clock when all four candidates competed. Digest ordering makes the decision reproducible. It provides no evidence of correctness.

Each module ran in the repository's fuel-limited CPython WASI guest. Selection recorded every candidate digest, relational output and decision before a separate command imported the frozen 60-case key. The author of this experiment had written that independent panel for the parent recovery study. No native model ran. The four modules were chosen to test a specific failure mode and give no estimate of its ordinary frequency. [Protocol](protocol.md) · [G52 archive](../../module_recovery/archive.json) · [Independent holdout](../../module_recovery/holdout.py) · [Control sources](controls/)

From this folder, with the repository's WASI SDK installed and wasmtime in the Python environment:

```sh
python study.py select --sdk /path/to/wasi --output /tmp/duration-selection.json
python study.py grade --sdk /path/to/wasi --selection /tmp/duration-selection.json --output /tmp/duration-grades.json
```
