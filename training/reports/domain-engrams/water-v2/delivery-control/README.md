# Can a wrong phase answer get through final delivery?

**Yes, on both independent phase-only requests in this six-case check.** The ordinary final-answer guard declined two complete questions, even though the physical rule could solve both. With a deliberately conflicting response injected at the model and worker boundaries, the talk path returned the wrong phase and the work path reported the wrong agreed answer on both. The guard also deferred on all four requests outside its scope.

| Intended scope | Cases | Guard activated | Observed result |
| --- | ---: | ---: | --- |
| Complete, one phase requested | 2 | 0 | Both injected wrong answers passed through on both routes |
| Missing pressure or at a phase boundary | 2 | 0 | The guard left both ordinary paths alone |
| Additional calculation or code requested | 2 | 0 | The guard left both ordinary paths alone |

At 58 °C the first caller asked which phase to put on a lab form. The outer eligibility check rejected ordinary wording such as “lab” and “form”. The second caller asked for the phase in one word at minus seventeen Celsius. Its wording failed the requested-decision test as well. On these same two inputs, direct calls to the underlying physical calculation returned **liquid** and **solid**. The label validator rejected both injected conflicts, and the explicit deterministic recovery produced the correct word in both cases. That component probe bypasses the outer scope check. A normal user did not receive either recovery in these trials.

The four exclusions include a question about a two-phase boundary and a request for a complete Python function. A phase-only response cannot resolve them. Deferring was appropriate for this guard; the injected answers still are not evidence of successful task delivery.

**How to reproduce.** Six full inputs, expected scopes and conflicting worker labels were committed by hash before the test author saw the guard. The replayer runs the public `talk.reply` path with forced talk/work choices, a simulated agreeing worker, and simulated conflicting model responses. It launches no 8B inference. The same six prompts with the pre-guard tree at `19992ca` delivered exactly the same injected strings. This mechanism check is separate from native generations, adapter qualification and real-answer benchmarks.

```sh
python training/reports/domain-engrams/water-v2/delivery-control/replay.py --output /tmp/hive-water-delivery.json
```

The measured guarded checkout was `73cc0059478431cd307e32e81f6ba6e63dcbc7c0`. [Frozen cases](cases.json) · [Protocol](protocol.md) · [Commitment](commitment.sha256) · [Guarded run and component probes](results.json) · [Pre-guard comparison](baseline.json)
