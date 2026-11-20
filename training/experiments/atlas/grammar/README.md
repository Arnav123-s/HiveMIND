# Does constrained decoding improve short answers?

Eight ordinary prompts request a JSON object, integer array, CSV row or exact label. A separate author fixed the questions, their answer keys and the grader before native inference. A new CPU process serves the pinned Ternary-Bonsai-8B base with no adapters. Each question receives one greedy reply with unrestricted generation and one with a GBNF grammar derived solely from its declared output schema. The prompts, base, 32-token completion cap and seed are identical across arms. The ambiguous request allows an uncertainty label. [Frozen panel](panel.json) · [Independent answer keys](answers.json) · [Scoring rules](oracle.py) · [Protocol](protocol.md)

Exact-format scoring removes surrounding whitespace, parses the entire answer and checks the required schema. The separate content score also accepts a single fully parsable payload in a Markdown fence or after a conventional `Answer:`, `Result:` or `Output:` prefix. It gives no credit for an answer buried in longer prose. A well-formed object containing a wrong integer fails content. The grammar determines key spelling, scalar types and the answer alphabet, without consulting the key for the task.

## Native results

| Measure on eight paired requests | Free generation | Native grammar |
| --- | ---: | ---: |
| Entire reply matches the requested format | 5/8 | **8/8** |
| Identifiable answer content is correct | 4/8 | 4/8 |
| Both content and format are correct | 2/8 | **4/8** |
| Prompt tokens evaluated | 525 | 525 |
| Generated tokens, as reported by the server | 103 | 65 |
| CPU seconds in the native process | 451.91 | 462.66 |
| Summed request wall time, seconds | 239.48 | 238.70 |

Two free replies already contained the correct electronics and ML answers inside Markdown fences. Constrained decoding delivered those same answers as usable JSON. The reversed-list question illustrates the remaining risk. Its free reply ran out of tokens during an explanation. Its grammar-constrained reply was valid JSON, `[17,17,5]`, while the correct reversed result was `[5,17,17]`. Both arms returned `unknown` when a flyer was silent about Sunday and both made the same arithmetic and list-length errors on three other questions. No item gained or lost content credit. [Raw paired replies and token timings](receipts/pairs.json) · [All independent grades](results.json)

The grammar removed 38 generated tokens, about 37%. CPU time increased by 10.75 seconds in total and wall time was within one second across the two arms. Each metric is one observation per arm per question, with another native job active during part of the run. Both arms recomputed all prompt tokens. These measurements do not establish a latency saving. An excluded preflight confirmed the sampler could force `QZ` on the same request that produced `A` in the free arm. The initial process-accounting setup attempt ended before submitting any inference. [Environment and GBNF rules](receipts/environment.json) · [Runtime revision](receipts/host.json) · [Forced-literal control](receipts/preflight.json)

## Reproduce on CPU

From the repository root, use the Python environment for this project and a local compatible `llama-server`. The program verifies the t80 model SHA before launch. It runs both arms on a private loopback port, disables prompt caching and closes its own server afterward. To re-score saved responses, only the second command is needed.

```sh
python -m training.experiments.atlas.grammar.run \
  --model /path/to/Ternary-Bonsai-8B-PQ2_0.gguf --runtime /path/to/llama-server \
  --threads 2 --out /tmp/hive-grammar-run
python -m training.experiments.atlas.grammar.score /tmp/hive-grammar-run \
  --out /tmp/hive-grammar-score.json
```

A separate metamorphic experiment tests relations between duration parsing and formatting on genuine recovered G52 module files and authored controls. It fixes the relations and chooses a program before consulting an independent exact-value panel. [Duration study and reproduction](metamorphic/README.md)

## What a structure check can miss

The duration study gives a second example. Both genuine G52 programs passed 24/24 metamorphic relations and later 60/60 exact-value cases. A base-61 clock passed all 24 relations too, while answering only 8/60 correctly. The frozen hash tie-break selected that wrong module when the control joined the two genuine candidates. A wrap-at-midnight control passed 20/24 relations and 44/60 exact cases. Round trips can establish that two functions agree with each other while both use the wrong unit. These checks used CPython WASI and zero model calls. [Candidate selection before the oracle](metamorphic/selection.json) · [Independent known-answer grades](metamorphic/grade.json)
