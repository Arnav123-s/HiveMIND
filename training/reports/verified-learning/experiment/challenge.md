# Can a verified alternative flag a bad qualification?

In a fresh independent panel, the optional challenge prevented **0 of 8 wrong deliveries** and withheld **6 correct deliveries**. The default completed 4 of 6 orders and returned 28 correct and 8 wrong answers. With the challenge enabled, the same system completed 3 of 6, returned 22 correct and 8 wrong answers, and withheld 6. The observed benefit on the earlier weak audit did not carry over to these six orders.

| Independent order | Default correct / wrong / withheld | Challenge correct / wrong / withheld | Outcome with challenge |
| --- | --- | --- | --- |
| After-hours log | 6 / 0 / 0 | 6 / 0 / 0 | No qualified rival |
| Clinic break credit | 2 / 4 / 0 | 2 / 4 / 0 | No applicable rival |
| Food-bank cart count | 6 / 0 / 0 | 0 / 0 / 6 | A qualified alternative disagreed with the correct primary |
| Meal voucher total | 6 / 0 / 0 | 6 / 0 / 0 | Both qualified programs agreed on every actual job |
| Printed shelf labels | 6 / 0 / 0 | 6 / 0 / 0 | Rival failed the supplied examples |
| Stationery envelopes | 2 / 4 / 0 | 2 / 4 / 0 | The rival failed the examples, leaving the original error |

The cart receipt records primary answer 1 and alternative answer 2 for the first requested input. The programs passed the same four public and four qualification examples. Without a label on that request the verifier had no basis for choosing which answer was right. The external key identifies the primary as correct. The clinic draft's unsupported threshold expression and the envelope draft's unrelated error left all eight wrong deliveries intact. On the voucher batch both sources gave the same six results. The author's separate off-batch witness records a case that distinguishes their semantics. It was never supplied to the application. [Sealed protocol](challenge-confirmation/protocol.md) · [Per-order receipts and values](challenge-initial.json.gz)

The earlier exposed weak-audit order had a different outcome. Disabled, the original produced 20 wrong weight totals. Enabled, two qualified sources returned 11 versus 83 on the first job, and all 20 files were withheld. The two earlier informative control orders still produced 40 correct results. These three orders motivated the feature and are retrospective.

## What was measured

The application qualified the same four original correction donors once through real WASI, then copied that bank for each arm and order. Each job had one authored primary. Every fresh draft matched all eight supplied examples. Only the challenge budget changed between arms, from zero to two. The verifier applies corroborated learned edit rules to the already-qualified primary, checks each variant on the public and qualification examples, then stages the actual job results privately when rivals qualify. Disagreement returns the job, input and observed alternatives. A disputed work order produces no exported jobs or new bank entry. An agreed result can be delivered from the staged primary. Neither the private labels nor the verifier's alternatives teach new repair rules. No model ran.

The fresh panel had 36 actual jobs, grouped into six deliberately selected work orders. The default made 18 WASI calls with 84 input evaluations. The optional arm made 26 calls with 120 input evaluations. Its challenge receipts count 10 internal calls and 48 inputs. Reusing staged results removes two ordinary delivery calls, so the net overhead is 8 calls and 36 inputs. The tool can expose disagreement within its checked rules and budget. Agreement on a batch and absence of an eligible rival both permit errors.

## Reproduce

Use the setup instructions and measured-engine checkout in the [main study](README.md). Start from the measured engine before applying any pre-field patches. The first command adds the source snapshot used for the untouched six-order confirmation.

```sh
gzip -dc "$p/measured-to-challenge.patch.gz" | git -C "$measured" apply
.venv/bin/python "$p/challenge_replay.py" --checkout "$measured" --sdk "$HIVE_FIELDWORK_SDK" \
  --new-cases "$p/challenge-confirmation/stream.json.gz" \
  --new-keys "$p/challenge-confirmation/keys.json.gz" --output challenge-results.json
```

The original decompressed receipt SHA-256 is `8ce7b298533365c6e9c3a5c87631428e08401ac6fa8486c2aafb1c880090aad4`. The exact source and data hashes appear in the receipt. The grader reopens the delivered JSON files, counts missing files separately, and checks that a disputed order added no program to the bank. The sealed tests are human-authored and specific to the two studied transformations. [Grader](challenge_replay.py) · [Confirmation hashes](challenge-confirmation/SHA256SUMS)

The final witness format also records the rival’s effective input when staged upstream files compare equal as JSON or CSV but contain different raw text. A withheld receipt clears the primary digest. Replaying all nine orders after these metadata changes reproduced every delivery, abstention, challenge outcome and retained program. To repeat the final run, apply `gzip -dc "$p/challenge-witness-update.patch.gz" | git -C "$measured" apply` after the first challenge patch and repeat the command above. [Final replay](challenge-final.json.gz)
