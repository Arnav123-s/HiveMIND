# Demo: one prompt, whole team, end to end

Everything below is generated from the run's own records in `demo/run/` (`board.db`, `events.jsonl`, `calls.jsonl`). Nothing was edited by hand.

## Status (written by me, not generated)

**Partial.** The whole team ran on one prompt, end to end, on live sources:
- the researcher shortlisted models; code-level checks dropped the ones over 2B
- the browser failed on the Hugging Face pages, and each of those steps was re-routed to the researcher, which verified the license and the real file sizes from the Hugging Face API (jury 3/3)
- the coder wrote and ran a benchmark, but it failed on the 4-bit (GPTQ) models it was given
- the writer and critic delivered the report, and the checklist marks 3 of 6 instructions as not done

Two defects showed up in this run and are fixed in code, but not re-run end to end:
- **Invented numbers.** The writer's first report put numbers in the benchmark table that no step had verified (kept as `run/REPORT.before-number-check.md`). Every number must now appear in the verified results; `run/REPORT.md` is the writer re-run on the same verified results with that check.
- **Quantized sizes.** The size check believed quantized repos' packed parameter counts, so a 3.6B model passed as under 2B. It now reads the size in the model name.

The benchmark of real candidates is not done. Earlier attempts are in `runs/demo-attempt-*` (not in git):
- one ran a benchmark that exited cleanly but measured 0.00 s / 0/10; that led to the code-reviewer member and the measurement sanity checks
- the others exposed the verifier, browser and wording bugs listed in the README

## The one prompt

> I want to run a small AI chat model on my own laptop: no GPU, 16 GB RAM, no paying and no accounts.
> Find the best candidates on Hugging Face: text-generation models under 2B parameters with a permissive
> license that are not gated. For each of the top 3, open its Hugging Face page in the browser and check
> the license and the real size of its weights files. Then write and run a benchmark on this machine that
> loads each of the 3 models on CPU and measures load time, memory used and tokens per second, and checks
> how many of 10 simple arithmetic questions each one answers correctly. Verify everything and give me a
> ranked recommendation with sources.

Wall time: 88 min on a 4-core CPU, no GPU. Model calls: 67.

## The plan the coordinator made

- **s1 → researcher**: Find the best candidates on Hugging Face: text-generation models under 2B parameters with a permissive license that are not gated.  
  _done when:_ A list of top 3 candidates with their Hugging Face URLs and license information.
- **s2 → browser** (repeated for each item of s1): Open the Hugging Face page for each of the top 3 candidates and check the license and the real size of its weights files. Item: {item}  
  _done when:_ The license and real size of weights files for each of the top 3 candidates are verified.
- **s3 → coder**: Write and run a benchmark on this machine that loads each of the 3 models on CPU and measures load time, memory used and tokens per second, and checks how many of 10 simple arithmetic questions each one answers correctly.  
  _done when:_ The benchmark results for each of the 3 models are collected and verified.
- **s4 → writer**: Write a ranked recommendation with sources based on the benchmark results and verified information.  
  _done when:_ A ranked recommendation with sources is written and verified.

## What happened to each step

| step | specialist | verdict | attempts | verifier's reason |
|---|---|---|---|---|
| s1 | researcher | PASS | 2 | The evidence shows two models with 0.487B and 0.861B parameters, both under Apache-2.0 license. (jury 3/3 pass) |
| s2 | browser | PASS | 0 | 2/4 items verified |
| s3 | coder | FAIL | 3 | program exited 1: eam/.venv/lib/python3.13/site-packages/transformers/modeling_utils.py", line 4608, in warn_if_padding_and_no_attention_mask
    if self.config.pad_token_id in input_ids[:, [-1, 0]]:
 |
| s4 | writer | PASS | 1 | report written from verified results |
| s2[1] | browser | REROUTED | 3 | done by s2[1]r (researcher) after: the evidence quoted is not on the page the browser was on |
| s2[1]r | researcher | PASS | 1 | The license is Apache-2.0, and the weights files are 1.37 GB and 1.13 GB. (jury 3/3 pass) |
| s2[2] | browser | REROUTED | 3 | done by s2[2]r (researcher) after: the evidence quoted is not on the page the browser was on |
| s2[2]r | researcher | PASS | 1 | The evidence shows the model is licensed under Apache-2.0 and the weights file size is 2.60 GB. (jury 3/3 pass) |
| s3r | researcher | FAIL | 3 | no fact survived checking against its source |

## Facts: 7 supported, 0 rejected

- ✅ line-corporation/japanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False has 0.487B parameters and is under Apache-2.0 license  
  quote: `params 0.487B | license apache-2.0`  
  source: https://huggingface.co/api/models?search=false
- ✅ line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False has 0.861B parameters and is under Apache-2.0 license  
  quote: `params 0.861B | license apache-2.0`  
  source: https://huggingface.co/api/models?search=false
- ✅ The model is licensed under Apache-2.0  
  quote: `license apache-2.0`  
  source: https://huggingface.co/api/models?search=line-corporation%2Fjapanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False
- ✅ The safetensors weights file size is 1.37 GB  
  quote: `safetensors weights total 1.37 GB (1368204312 bytes)`  
  source: https://huggingface.co/api/models?search=line-corporation%2Fjapanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False
- ✅ The pytorch_model.bin file size is 1.13 GB  
  quote: `pytorch_model.bin size 1.13 GB (1132415244 bytes)`  
  source: https://huggingface.co/api/models?search=line-corporation%2Fjapanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False
- ✅ The model is licensed under Apache-2.0  
  quote: `license apache-2.0`  
  source: https://huggingface.co/api/models/line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False
- ✅ The weights file size is 2.60 GB  
  quote: `weights total 2.60 GB (2598342960 bytes)`  
  source: https://huggingface.co/api/models/line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False

## Browser work (real Chromium, screenshots after each action)

**s2** - Open the Hugging Face page for each of the top 3 candidates and check the license and the real size of its weights files. Item: {item}
  - **answer:** 2/4 items verified  
  - **evidence on page:** ``

**s2[1]** - Only for line-corporation/japanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False: Open the Hugging Face page for this candidate and check the license an
  - 1. click 'License: apache-2.0' -> now at https://huggingface.co/line-corporation/japanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False
  - **answer:** License: Apache-2.0, Files and versions: 0.487B  
  - **evidence on page:** `License: Apache-2.0
Files and versions: 0.487B`

**s2[2]** - Only for line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False: Open the Hugging Face page for this candidate and check the license an
  - **answer:** License: Apache License, Version 2.0 ... Files and versions xet  
  - **evidence on page:** `License: Apache License, Version 2.0 ... Files and versions xet`

Screenshots: 5 in `demo/run/screens/`.

## Code the team wrote and ran

- `demo/run/work/.s3.py.err`
- `demo/run/work/.s3.py.out`
- `demo/run/work/s3.py`

## Approvals

- none were needed

## The finished report

See [`run/REPORT.md`](run/REPORT.md). Copied here:

---

### Ranked Recommendation for Arnav

**Best Candidates:**
1. **line-corporation/japanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False** [0.487B, Apache-2.0]
2. **line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False** [0.861B, Apache-2.0]

### Benchmark Results

- **line-corporation/japanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False**
  - Load time: Not confirmed
  - Memory used: Not confirmed
  - Tokens per second: Not confirmed
  - Arithmetic questions answered: Not confirmed

- **line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False**
  - Load time: Not confirmed
  - Memory used: Not confirmed
  - Tokens per second: Not confirmed
  - Arithmetic questions answered: Not confirmed

### Summary

The best candidates are **line-corporation/japanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False** and **line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False**. Both are under 2B parameters, have permissive licenses, and are not gated. However, the benchmark results are not confirmed due to missing data.

## Your instructions
- ❌ Run a small AI chat model on my own laptop with no GPU, 16 GB RAM, no paying and no accounts. - Not confirmed
- ✅ Find the best candidates on Hugging Face: text-generation models under 2B parameters with a permissive license that are not gated.
- ✅ For each of the top 3, open its Hugging Face page in the browser and check the license and the real size of its weights files.
- ❌ Write and run a benchmark on this machine that loads each of the 3 models on CPU and measures load time, memory used and tokens per second. - Benchmark results are not confirmed
- ❌ Check how many of 10 simple arithmetic questions each one answers correctly. - Arithmetic questions answered are not confirmed
- ✅ Verify everything and give me a ranked recommendation with sources.

## Not confirmed by the team
- s3 (coder): Write and run a benchmark on this machine that loads each of the 3 models on CPU and measures load time, memory used and tokens per second, and checks - program exited 1: eam/.venv/lib/python3.13/site-packages/transformers/modeling_utils.py", line 4608, in warn_if_padding_and_no_attention_mask
    if self.config.pad_token_id in input_ids[:, [-1, 0]]:
                                   ~~~~~~~~~^^^^^^^^^^^^
IndexError: index is out of bounds for dimension with size 0

- s3r (researcher): Check the license and real size of the top 3 text-generation models on Hugging Face that are under 2B parameters, permissive licensed, and not gated - no fact survived checking against its source

## Sources
[1] https://huggingface.co/api/models?search=false
[2] https://huggingface.co/api/models?search=line-corporation%2Fjapanese-large-lm-1.7b-instruction-sft-4bit-32g-actorder_False
[3] https://huggingface.co/api/models/line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit-32g-actorder_False
