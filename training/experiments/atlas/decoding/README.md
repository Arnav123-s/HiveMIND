# Five-token draft decoding on Ternary Bonsai 8B

Five-token speculative decoding **preserved all 64 target token IDs on three ordinary requests and slowed this two-thread CPU down**. The 4B draft took 37.30 seconds for the three replies. The two ordinary T80 measurements took 13.36 and 17.94 seconds. The 1.7B draft and prompt lookup also took longer than either ordinary run. All messages and finish reasons matched, all responses ended naturally and all 15 requests reported zero cached prompt tokens. [Native receipts with emitted token IDs](results.json) · [Exact comparison](summary.json)

| Method | Exact token sequences | Proposals accepted | Decode tokens/s | HTTP wall seconds | Native CPU seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary T80, first | 3/3 | — | 6.51 | 13.36 | 26.60 |
| 4B neural draft | 3/3 | 40/115 (35%) | 1.97 | 37.30 | 72.48 |
| 1.7B neural draft | 3/3 | 52/65 (80%) | 3.62 | 23.36 | 46.46 |
| Prompt lookup | 3/3 | 12/25 (48%) | 4.49 | 20.04 | 39.92 |
| Ordinary T80, last | 3/3 | — | 5.18 | 17.94 | 35.78 |

The 4B draft proposed 15 tokens on the Python task and T80 accepted all 15. Even there the round trip took 6.39 seconds, versus 3.71 and 5.08 seconds in the ordinary runs. On the pantry sentence T80 accepted only 10 of 70 proposals. With a shared vocabulary the 1.7B draft raised overall acceptance to 80%, but generating and verifying those proposals still cost 46.46 CPU seconds. Prompt lookup proposed no tokens on the Python task. All three methods reproduced the ordinary copy response, including two trailing spaces on its first three lines. [Per-question timings, text and acceptance by depth](results.json)

The first and last ordinary runs differ by 20% in decoding throughput. No other native server was active at any arm launch, yet the shared CPU and single fixed-order repetition leave considerable timing uncertainty. Both neural methods and prompt lookup were slower than the slower ordinary run on aggregate. Three short greedy completions establish identity on this workload only. Timing includes the same token-probability instrumentation in every arm. These results provide no basis for enabling a default speed optimization or promising stochastic equivalence. The preflight port check encountered a recently used socket after the first arm; the runner resumed from its saved first-arm receipt and used a separate loopback port per remaining arm. No completed question was repeated beyond the predefined control.

## What was compared

All arms served the same unadapted 8B target. Three short requests asked for an inventory copy, one Python expression and a sentence for a volunteer. Each process used two threads, a 512-token context, greedy sampling, seed 314159 and the native chat template with thinking disabled. Each had one warm-up request before the timed questions. Every timed request disabled the prompt cache, requested the chosen token IDs and allowed up to 36 generated tokens. The fixed order brackets the interventions with an ordinary run at each end. Server startup and warm-up are excluded from request times. The receipt includes both. [Panel](panel.json) · [Protocol](protocol.md) · [Runner](bench.py)

The target and 1.7B draft are Qwen3 GGUFs with identical 151,669-entry token tables and the same EOS ID. The 4B draft is Qwen3.5 with 248,320 entries and a different EOS ID. The backend's classic draft path can translate a token sequence between vocabularies by detokenizing and retokenizing. The published 9B draft alone is 2,416,851,840 bytes, larger than the 2,182,184,672-byte target. The neural comparison covers the 4B model proposed for HiveMIND and a smaller same-vocabulary 1.7B alternative. The 9B file was inspected through release metadata only. [GGUF headers and release metadata](weights.json) · [Draft backend](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/common/speculative.cpp) · [Published 9B](https://huggingface.co/prism-ml/Ternary-Bonsai-2-9B-gguf/tree/82265ccc78ddaac4700286a35e9badcc32376dd9)

The classic algorithm benefits when verifying several proposed tokens costs less than generating them one at a time. Its published gains depend on the models, acceptance and hardware. [Leviathan, Kalman and Matias, ICML 2023](https://proceedings.mlr.press/v202/leviathan23a.html)

Prompt lookup uses an exact three-token match in the text already seen to propose up to the next five tokens. It needs no second model. A target model checks the proposals in either mode. The native acceptance counters tell how many proposed tokens survived. Previously reported CPU measurements used different requests and specialist adapters, so the comparator here is the ordinary arm on this same panel. [Prior native measurement](../../../reports/verified-learning/peer/README.md)

## Reproduce on Linux

Use Python 3.11 or later, an x86-64 CPU with sufficient RAM and the native ik_llama.cpp backend. The measured checkout was commit `7aa7e01482db892b023bb9aace9a40567ab5297a` with a release CPU build, native instructions and OpenMP. Its exact binary SHA-256 was `0dc642d61dc39d51a8b5da348c43ba19d29f720b2a3ac790e0019351239da3b2`. The Hugging Face CLI commands below retrieve the pinned files. The experiment itself uses the Python standard library.

```bash
hf download prism-ml/Ternary-Bonsai-8B-gguf Ternary-Bonsai-8B-PQ2_0.gguf --revision c2aefbeb4b24469cd11579c3384b990404c17a30 --local-dir weights
hf download prism-ml/Ternary-Bonsai-2-4B-gguf Ternary-Bonsai-2-4B-PQ2_0.gguf --revision 50ebba61be85e5be07e8083db468ace0fc1bac43 --local-dir weights
hf download prism-ml/Ternary-Bonsai-1.7B-gguf Ternary-Bonsai-1.7B-PQ2_0.gguf --revision 40e40ecfe50bdfab51628042b1f8f4e97f08acd0 --local-dir weights

python bench.py --binary /path/to/llama-server --target weights/Ternary-Bonsai-8B-PQ2_0.gguf \
  --t4 weights/Ternary-Bonsai-2-4B-PQ2_0.gguf --t17 weights/Ternary-Bonsai-1.7B-PQ2_0.gguf \
  --port 18493 --logs native-logs --output run.json
python summarize.py run.json
python inspect_weights.py weights/*.gguf
```

The separate abstention test used archived G50 and G51 evidence to calibrate a release rule for G52. That study measures answer selection and risk independently of token-generation speed. [Cross-generation calibration](../calibration/README.md)
