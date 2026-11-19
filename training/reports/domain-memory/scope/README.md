# Which ordinary requests would consult a native microtask?

The four-adapter starter bank definitely selected the intended specialist on **3 of 12 applicable requests**. Two more could select it if the chat router chose the talk path. Seven applicable requests reached neither specialist path. Among 12 adjacent requests the system left seven alone and consulted an adapter on five, all for the expected broad subject but outside the label task the adapter had qualified on.

| Scope of request | Framed consultation on every available route | Direct label on talk only | No consultation on any available route |
| --- | ---: | ---: | ---: |
| Applicable | 3 | 2 | 7 |
| Adjacent or ambiguous | 5 | 0 | 7 |

The three definite hits came from narrow task cues after the subject consensus had abstained. Both conditional direct hits came from matching conversation consensus. Of the five adjacent consultations, four followed matching consensus and one followed abstention. The five adjacent consultations included debugging an invoice script, explaining two Python operations, explaining how cube scaling works, diagnosing a training curve, and writing grouped train/test splitting code. A framed hint might still be helpful on a larger assignment. This check cannot tell whether any such hint improves or harms the final answer.

Coding, math, conversation and machine learning had qualified starter weights. No physical-science or computer-engineering weight was available in this first package, accounting for four of the seven definite misses. Across just the eight applicable requests in the installed subjects, three definitely reached the right adapter, two depended on the conversational branch and three were missed. No prompt was sent to a different domain's native adapter.

**What was measured.** The 24 prompts and scope labels were frozen before inspecting the helper. None exactly repeats a prompt from the earlier public exercises, native chat examples, end-answer panel or routing panel. The evaluator uses the real subject consensus, native registry metadata, hashed weight files and ordinary lookup functions. When chat would ask the model to choose talk or work, it enumerates both route choices. It intercepts potential inference at the actual generation boundary. The counts therefore describe adapter selection, including branch uncertainty. No 8B generation, adapter answer or final answer was measured. The small panel deliberately includes close negatives and cannot estimate everyday misuse rates.

Original route and selector code matches `4bb1259`. The v1 store checksum is `e95f24021525998f6bed1880b4667b09da5c2a96a63bd58127e55686c364f4c8`. [Frozen prompts and rationales](cases.json) · [Protocol](protocol.md) · [Complete per-request route decisions](results.json) · [Initial registry](registry-v1.jsonl) · [Replayer](evaluate.py)

The subsequent generic requested-decision guard removed all five adjacent consultations on this original panel and also lost one definite applicable case. A separately sealed 12-case confirmation on the same four weights removed one adjacent consultation and preserved all four reachable positive cases, three definite and one conditional on the talk branch. [Prospective scope confirmation](confirmation/README.md)

To reproduce the four-weight v1 trace from the repository root, check out commit `8e3a0a9` in a separate directory, which contains the frozen production code and the initial GGUF store. Use this report's driver against that checkout:

```sh
python training/reports/domain-memory/scope/evaluate.py \
  --checkout /path/to/v1-checkout \
  --registry-sha e95f24021525998f6bed1880b4667b09da5c2a96a63bd58127e55686c364f4c8 \
  --output /tmp/hive-v1-scope.json
```

For the 12-case panel, add `--cases training/reports/domain-memory/scope/confirmation/cases.json --panel-sha 5ba4f90213d0e5e9cb058070694ec01ee1e258fec61f6bb36aa70aafbcea9567`. For a newer policy or different verified bank, the driver accepts `--scope-sha` and `--bank` explicitly. The stored decision files record which helper, registry and native-file hashes were used.
