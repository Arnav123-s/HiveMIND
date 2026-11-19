# Generation 49 on the ordinary chat path

Two released G49 members wrote and ran separate programs for a repair café. Seven envelopes contained 18 washers each. The café reserved 23 and handed out 31. Both programs printed `72`, and the ordinary chat interface returned exactly `72`. The independent key was fixed before inference. The native server reported `g49trunk` at scale 1 for the first member and `g49code2` at scale 1 for the second. Each produced its program on the first turn and used a second turn to finish. The selected programs and their printed outputs are in the [receipt](receipt.json).

A separate direct question on the same installation asked for Finland’s capital. The reply was `Helsinki`. Both the routing call and the direct answer used the base T80 model with all edits at zero. The five qualified starter weights and the G49 data specialist were loaded and available throughout. The observed requests activated the trunk and code specialist only during the arithmetic task.

The full run took 237 seconds on two shared CPU threads, including 187 seconds for the arithmetic task and 48 seconds for direct chat. The server ran the pinned native binary with `--no-graph-reuse` and was stopped after the two requests. This single predeclared arithmetic case confirms the installed body launches and can produce a checked answer. The [broader paired answer study](../answers/README.md) used its own frozen setup and measures separate questions.

## Reproduce the requests

Use a checkout of `19992ca4ae4c46f6d5f79eb6dbc3f9fd47fc8d9e` with the T80 model and pinned native runtime installed. The [public release](https://github.com/Arnav123-s/HiveMIND/releases/tag/hive-grown) contains the three G49 files used here. These commands install them in a temporary directory under their runtime names. Their SHA-256 digests, release asset IDs and public URLs are in the receipt.

```sh
export HIVE_ADAPTERS_HOME="$(mktemp -d)"
for edit in g49trunk g49code2 g49data2; do
  curl --fail --location --silent --show-error \
    "https://github.com/Arnav123-s/HiveMIND/releases/download/hive-grown/t80.$edit.gguf" \
    -o "$HIVE_ADAPTERS_HOME/t80+$edit.gguf"
done
export HIVE_MEMBERS=t80+g49trunk,t80+g49code2,t80+g49data2
export AGENT_TEAM_THREADS=2 AGENT_TEAM_SOLO=2 HIVE_BANK=off
./hive --once 'A repair café received 7 envelopes with 18 washers each. It set aside 23 washers for Saturday and handed out another 31 today. How many washers are still available? Calculate it with a program and reply with just the integer.'
./hive --once 'What is the capital city of Finland? Reply with just the city name.'
```

The recorded test called `team.talk.reply` directly and observed the active native scales after each model call. It remapped the loopback port and used fresh private run and memory directories. The second worker used the normal sampling temperature of 0.7, so another run can generate different code. The active body manifest identified G49, and this check installed three of its released members. [Body manifest](../../../../cells/body.json) · [T80 base](https://huggingface.co/prism-ml/Ternary-Bonsai-8B-gguf/tree/c2aefbeb4b24469cd11579c3384b990404c17a30)

## Separate water-phase replay

At one atmosphere, the original G49 run told the user that pure water at 72 °C was a gas and that two programs agreed. Both programs printed that assertion. On the single retrospective replay at `73cc005`, the ordinary chat reply was **“The water is liquid.”** The base router again selected `WORK`, and the water adapter again returned the unusable token `At` while active at scale 1.0. The fix used the pure-water equilibrium rule to supply the answer. The receipt recorded the model’s rejected output and the rule as the source. There were two native calls and no worker-confirmation claim. The original run used five native calls. [Original G49 trace](../../domain-engrams/serving-final/physics-open.json) · [Replay trace](water-replay/physics-open.json) · [Paired settings and results](water-replay/comparison.json)

**This release recognized 0 of 2 new eligible phrasings** in a separate six-question test. Both injected wrong answers passed through on both tested routes. It correctly deferred on all four ambiguous or compound requests. The independent check used controlled conflicting replies. The original disclosed question above is the only live native replay in this comparison. [Independent six-case controls](../../domain-engrams/water-v2/delivery-control/README.md)

To repeat the native question, use the same T80 and G49 setup above in a checkout of `73cc0059478431cd307e32e81f6ba6e63dcbc7c0`. Run the shared native probe on a free local port with `python training/reports/domain-engrams/serve.py --domain physics --form open --out /tmp/hive-water-readback --port 18349`. The probe records live adapter scales, token budgets, seeds and model replies. The two paired runs had identical first two native prompts, active weights, seeds and token budgets. [Replay environment](water-replay/launch-1e5fb1fcc11b.json)
