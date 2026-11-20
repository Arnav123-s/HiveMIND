# What the file publisher actually delivered

The original and checked default publishers each delivered **33 correct files, nine wrong files and 12 abstentions** across all 54 table inputs. None of their outputs changed on this panel. The updated publisher checks exact decimal arithmetic and some explicit unit mismatches. It still wrote ticket totals when the user asked for unresolved tickets and visit totals when the user asked for revenue. Both questions lacked the necessary data. These two questions across two editions account for four of the nine wrong files. [Every actual file's decoded value and digest](results.json)

| Public CLI and evidence supplied | Inputs | Correct file | Wrong file | Answerable, withheld | Appropriate hold |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original, rules only | 54 | 33 | 9 | 10 | 2 |
| Checked, rules only | 54 | 33 | 9 | 10 | 2 |
| Checked, one externally labeled example | 48 | 36 | 0 | 12 | — |

For the example arm, each question used the same previously frozen third-table worked example. It covered 48 answerable inputs. The remaining six inputs had no definable answer to supply as a demonstration. On the shared 48, the rules-only path gave 33 correct, five wrong and ten withheld. The example path gave three more correct files, five fewer wrong files and two additional abstentions. [External teacher and original trial](../README.md)

The independent runner invoked the actual CLIs in 156 fresh working directories, using the preregistered 27 questions and two input CSVs per question. Each request gained the same explicit delivery instruction, “Save the answer as result.json.” Every answer created exactly one file with that name, valid JSON and bytes matching the advertised contents. Every abstention left its output directory empty. The original publisher's verdict and value matched the previously frozen rules on all 54. The checked publisher was developed after the original benchmark, so this audit measures end-to-end behavior on the known panel.

From the repository root, run `python training/experiments/verified_growth/transfer/checked_delivery/audit.py --out /tmp/hive-all-files.json`. The runner verifies source and fixture digests, collects all delivered files, then scores them against the independent SQLite-derived keys. [Runner](audit.py)
