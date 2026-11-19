# Independent timing-unit correction check

The corrective timing adapter answered **3 of 6 new unit-equivalence questions** correctly. Bare and initial-edit runs each produced two correct first tokens. The new edit fixed one genuinely different conversion, from 0.001 microseconds to one nanosecond. It continued to miss both fresh cases that called for “us” and one that called for “ms”. All three old checks passed after being included in corrective training. The fresh gate required six out of six; the candidate failed qualification.

| Matched native first-token check | Bare 8B | Initial edit | Corrective edit |
| --- | ---: | ---: | ---: |
| Six fresh descriptions, two per unit | 2/6 | 2/6 | 3/6 |
| Three old checks included in corrective training | 1/3 | 1/3 | 3/3 |

The test author froze the six descriptions and verified every conversion independently with decimal arithmetic. None of the six full descriptions appears in the teaching corpus. The frozen corrective GGUF (`fca504027e9e0a07ad76ce06eda440a4683818bb68ad9e2be2502b251a04b56f`) was independently hashed before the trainer received the panel. An independent regrade of the decoded raw first tokens reproduced all totals. With native graph reuse disabled, reapplying the initial adapter recovered its exact first token on every question. This experiment tests one prompted abbreviation per question. [Commitment](commitment.sha256) · [Inputs and labels](panel.json) · [Frozen protocol](protocol.md) · [Native four-pass evidence](../timing-v2/qualification.json)

The final catalogue contains no timing adapter. [Recorded release decision](../timing-v2/release.json)
