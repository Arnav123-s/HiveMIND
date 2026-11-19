# Can verified corrections help on a different work order?

The four donors are two corrected aggregation programs and two corrected boundary comparisons. A person authored the faulty drafts and corrected second drafts. The production work-order runner executed them in WASI, checked their public and qualification examples, and retained the successful programs. The inference count for every arm is zero. This study measures whether corrections travel to new source programs. Model generation is a separate experiment.

## Independent confirmation

With four supplied corrections in memory, HiveMIND completed **10 of 20** fresh contracts. The same system with repair learning disabled completed **4 of 20**. Learning added six correct contracts and lost none. Both arms preserved all three correct controls. Among the 17 faulty drafts the learning arm completed seven, including one decoded-input fix shared with the baseline. The other six carried an edit learned from the donors. Ten of 20 contracts still received no files.

| Method | Complete contracts | Correct private results | Wrong | Withheld | Candidate edits tested | WASI batches / inputs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Production, learning off | 4/20 | 64/320 | 0 | 256 | 1 | 29 / 197 |
| Production, learning on | 10/20 | 160/320 | 0 | 160 | 10 | 51 / 387 |
| Human-supplied aggregation rule | 8/20 | 128/320 | 0 | 192 | 10 | 47 / 341 |
| Human-supplied boundary rule | 4/20 | 64/320 | 0 | 256 | 1 | 29 / 197 |
| Both human-supplied rules | 9/20 | 144/320 | 0 | 176 | 11 | 50 / 369 |

The fixed two-rule diagnostic solved exactly the six contracts gained from learned rules and the three controls. Its menu omitted the decoded-input fallback. The difference between 10 and 9 therefore provides no evidence of an advantage over a hand-designed policy with equivalent operations. Both production arms received the same 20 draft callbacks and maximum of two edits per draft. The learning arm used 190 more input evaluations. Per-order shared-machine timings are in the raw receipt. [Production results](final-results.json.gz) · [Fixed controls](final-fixed.json.gz)

| Predeclared task group | Learning off | Learning on |
| --- | ---: | ---: |
| Aggregation | 0/3 | 2/3 |
| Threshold boundary | 0/4 | 1/4 |
| Distracting edit sites | 0/2 | 1/2 |
| Ambiguous public examples | 0/1 | 0/1 |
| Distribution or representation shift | 0/2 | 2/2 |
| Decoded dictionaries | 1/2 | 1/2 |
| Unrelated faults | 0/3 | 0/3 |
| Already-correct drafts | 3/3 | 3/3 |

Eight edits in the learning arm fit the public examples. Seven qualified and delivered. A lecture-chair repair matched all five public examples but failed all seven qualification examples. The runner withheld all sixteen chair orders. It delivered no wrong file anywhere on this panel. The three control solve functions retained their original syntax trees in both arms. Their saved solver files also include retrieved helpers or a newline, so their full-file hashes differ from the standalone draft bytes.

On the six earlier related contracts, the updated implementation now completes **6/6** and delivers **120/120** correct files. The two-rule fixed menu also completes 6/6 there. Both production arms still withhold the median and compound orders, preserve 4/4 old programs on 48 fresh jobs, and deliver 20 wrong files on the weak audit. The two audits show that independent inputs need to cover the behavioral difference that matters.

## What the first blind study found

The original learner completed **3 of 6** new related contracts with **60 of 120** correct private files. Disabling learning completed **0 of 6** and withheld all 120 files. Both arms completed all four training contracts, both correct controls, and all four earlier-contract revisits with 48 fresh correct files and no extra drafts. Both withheld the unsupported median and the compound two-edit order. Both delivered **20 wrong files** on the weak audit. Its public and qualification inputs always made counting sacks indistinguishable from adding their weights.

Only the aggregation rewrite had two recognized donor pairs. One threshold donor accessed a literal field in a dictionary. The initial expression grammar could not recognize that correction. A fixed, human-supplied aggregation rule and a fixed, human-supplied boundary rule each completed 3 of 6. The learning arm and baseline each received the same six authored proposals and limit of two edits per draft. Learning used 16 WASI executions and 131 input evaluations on those orders. The baseline used 6 executions and 30 inputs.

The full first-run file is [initial-results.json.gz](initial-results.json.gz). Its decompressed SHA-256 is `170e174a875e540cb72b05a0d5e70ad79f7dd2de345a7874fdf2c8ab22c83b19`. It contains the observed engine hashes, individual file outcomes, chosen programs, donor digests, qualification counts and measured WASI calls. Field-read support was added after that result was disclosed. The six original orders are development cases for the later version. A separately preserved pre-field-read revision added a requirement for distinct donor qualification corpora. A replay on that revision reproduced both arms’ summaries, every file outcome and every selected solver SHA across 38 order-visits. [Pre-field-read replay](first-engine-recheck.json.gz)

The optional [qualification challenge](challenge.md) later withheld all 20 bad files on that exposed audit. On a separate blinded six-order panel it prevented zero of eight wrong files and withheld six correct files.

## Experimental design

The first panel has 15 named contracts. Each uses five public examples, seven separate qualification examples and twenty private jobs. Four additional batches revisit the earlier donor contracts with twelve fresh jobs each. [freeze.py](freeze.py) defines the input draws, separate reference computations and distinct candidate sources.

The confirmation panel was authored independently of the donors, first panel and implementation body. It has 20 new contracts with five public examples, seven qualification examples and sixteen private jobs each. Every fresh contract receives a single authored draft. Its author predeclared the primary endpoint as a complete contract with seven correct qualification answers and sixteen exact private deliveries. A partial result, wrong result and missing file get distinct counts. The 320 private rows are clustered within 20 contracts. [Confirmation protocol](confirmation/protocol.md)

Each production arm starts from an empty bank, qualifies its own copies of the donors, then applies every fresh request to a copy of that same arm's trained bank. Transfer on one new request cannot teach the next. The last novel bank that actually added a fully correct program is used for old-program revisits. In the final replay this was the tower-lamp control in both arms. Each bank held the four original workers and this new worker. The retention check measures one additional acquisition. The grader passes private inputs to `work()`, reopens every delivered `answer.json`, and compares its JSON value with a separate key. Only public examples can choose or rank candidate repairs. The qualification inputs can reject the selected program. Qualification examples stay out of the proposal callback. In the new engine both arms have the same handcrafted arithmetic and decoded-input candidates. Only the learning arm receives the extracted rules.

Three human-specified diagnostics use the same WASI guest, public-first placement rule, qualification gate and two-candidate cap. One has only `len → sum`, another has only `> → >=`, and the third alternates the rules across available source sites. The two-rule menu tries the earliest site of each applicable rule before a second site. These diagnostics can match a wider range of AST operands than the guarded production learner. They run private values directly in the guest, whereas the two production arms also exercise saving programs and exporting real files. [Fixed-rule implementation](fixed_rules.py)

## Reproduce

Run from this repository root. Installation downloads a pinned CPython WASI build and installs Wasmtime 36.0.0. Use a fresh SDK directory if installing the guest for the first time.

```sh
export HIVE_FIELDWORK_SDK="$PWD/.fieldwork-wasi"
python scripts/setup_fieldwork.py
p="$PWD/training/reports/verified-learning/experiment"
study_root=$(mktemp -d)
measured="$study_root/measured"
git worktree add --detach "$measured" 1414d49
gzip -dc "$p/g48-to-measured-engine.patch.gz" | git -C "$measured" apply
.venv/bin/python "$p/replay.py" --checkout "$measured" --sdk "$HIVE_FIELDWORK_SDK" \
  --confirmation-stream "$p/confirmation/corpus.json.gz" \
  --confirmation-keys "$p/confirmation/keys.json.gz" --output paired-results.json
.venv/bin/python "$p/fixed_rules.py" --checkout "$measured" --sdk "$HIVE_FIELDWORK_SDK" \
  --confirmation-stream "$p/confirmation/corpus.json.gz" \
  --confirmation-keys "$p/confirmation/keys.json.gz" --output fixed-results.json
```

The patch reconstructs the exact measured engine from the published G48 baseline. Supplying `--checkout .` instead runs the implementation in the current working tree. Elapsed seconds vary by machine. All corpora and keys are independently regenerable. Run `python "$p/freeze.py" --out /tmp/original-corpus` in a fresh directory for the first panel. Copy `$p/confirmation/make_panel.py` into a fresh directory and run it for the confirmation panel. The checksums in the raw receipts and [SHA256SUMS](confirmation/SHA256SUMS) identify the decompressed JSON bytes.

To reproduce the behaviorally equivalent pre-field-read check, run `gzip -dc "$p/release-to-pre-field.patch.gz" | git -C "$measured" apply` after the measured-engine run. Omit both confirmation flags when running `replay.py`. To reconstruct the exact first learner at SHA-256 `ad4ce1e01ff98e3a52e77c8d45270021a59e241761da223c21d1ecd5ab6f4e8a`, apply `gzip -dc "$p/pre-field-to-observed-v1.patch.gz" | git -C "$measured" apply` after the pre-field patch.
