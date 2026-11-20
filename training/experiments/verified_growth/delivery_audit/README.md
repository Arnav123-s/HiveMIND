# Where two G52 worker files stopped

**The requested file existed in the third worker's directory in both jobs.** Both earlier workers repeatedly imported a module that did not exist and returned no answer. On turn two, the third worker's script ran successfully. The ordinary runtime wrote `durations.py` from its declarations, recorded “durations.py saved from the program's functions,” and received the worker's two printed answers. The hive reported an unconfirmed job and published no file. The report listed only the missing files from the first and second workers. [Original events, digests and normal handoff replay](results.json)

| G52 job | Member 3 actually printed | Reconstructed member file | Final published file |
| --- | --- | --- | --- |
| h20000523_03 | 36228 and `1h` | 459 bytes, SHA-256 starts `83af6f54` | None |
| h20000527_03 | 72268 and `1m` | 462 bytes, SHA-256 starts `ee6373e9` | None |

The original run was revision `136e888`. The implementation wrote the declarations to the named file **before** recording the module event. The exam separately copied each worker's own working directory for grading. Its module check required the named file to exist, ran its private tests and checked the printed answers. The later examiner passed member 3 on both jobs, and graded the root delivery “no durations.py saved.” Those private results were unavailable when the hive decided whether to send the file. [Module writer](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/solo.py#L308) · [Member grading](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/training/exam.py#L329) · [Exact official file requirement](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/training/kinds/h_module.py#L207)

## Generation, selection and publication

1. Each worker runs in its own directory. The runtime records the request's named files, their byte hashes and the worker's stdout in local member records. The board writes individual worker events to SQLite and JSONL. Its artifact registry is a separate interface; the solo worker events do not automatically publish a draft file. [Worker outcome recording](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/solo.py#L762) · [Board events](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/board.py#L44) · [Board artifacts](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/board.py#L116)
2. The chooser requires an agreeing peer. Python source may legitimately differ, so Python files are excluded from its ordinary file-content agreement path. The two failed workers supplied neither stdout nor a file. This left member 3 without a witness. The candidate had passed the file-presence check. [Peer comparison](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/solo.py#L680) · [Winner selection](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/solo.py#L707)
3. The report includes per-member file issues, so the only member with a file disappears from the text. On a decline the result's work pointer falls back to the first worker's directory. The outer handoff starts with an empty file list and copies requested bytes into the user's work directory only for an agreed winner. The copy operation was never reached. [Decline report](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/solo.py#L836) · [Returned metadata and publication](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/solo.py#L866)
4. The Actions artifact whitelist kept the worker scripts, stdout/stderr, events, public report and exam grade. It omitted the named worker module and local member JSON manifests. Its ZIP alone cannot provide a historical byte attestation for `durations.py`. Replaying the ordinary module writer on each successful turn-two script gives published Atlas reconstruction bytes exactly. Thus the duration-specific Atlas path qualified a pre-existing candidate in a retrospective experiment; its checked-in files supply no evidence that the general writer needed replacing. [Uploaded paths](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/.github/workflows/grow.yml#L816) · [Atlas qualification implementation](../../atlas/module_recovery/recover.py)

## Why a blanket publishing rule fails

In a neutral control, the request asks for `scale(x)` returning twice its input and the printed value at zero. One member supplies `return 0`; another supplies `return 2*x`. Both print zero. The ordinary handoff accepts, selects member one and copies its **wrong** module. Both Python files are present and have distinct digests, but the file inspector compares parsed contents for tables and JSON; a Python file contributes a byte hash alone. Matching printed output on one example supplied the accepted witness. A lone wrong constant implementation is withheld exactly as the good G52 singleton was. A pair of identical correct implementations is published. These controls exercise the normal selection and staging code and use fixed, human-authored worker outputs. [Control receipts](results.json) · [Output inspection](https://github.com/Arnav123-s/HiveMIND/blob/136e8880243a533299448fe8505ef08194d5bd18/team/deliverables.py#L321)

A general handoff can keep and identify the exact isolated candidate bytes, origin, visible checks and reason for withholding them. That fixes discoverability and enables independent checking, including on an archived run. It does not settle a program's behavioral correctness. Confirmed publication needs evidence appropriate to the actual contract. A digest establishes byte identity; a sample output, a worker's own assertion or another worker repeating that output establishes only the observed behavior. Exposing an unconfirmed candidate and counting a confirmed delivery are separate user outcomes.

## Does comparing extra user inputs resolve this?

On a separate panel of twelve neutral handoffs, sandboxed comparison disproved agreement for four pairs. Two of the ordinary chooser's selected files were correct and two wrong among those four. Requiring matching observations still shipped two wrong files. This experiment supplied no extra confirmed G52 deliveries. [Independent grades, counterexamples and reproducible comparison](probes/README.md)

## Reproduce

The runner validates the two original ZIP digests, feeds their observed worker outcomes to the existing `solo.first`, and exercises the normal module writer, file inspector, vote, result shaping and user-directory copy. The neural generation is supplied from the recorded outputs. It caps the replay at the original three seats and disables writing to long-term memory. Its two original reports match the published text exactly. No hidden answers are given to the handoff. From the repository root, provide the two original G52 gate artifacts as `14587903855.zip` and `14587642648.zip`.

```sh
python -m training.experiments.verified_growth.delivery_audit.inspect_run \
  --archives /path/to/original-gate-zips --out /tmp/hive-delivery-audit.json
```

[Original G52 workflow](https://github.com/Arnav123-s/HiveMIND/actions/runs/44594712108) · [Archive identities and digests](../../atlas/pulse/artifacts.json) · [Audit source](inspect_run.py)
