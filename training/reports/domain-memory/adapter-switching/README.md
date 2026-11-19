# Checking which adapter served a request

A server returned **confirm** after the client switched the conversation edit off and the native HTTP endpoint reported scale zero. Disabling compute-graph reuse restored the base model's **Thank** on this prompt. The middle response with the checked conversation edit stayed **confirm**. [Exact outputs and reported scales](results.json)

| Same prompt and requested weights | Original native server | Server with graph reuse disabled |
|---|---|---|
| Appointment, normal chat, off → on → off | Thank → confirm → Thank | Thank → confirm → Thank |
| Appointment, cached prefix, off → on → off | Thank → confirm → confirm | Thank → confirm → Thank |
| Water, cached prefix, A → B → A | solid → solid → solid | solid → Solid → solid |

Both servers used the same frozen quantized 8B checkpoint, binary, three adapter files, one CPU thread, 512-token context, and greedy one-token generation. Each ran on its own loopback port. A is the original withheld water candidate and B is the corrective candidate. These two exact tokens differ by capitalization and imply the same water phase. A separate normal-chat A → B → A on the fixed server also returned **solid → Solid → solid**. On this server the unedited water answer was **Liquid**. The low-level qualification's **Liquid** prediction for candidate A differed from this HTTP replay.

For the cached-prefix comparison, the test passed the identical tokens back through the native completion endpoint after each adapter switch. The initial appointment and water prefills evaluated 158 and 147 tokens respectively. Every subsequent request in each series evaluated one token. The adapters modify the output weights, so reusing the prefix keeps their input states comparable. The server-reported chat template matched the original serialized qualification prompt in each case. Ordinary chat clears its prompt cache on a switch. The first row shows why the normal multi-token prefill alone missed this defect.

At the pinned ik_llama.cpp revision, the HTTP switch clears and sets entries in the adapter map. The reusable graph's model-state key is zero on the Qwen architecture used here. A same-shape graph can therefore encode the previous adapter and outlive a successful scale update. The pinned executable accepts `--no-graph-reuse`. HiveMIND passes it when launching a server with one or more adapters and verifies the server identity when attaching to it. A base-only process can reuse its graph. [HTTP switch](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/examples/server/server-context.cpp#L3304) · [Adapter application](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/common/common.cpp#L4599) · [Graph state key](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/src/llama.cpp#L638)

## Reproduce the appointment comparison

From the project root, set `model` to the local Ternary-Bonsai-8B PQ2_0 GGUF and `server` to the pinned native executable. The script reads the public corpus, starts one isolated server, records the reported adapter scales and the actual outputs, and closes its own process. Run once with each checkout. To include water, supply both study GGUFs with `--water-a` and `--water-b`; their content hashes are in the results.

```sh
reference_dir=$(mktemp -d)
git archive 582792e team | tar -x -C "$reference_dir"
for arm in original corrected; do
  checkout=.
  if [ "$arm" = original ]; then checkout="$reference_dir"; fi
  python training/reports/domain-memory/adapter-switching/replay.py \
    --checkout "$checkout" --runtime "$server" --model "$model" \
    --conversation cells/engrams/t80+e_domain_conversation.gguf \
    --out "/tmp/hive-switch-$arm.json"
done
```
